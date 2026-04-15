"""
TDD: delegate_task 도구 단위 테스트 (HTTP 요청 mock 처리)
"""
import json
import pytest
from unittest.mock import patch, MagicMock
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.tools.delegate import delegate_task


def _make_sse_lines(text_chunks: list[str], include_final: bool = True) -> list[bytes]:
    """SSE 라인 목록 생성 헬퍼"""
    lines = []
    for i, chunk in enumerate(text_chunks):
        event = {
            "type": "task_artifact_update",
            "task_id": "test-task",
            "artifact": {
                "index": i,
                "parts": [{"type": "text", "text": chunk}],
                "last_chunk": False,
            },
        }
        lines.append(f"data: {json.dumps(event)}".encode())
    if include_final:
        final_event = {
            "type": "task_status_update",
            "task_id": "test-task",
            "status": {"state": "completed"},
            "final": True,
        }
        lines.append(f"data: {json.dumps(final_event)}".encode())
    return lines


def _make_mock_response(sse_lines: list[bytes], status_code: int = 200) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.iter_lines.return_value = iter(sse_lines)
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


class TestDelegateTaskSuccess:
    def test_accumulates_text_chunks(self):
        lines = _make_sse_lines(["안녕", "하세요", "!"])
        mock_resp = _make_mock_response(lines)

        with patch("agent.tools.delegate.requests.post", return_value=mock_resp):
            result = delegate_task.invoke({
                "target_url": "http://127.0.0.1:9001/chat",
                "task_description": "메이플스토리 캐릭터 조회",
            })

        assert "안녕" in result
        assert "하세요" in result
        assert "!" in result

    def test_returns_full_concatenated_text(self):
        lines = _make_sse_lines(["결과: ", "레벨 250"])
        mock_resp = _make_mock_response(lines)

        with patch("agent.tools.delegate.requests.post", return_value=mock_resp):
            result = delegate_task.invoke({
                "target_url": "http://127.0.0.1:9001/chat",
                "task_description": "캐릭터 레벨 조회",
            })

        assert result == "결과: 레벨 250"

    def test_ignores_non_artifact_events(self):
        """status_update 이벤트는 무시하고 artifact 텍스트만 누적"""
        status_event = {
            "type": "task_status_update",
            "task_id": "t",
            "status": {"state": "working"},
            "final": False,
        }
        artifact_event = {
            "type": "task_artifact_update",
            "task_id": "t",
            "artifact": {"index": 0, "parts": [{"type": "text", "text": "응답"}], "last_chunk": False},
        }
        lines = [
            f"data: {json.dumps(status_event)}".encode(),
            f"data: {json.dumps(artifact_event)}".encode(),
        ]
        mock_resp = _make_mock_response(lines, status_code=200)

        with patch("agent.tools.delegate.requests.post", return_value=mock_resp):
            result = delegate_task.invoke({
                "target_url": "http://127.0.0.1:9001/chat",
                "task_description": "테스트",
            })

        assert result == "응답"

    def test_sends_correct_json_rpc_payload(self):
        lines = _make_sse_lines(["ok"])
        mock_resp = _make_mock_response(lines)

        with patch("agent.tools.delegate.requests.post", return_value=mock_resp) as mock_post:
            delegate_task.invoke({
                "target_url": "http://127.0.0.1:9001/chat",
                "task_description": "테스트 설명",
            })

        call_kwargs = mock_post.call_args
        payload = call_kwargs[1]["json"]
        assert payload["jsonrpc"] == "2.0"
        assert payload["method"] == "message/stream"
        assert payload["params"]["message"]["role"] == "user"
        assert payload["params"]["message"]["parts"][0]["text"] == "테스트 설명"

    def test_uses_15_second_timeout(self):
        lines = _make_sse_lines(["ok"])
        mock_resp = _make_mock_response(lines)

        with patch("agent.tools.delegate.requests.post", return_value=mock_resp) as mock_post:
            delegate_task.invoke({
                "target_url": "http://127.0.0.1:9001/chat",
                "task_description": "테스트",
            })

        call_kwargs = mock_post.call_args
        assert call_kwargs[1]["timeout"] == 15

    def test_stream_flag_is_true(self):
        lines = _make_sse_lines(["ok"])
        mock_resp = _make_mock_response(lines)

        with patch("agent.tools.delegate.requests.post", return_value=mock_resp) as mock_post:
            delegate_task.invoke({
                "target_url": "http://127.0.0.1:9001/chat",
                "task_description": "테스트",
            })

        call_kwargs = mock_post.call_args
        assert call_kwargs[1]["stream"] is True


class TestDelegateTaskEmpty:
    def test_empty_response_returns_notice_message(self):
        """에이전트가 빈 텍스트를 반환한 경우"""
        lines = _make_sse_lines([])
        mock_resp = _make_mock_response(lines)

        with patch("agent.tools.delegate.requests.post", return_value=mock_resp):
            result = delegate_task.invoke({
                "target_url": "http://127.0.0.1:9001/chat",
                "task_description": "테스트",
            })

        assert "빈 텍스트" in result or "올바르게" in result


class TestDelegateTaskErrors:
    def test_timeout_returns_error_message(self):
        import requests as req_lib
        with patch("agent.tools.delegate.requests.post",
                   side_effect=req_lib.exceptions.Timeout()):
            result = delegate_task.invoke({
                "target_url": "http://127.0.0.1:9001/chat",
                "task_description": "테스트",
            })

        assert "시간 초과" in result or "응답 대기" in result

    def test_connection_error_returns_error_message(self):
        import requests as req_lib
        with patch("agent.tools.delegate.requests.post",
                   side_effect=req_lib.exceptions.ConnectionError("refused")):
            result = delegate_task.invoke({
                "target_url": "http://127.0.0.1:9001/chat",
                "task_description": "테스트",
            })

        assert "위임 실패" in result

    def test_malformed_json_in_sse_does_not_crash(self):
        """SSE 라인에 잘못된 JSON이 포함되어도 크래시 없이 처리"""
        lines = [b"data: {invalid json}", b"data: {\"artifact\":{\"parts\":[{\"text\":\"정상\"}]}}"]
        mock_resp = _make_mock_response(lines)

        with patch("agent.tools.delegate.requests.post", return_value=mock_resp):
            result = delegate_task.invoke({
                "target_url": "http://127.0.0.1:9001/chat",
                "task_description": "테스트",
            })

        # 크래시 없이 실행되어야 함
        assert isinstance(result, str)
