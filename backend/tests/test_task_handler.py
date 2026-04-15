"""
TDD: task_handler 단위 테스트

_tool_notice, _to_lc_messages 등 내부 헬퍼 함수를 직접 테스트합니다.
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from task_handler import _tool_notice, _to_lc_messages, _user_text, _register_mcp_tool_names, _MCP_TOOL_NAMES
from models import TaskSendParams, Message, TextPart
from langchain_core.messages import HumanMessage, AIMessage


@pytest.fixture(autouse=True)
def clear_mcp_tool_names():
    _MCP_TOOL_NAMES.clear()
    yield
    _MCP_TOOL_NAMES.clear()


class TestToolNotice:
    """_tool_notice: 도구 실행 알림 텍스트 생성"""

    def test_web_search_notice_contains_query(self):
        notice = _tool_notice("web_search", {"query": "파이썬 최신 버전"})
        assert "파이썬 최신 버전" in notice

    def test_web_search_notice_has_search_icon(self):
        notice = _tool_notice("web_search", {"query": "test"})
        assert "🔍" in notice

    def test_calculator_notice_contains_expression(self):
        notice = _tool_notice("calculator", {"expression": "2 + 3"})
        assert "2 + 3" in notice

    def test_calculator_notice_has_calc_icon(self):
        notice = _tool_notice("calculator", {"expression": "x"})
        assert "🧮" in notice

    def test_get_datetime_notice_contains_timezone(self):
        notice = _tool_notice("get_datetime", {"timezone": "UTC"})
        assert "UTC" in notice

    def test_get_datetime_notice_has_clock_icon(self):
        notice = _tool_notice("get_datetime", {})
        assert "🕐" in notice

    def test_delegate_task_notice_has_robot_icon(self):
        notice = _tool_notice("delegate_task", {"target_url": "http://127.0.0.1:9001/chat"})
        assert "🤖" in notice

    def test_unknown_tool_has_wrench_icon(self):
        notice = _tool_notice("some_unknown_tool", {})
        assert "🔧" in notice

    def test_notice_is_blockquote_format(self):
        """blockquote 형식 (> 로 시작)"""
        notice = _tool_notice("web_search", {"query": "test"})
        assert ">" in notice

    def test_mcp_tool_notice_has_plug_icon(self):
        _register_mcp_tool_names(["get_current_weather"])
        notice = _tool_notice("get_current_weather", {"city": "서울"})
        assert "🔌" in notice

    def test_mcp_extract_text_notice_contains_filename(self):
        _register_mcp_tool_names(["extract_text_from_file"])
        notice = _tool_notice("extract_text_from_file", {"file_path": "/uploads/report.pdf"})
        assert "report.pdf" in notice

    def test_mcp_weather_notice_contains_city(self):
        _register_mcp_tool_names(["get_current_weather"])
        notice = _tool_notice("get_current_weather", {"city": "부산"})
        assert "부산" in notice

    def test_mcp_create_document_notice_contains_filename(self):
        _register_mcp_tool_names(["create_document"])
        notice = _tool_notice("create_document", {"filename": "report", "format": "docx"})
        assert "report" in notice

    def test_mcp_forecast_notice_contains_days(self):
        _register_mcp_tool_names(["get_weather_forecast"])
        notice = _tool_notice("get_weather_forecast", {"city": "서울", "days": 3})
        assert "3" in notice


class TestToLcMessages:
    """_to_lc_messages: DB rows → LangChain 메시지 변환"""

    def test_user_row_becomes_human_message(self):
        rows = [{"role": "user", "content": "안녕"}]
        msgs = _to_lc_messages(rows)
        assert len(msgs) == 1
        assert isinstance(msgs[0], HumanMessage)
        assert msgs[0].content == "안녕"

    def test_agent_row_becomes_ai_message(self):
        rows = [{"role": "agent", "content": "반가워요"}]
        msgs = _to_lc_messages(rows)
        assert isinstance(msgs[0], AIMessage)
        assert msgs[0].content == "반가워요"

    def test_alternating_messages_preserved(self):
        rows = [
            {"role": "user", "content": "질문1"},
            {"role": "agent", "content": "답변1"},
            {"role": "user", "content": "질문2"},
        ]
        msgs = _to_lc_messages(rows)
        assert len(msgs) == 3
        assert isinstance(msgs[0], HumanMessage)
        assert isinstance(msgs[1], AIMessage)
        assert isinstance(msgs[2], HumanMessage)

    def test_empty_rows_returns_empty_list(self):
        assert _to_lc_messages([]) == []

    def test_content_preserved_exactly(self):
        long_text = "긴 텍스트 " * 100
        rows = [{"role": "user", "content": long_text}]
        msgs = _to_lc_messages(rows)
        assert msgs[0].content == long_text


class TestUserText:
    """_user_text: TaskSendParams에서 텍스트 추출"""

    def test_extracts_single_text_part(self):
        params = TaskSendParams(
            message=Message(role="user", parts=[TextPart(text="안녕하세요")])
        )
        assert _user_text(params) == "안녕하세요"

    def test_joins_multiple_text_parts(self):
        params = TaskSendParams(
            message=Message(
                role="user",
                parts=[TextPart(text="파트1"), TextPart(text="파트2")],
            )
        )
        assert _user_text(params) == "파트1 파트2"

    def test_empty_parts_returns_empty_string(self):
        params = TaskSendParams(
            message=Message(role="user", parts=[TextPart(text="")])
        )
        assert _user_text(params) == ""


class TestRegisterMcpToolNames:
    def test_registers_tool_names(self):
        _register_mcp_tool_names(["tool_a", "tool_b"])
        assert "tool_a" in _MCP_TOOL_NAMES
        assert "tool_b" in _MCP_TOOL_NAMES

    def test_accumulates_registrations(self):
        _register_mcp_tool_names(["tool_a"])
        _register_mcp_tool_names(["tool_b"])
        assert "tool_a" in _MCP_TOOL_NAMES
        assert "tool_b" in _MCP_TOOL_NAMES

    def test_empty_list_does_not_fail(self):
        _register_mcp_tool_names([])
        assert len(_MCP_TOOL_NAMES) == 0
