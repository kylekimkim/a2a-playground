"""
TDD: A2A 라우터 통합 테스트 (FastAPI TestClient)

실제 LangGraph 에이전트 실행 없이 task_handler를 mock 처리합니다.
"""
import json
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── app 픽스처 ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """DB, MCP 초기화 없이 앱만 로드하는 TestClient"""
    with patch("database.init_db", AsyncMock()), \
         patch("database.close_db", AsyncMock()), \
         patch("agent.tools.mcp_tools.init_mcp_client", AsyncMock()), \
         patch("agent.tools.mcp_tools.close_mcp_client", AsyncMock()):
        from main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


def _make_payload(method="message/stream", params=None, req_id="req-1"):
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": method,
        "params": params or {
            "message": {"role": "user", "parts": [{"type": "text", "text": "안녕"}]}
        },
    }


async def _noop_handler(params):
    """아무 이벤트도 생성하지 않는 더미 핸들러"""
    return
    yield  # async generator


async def _simple_handler(params):
    """submitted → completed 이벤트만 생성하는 핸들러"""
    yield {"type": "task_status_update", "task_id": "t-1", "status": {"state": "submitted"}, "final": False}
    yield {"type": "task_artifact_update", "task_id": "t-1", "artifact": {"index": 0, "parts": [{"type": "text", "text": "응답"}], "last_chunk": True}}
    yield {"type": "task_status_update", "task_id": "t-1", "status": {"state": "completed"}, "final": True}


# ── JSON-RPC 파싱 오류 ──────────────────────────────────────────────────────────

class TestJsonRpcParseErrors:
    def test_empty_body_returns_200_with_error(self, client):
        resp = client.post("/chat", content=b"", headers={"Content-Type": "application/json"})
        # JSON-RPC 에러는 HTTP 200 반환
        assert resp.status_code == 200

    def test_invalid_json_body(self, client):
        resp = client.post("/chat", content=b"{invalid", headers={"Content-Type": "application/json"})
        assert resp.status_code == 200

    def test_wrong_jsonrpc_version(self, client):
        payload = {"jsonrpc": "1.0", "id": "1", "method": "message/stream",
                   "params": {"message": {"role": "user", "parts": [{"type": "text", "text": "hi"}]}}}
        resp = client.post("/chat", json=payload)
        assert resp.status_code == 200

    def test_missing_message_in_params(self, client):
        payload = _make_payload(params={"session_id": "room-1"})
        resp = client.post("/chat", json=payload)
        # params 검증 실패 → -32602
        assert resp.status_code == 200


# ── 정상 스트리밍 요청 ──────────────────────────────────────────────────────────

class TestValidStreamingRequest:
    def test_returns_text_event_stream_content_type(self, client):
        with patch("task_handler.handle_tasks_send_subscribe", side_effect=_simple_handler):
            resp = client.post("/chat", json=_make_payload())
        assert "text/event-stream" in resp.headers.get("content-type", "")

    def test_sse_no_cache_header(self, client):
        with patch("task_handler.handle_tasks_send_subscribe", side_effect=_simple_handler):
            resp = client.post("/chat", json=_make_payload())
        assert resp.headers.get("cache-control") == "no-cache"

    def test_sse_response_contains_data_lines(self, client):
        with patch("task_handler.handle_tasks_send_subscribe", side_effect=_simple_handler):
            resp = client.post("/chat", json=_make_payload())
        assert "data:" in resp.text

    def test_sse_events_are_valid_json(self, client):
        with patch("task_handler.handle_tasks_send_subscribe", side_effect=_simple_handler):
            resp = client.post("/chat", json=_make_payload())

        for line in resp.text.splitlines():
            if line.startswith("data:"):
                data = line[5:].strip()
                parsed = json.loads(data)  # ValueError 발생 시 테스트 실패
                assert "type" in parsed

    def test_submitted_event_present(self, client):
        with patch("task_handler.handle_tasks_send_subscribe", side_effect=_simple_handler):
            resp = client.post("/chat", json=_make_payload())

        events = [json.loads(line[5:].strip())
                  for line in resp.text.splitlines() if line.startswith("data:")]
        states = [e["status"]["state"] for e in events if e.get("type") == "task_status_update"]
        assert "submitted" in states

    def test_completed_event_present(self, client):
        with patch("task_handler.handle_tasks_send_subscribe", side_effect=_simple_handler):
            resp = client.post("/chat", json=_make_payload())

        events = [json.loads(line[5:].strip())
                  for line in resp.text.splitlines() if line.startswith("data:")]
        states = [e["status"]["state"] for e in events if e.get("type") == "task_status_update"]
        assert "completed" in states

    def test_artifact_event_contains_text(self, client):
        with patch("task_handler.handle_tasks_send_subscribe", side_effect=_simple_handler):
            resp = client.post("/chat", json=_make_payload())

        events = [json.loads(line[5:].strip())
                  for line in resp.text.splitlines() if line.startswith("data:")]
        artifacts = [e for e in events if e.get("type") == "task_artifact_update"]
        assert any("응답" in str(a) for a in artifacts)

    def test_session_id_passed_to_handler(self, client):
        captured = []

        async def capture_handler(params):
            captured.append(params)
            yield {"type": "task_status_update", "task_id": "t", "status": {"state": "completed"}, "final": True}

        payload = _make_payload(params={
            "session_id": "room-abc",
            "message": {"role": "user", "parts": [{"type": "text", "text": "hi"}]},
        })
        with patch("task_handler.handle_tasks_send_subscribe", side_effect=capture_handler):
            client.post("/chat", json=payload)

        assert len(captured) == 1
        assert captured[0].session_id == "room-abc"


# ── 에이전트 카드 ──────────────────────────────────────────────────────────────

class TestAgentCard:
    def test_well_known_returns_200(self, client):
        resp = client.get("/.well-known/agent.json")
        assert resp.status_code == 200

    def test_well_known_returns_json(self, client):
        resp = client.get("/.well-known/agent.json")
        data = resp.json()
        assert isinstance(data, dict)

    def test_agent_card_has_required_fields(self, client):
        resp = client.get("/.well-known/agent.json")
        data = resp.json()
        assert "name" in data
        assert "url" in data
        assert "version" in data
