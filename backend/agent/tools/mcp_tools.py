"""
MCP Tools — Tika MCP 서버와의 연결 및 툴 캐시 관리.

앱 시작 시 init_mcp_client()를 호출하면 SSE로 연결하고 툴 목록을 캐시합니다.
이후 get_mcp_tools()로 LangChain 툴 목록을 가져와 ReAct 에이전트에 주입합니다.
"""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# 이 모듈은 agent/tools/__init__.py 를 통해 a2a_router 보다 먼저 import 되므로
# database.py 의 load_dotenv 를 기다리지 않고 여기서 직접 .env 를 로드한다.
# (backend/agent/tools/mcp_tools.py → 프로젝트 루트 .env)
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

logger = logging.getLogger(__name__)

TIKA_MCP_URL = os.getenv("TIKA_MCP_URL", "http://127.0.0.1:8100/mcp")
WEATHER_MCP_URL = os.getenv("WEATHER_MCP_URL", "http://127.0.0.1:8101/mcp")
DOCGEN_MCP_URL = os.getenv("DOCGEN_MCP_URL", "http://127.0.0.1:8102/mcp")
MCP_AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN", "")

_client = None
_tools: list = []


def _server_config(url: str) -> dict:
    cfg: dict = {"url": url, "transport": "streamable_http"}
    if MCP_AUTH_TOKEN:
        cfg["headers"] = {"Authorization": f"Bearer {MCP_AUTH_TOKEN}"}
    return cfg


def _unwrap_exc(e: BaseException) -> str:
    """ExceptionGroup/TaskGroup 을 풀어서 실제 원인 문자열로 변환."""
    causes: list[str] = []
    seen: set[int] = set()
    stack: list[BaseException] = [e]
    while stack:
        cur = stack.pop()
        if id(cur) in seen:
            continue
        seen.add(id(cur))
        sub = getattr(cur, "exceptions", None)
        if sub:
            stack.extend(sub)
        else:
            causes.append(f"{type(cur).__name__}: {cur}")
    return " | ".join(causes) if causes else f"{type(e).__name__}: {e}"


async def init_mcp_client() -> None:
    """모든 MCP 서버에 개별 연결을 시도한다. 한 서버 실패가 나머지를 막지 않는다."""
    global _client, _tools

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except Exception as e:
        msg = f"MCP 라이브러리 import 실패: {_unwrap_exc(e)}"
        print(f"[MCP] {msg}", flush=True)
        logger.warning(msg)
        _tools = []
        return

    if MCP_AUTH_TOKEN:
        logger.info("MCP_AUTH_TOKEN 활성화 — 모든 MCP 서버 요청에 Bearer 헤더를 추가합니다.")
    else:
        logger.warning("MCP_AUTH_TOKEN이 설정되지 않아 MCP 서버에 인증 헤더를 보내지 않습니다.")
    token_state = "set" if MCP_AUTH_TOKEN else "EMPTY"

    servers = {
        "tika": _server_config(TIKA_MCP_URL),
    }
    if WEATHER_MCP_URL:
        servers["weather"] = _server_config(WEATHER_MCP_URL)
    if DOCGEN_MCP_URL:
        servers["docgen"] = _server_config(DOCGEN_MCP_URL)

    _client = MultiServerMCPClient(servers)
    aggregated: list = []
    succeeded: list[str] = []
    failed: list[str] = []

    for name in servers:
        try:
            tools = await _client.get_tools(server_name=name)
            aggregated.extend(tools)
            succeeded.append(f"{name}({len(tools)})")
            logger.info(f"[MCP:{name}] 연결 완료 — {len(tools)}개 툴: {[t.name for t in tools]}")
        except Exception as e:
            detail = _unwrap_exc(e)
            failed.append(name)
            msg = f"[MCP:{name}] 연결 실패 (token={token_state}): {detail}"
            print(msg, flush=True)
            logger.warning(msg)

    _tools = aggregated
    summary = f"[MCP] 로드 완료 — 성공: {succeeded or '없음'} / 실패: {failed or '없음'} (총 {len(_tools)}개 툴)"
    print(summary, flush=True)
    logger.info(summary)

    try:
        from task_handler import _register_mcp_tool_names
        _register_mcp_tool_names([t.name for t in _tools])
    except Exception as e:
        logger.warning(f"task_handler MCP 툴 이름 등록 실패: {e}")


async def close_mcp_client() -> None:
    """MCP 클라이언트 연결을 종료합니다."""
    global _client
    _client = None
    logger.info("MCP 클라이언트 정리 완료")


def get_mcp_tools() -> list:
    """캐시된 MCP 툴 목록을 반환합니다."""
    return _tools
