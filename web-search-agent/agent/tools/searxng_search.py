"""
SearXNG Search Tool — SDD §7.2.

로컬 SearXNG 인스턴스(SEARXNG_URL, 기본 http://localhost:8888)의 JSON API를 호출합니다.
SearXNG는 settings.yml에서 `formats: [html, json]`을 활성화해야 합니다 (searxng/settings.yml 참고).
"""
import os
import logging
from urllib.parse import urlparse

import httpx
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

SEARXNG_URL = os.getenv("SEARXNG_URL", "http://localhost:8888").rstrip("/")
SEARXNG_TIMEOUT = float(os.getenv("SEARXNG_TIMEOUT", "10"))

# SDD §13 — Private IP / SSRF 차단을 위한 도메인 deny 목록
_BLOCKED_HOST_SUFFIXES = (
    ".local", ".localhost", ".internal",
)


def _is_blocked(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return True
    return any(host == s.lstrip(".") or host.endswith(s) for s in _BLOCKED_HOST_SUFFIXES)


@tool
def search_web(query: str, max_results: int = 5) -> str:
    """SearXNG로 웹 검색을 수행합니다.

    Args:
        query: 검색 쿼리 문자열.
        max_results: 반환할 결과 수 (1~10).

    Returns:
        제목·URL·스니펫이 번호 매겨진 텍스트 블록. 검색 실패 시 에러 메시지.
    """
    if not query or not query.strip():
        return "에러: 비어 있는 쿼리는 검색할 수 없습니다."
    n = max(1, min(int(max_results or 5), 10))

    try:
        with httpx.Client(timeout=SEARXNG_TIMEOUT) as client:
            resp = client.get(
                f"{SEARXNG_URL}/search",
                params={
                    "q": query,
                    "format": "json",
                    "safesearch": 1,
                    "language": "ko",
                },
                headers={"User-Agent": "a2a-web-search-agent/1.0"},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        return f"SearXNG 호출 실패 (HTTP {e.response.status_code}). settings.yml에서 JSON format이 활성화됐는지 확인하세요."
    except httpx.HTTPError as e:
        return f"SearXNG 연결 실패: {e}. 컨테이너가 실행 중인지 확인하세요 ({SEARXNG_URL})."
    except ValueError:
        return "SearXNG 응답을 JSON으로 파싱할 수 없습니다. settings.yml에서 JSON format이 활성화됐는지 확인하세요."

    results = data.get("results", [])
    if not results:
        return f"'{query}'에 대한 검색 결과가 없습니다."

    lines: list[str] = [f"[검색 결과 — '{query}' (top {n})]"]
    seen_urls: set[str] = set()
    count = 0
    for r in results:
        url = (r.get("url") or "").strip()
        if not url or url in seen_urls or _is_blocked(url):
            continue
        seen_urls.add(url)
        title = (r.get("title") or "").strip() or "(no title)"
        snippet = (r.get("content") or "").strip().replace("\n", " ")
        if len(snippet) > 300:
            snippet = snippet[:300] + "…"
        count += 1
        lines.append(f"{count}. {title}\n   URL: {url}\n   요약: {snippet}")
        if count >= n:
            break

    if count == 0:
        return f"'{query}': 모든 결과가 허용되지 않는 도메인입니다."
    return "\n\n".join(lines)
