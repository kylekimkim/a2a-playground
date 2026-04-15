"""
MCP Tools — Tika MCP 서버와의 연결 및 툴 캐시 관리.

앱 시작 시 init_mcp_client()를 호출하면 SSE로 연결하고 툴 목록을 캐시합니다.
이후 get_mcp_tools()로 LangChain 툴 목록을 가져와 ReAct 에이전트에 주입합니다.
"""
import logging
import os

logger = logging.getLogger(__name__)

TIKA_MCP_URL = os.getenv("TIKA_MCP_URL", "http://127.0.0.1:8100/sse")
WEATHER_MCP_URL = os.getenv("WEATHER_MCP_URL", "http://127.0.0.1:8101/sse")
DOCGEN_MCP_URL = os.getenv("DOCGEN_MCP_URL", "http://127.0.0.1:8102/sse")

_client = None
_tools: list = []


async def init_mcp_client() -> None:
    """MCP 클라이언트를 초기화하고 Tika 서버에 연결합니다."""
    global _client, _tools

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient

        servers = {
            "tika": {"url": TIKA_MCP_URL, "transport": "sse"},
        }
        if WEATHER_MCP_URL:
            servers["weather"] = {"url": WEATHER_MCP_URL, "transport": "sse"}
        if DOCGEN_MCP_URL:
            servers["docgen"] = {"url": DOCGEN_MCP_URL, "transport": "sse"}

        _client = MultiServerMCPClient(servers)
        _tools = await _client.get_tools()
        print(f"[MCP] 연결 완료 — {len(_tools)}개 툴 로드: {[t.name for t in _tools]}", flush=True)
        logger.info(f"MCP 클라이언트 연결 완료 — {len(_tools)}개 툴 로드: {[t.name for t in _tools]}")

        from task_handler import _register_mcp_tool_names
        _register_mcp_tool_names([t.name for t in _tools])
    except Exception as e:
        print(f"[MCP] 연결 실패: {e}", flush=True)
        logger.warning(f"MCP 클라이언트 연결 실패 (Tika 서버가 실행 중인지 확인하세요): {e}")
        _tools = []


async def close_mcp_client() -> None:
    """MCP 클라이언트 연결을 종료합니다."""
    global _client
    _client = None
    logger.info("MCP 클라이언트 정리 완료")


def get_mcp_tools() -> list:
    """캐시된 MCP 툴 목록을 반환합니다."""
    return _tools
