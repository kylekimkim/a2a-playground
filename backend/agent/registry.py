import json
import requests
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _norm_authority(url: str) -> str:
    """URL에서 host:port를 정규화해 추출. 경로/쿼리/슬래시 차이를 무시한 비교에 사용."""
    if not url:
        return ""
    try:
        candidate = url if "://" in url else f"http://{url}"
        p = urlparse(candidate)
        host = (p.hostname or "").lower()
        if not host:
            return ""
        port = p.port or (80 if p.scheme == "http" else 443)
        return f"{host}:{port}"
    except Exception:
        return ""


def is_passthrough_agent(target_url: str) -> bool:
    """캐시된 카드에서 capabilities.passthrough=True 인 에이전트인지 확인.

    LLM이 trailing slash나 /chat 유무를 다르게 줘도 host:port로 매칭합니다.
    캐시는 매 요청마다 갱신되므로(_AGENT_CACHE) 직전 폴링 결과를 기준으로 판단합니다.
    """
    target_auth = _norm_authority(target_url)
    if not target_auth:
        return False
    for chat_url, card in _AGENT_CACHE.items():
        if _norm_authority(chat_url) == target_auth:
            return bool((card.get("capabilities") or {}).get("passthrough", False))
    return False

# 현재 프로토타입 동작을 위해 알려진 특화 에이전트 목록을 하드코딩
# (실제 환경에서는 서비스 디스커버리 또는 레지스트리 DB를 사용할 수 있습니다)
KNOWN_NODES: list[str] = [
    "http://127.0.0.1:9001",
    "http://127.0.0.1:9002",
    "http://127.0.0.1:9003",
    "http://127.0.0.1:9004",  # web-search-agent (SearXNG + Crawl4AI ReAct)
]

_AGENT_CACHE = {}


def add_node(url: str) -> bool:
    """KNOWN_NODES에 새 에이전트 URL을 추가합니다. 이미 존재하면 False 반환."""
    url = url.rstrip("/")
    if url in KNOWN_NODES:
        return False
    KNOWN_NODES.append(url)
    return True


def remove_node(url: str) -> bool:
    """KNOWN_NODES에서 에이전트 URL을 제거합니다. 존재하지 않으면 False 반환."""
    url = url.rstrip("/")
    if url not in KNOWN_NODES:
        return False
    KNOWN_NODES.remove(url)
    _AGENT_CACHE.pop(url, None)
    return True


def get_agents_with_status() -> list[dict]:
    """
    등록된 모든 에이전트의 상태와 카드 정보를 반환합니다.
    각 에이전트에 대해 실시간으로 .well-known/agent.json을 조회합니다.
    """
    result = []
    for node in KNOWN_NODES:
        base_url = node.rstrip("/")
        try:
            resp = requests.get(f"{base_url}/.well-known/agent.json", timeout=2)
            if resp.status_code == 200:
                card = resp.json()
                # 카드의 url(chat endpoint)을 캐시 키로 사용
                chat_url = card.get("url", base_url)
                _AGENT_CACHE[chat_url] = card
                result.append({"url": base_url, "online": True, "card": card})
            else:
                cached = next((c for c in _AGENT_CACHE.values() if c.get("url", "").startswith(base_url)), None)
                result.append({"url": base_url, "online": False, "card": cached})
        except Exception:
            cached = next((c for c in _AGENT_CACHE.values() if c.get("url", "").startswith(base_url)), None)
            result.append({"url": base_url, "online": False, "card": cached})
    return result

def fetch_agent_cards():
    """
    모든 KNOWN_NODES에 대해 .well-known/agent.json을 가져와서 캐시에 저장합니다.
    """
    global _AGENT_CACHE
    new_cache = {}
    for node in KNOWN_NODES:
        try:
            response = requests.get(f"{node}/.well-known/agent.json", timeout=2)
            if response.status_code == 200:
                card = response.json()
                # 카드의 url(chat endpoint)을 캐시 키로 사용
                chat_url = card.get("url", node)
                new_cache[chat_url] = card
        except Exception as e:
            logger.warning(f"Failed to fetch agent card from {node}: {e}")

    _AGENT_CACHE = new_cache

def get_available_agents_prompt_snippet() -> str:
    """
    현재 접속 가능한 에이전트 목록을 시스템 프롬프트용 텍스트로 변환합니다.
    (새로운 에이전트가 뜰 때마다 갱신하기 위해 요청 시마다 fetch 수행)
    """
    fetch_agent_cards()
    
    if not _AGENT_CACHE:
        return ""
        
    lines = ["[현재 이용 가능한 특화 에이전트 목록]"]
    lines.append("당신은 다음 에이전트들에게 `delegate_task` 도구를 사용하여 작업을 위임할 수 있습니다.")
    
    for _, card in _AGENT_CACHE.items():
        name = card.get("name", "Unknown Agent")
        desc = card.get("description", "")
        skills = card.get("skills", [])
        chat_url = card.get("url", "")

        skill_texts = []
        for s in skills:
            skill_texts.append(f"- {s.get('name')}: {s.get('description')}")

        lines.append(f"\n에이전트 이름: {name}")
        lines.append(f"대상 URL (target_url): {chat_url}")
        lines.append(f"설명: {desc}")
        lines.append("보유 스킬:")
        lines.extend(skill_texts)
        
    lines.append("\n[위임 지침]")
    lines.append("사용자의 질문이 위 에이전트들의 전문 분야와 일치한다면, 해당하는 '대상 URL'을 target_url 인자로 삼아 delegate_task를 호출하여 위임하세요.")
    return "\n".join(lines)

def get_agent_name(url: str) -> str:
    """대상 URL로부터 에이전트 이름을 캐시에서 가져옵니다."""
    card = _AGENT_CACHE.get(url)
    if card:
        return card.get("name", "특화 에이전트")
    return "특화 에이전트"
