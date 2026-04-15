"""
TDD: Pydantic 데이터 모델 단위 테스트
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pydantic import ValidationError
from models import (
    TextPart,
    Message,
    TaskStatus,
    Artifact,
    Task,
    TaskSendParams,
    JsonRpcRequest,
    JsonRpcError,
    JsonRpcResponse,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
)


class TestTextPart:
    def test_default_type_is_text(self):
        part = TextPart(text="hello")
        assert part.type == "text"

    def test_text_field(self):
        part = TextPart(text="안녕하세요")
        assert part.text == "안녕하세요"

    def test_invalid_type_rejected(self):
        with pytest.raises(ValidationError):
            TextPart(type="image", text="hi")


class TestMessage:
    def test_user_role(self):
        msg = Message(role="user", parts=[TextPart(text="hi")])
        assert msg.role == "user"

    def test_agent_role(self):
        msg = Message(role="agent", parts=[TextPart(text="응답")])
        assert msg.role == "agent"

    def test_invalid_role_rejected(self):
        with pytest.raises(ValidationError):
            Message(role="system", parts=[TextPart(text="x")])

    def test_multiple_parts(self):
        msg = Message(
            role="user",
            parts=[TextPart(text="파트1"), TextPart(text="파트2")],
        )
        assert len(msg.parts) == 2


class TestTaskStatus:
    @pytest.mark.parametrize("state", ["submitted", "working", "completed", "failed", "canceled"])
    def test_valid_states(self, state):
        ts = TaskStatus(state=state)
        assert ts.state == state

    def test_invalid_state_rejected(self):
        with pytest.raises(ValidationError):
            TaskStatus(state="unknown")

    def test_optional_message_defaults_none(self):
        ts = TaskStatus(state="submitted")
        assert ts.message is None


class TestArtifact:
    def test_default_index_zero(self):
        a = Artifact()
        assert a.index == 0

    def test_default_last_chunk_false(self):
        a = Artifact()
        assert a.last_chunk is False

    def test_last_chunk_true(self):
        a = Artifact(last_chunk=True)
        assert a.last_chunk is True

    def test_parts_field(self):
        a = Artifact(parts=[TextPart(text="chunk")])
        assert len(a.parts) == 1
        assert a.parts[0].text == "chunk"


class TestTask:
    def test_auto_generates_id(self):
        task = Task(status=TaskStatus(state="submitted"))
        assert task.id is not None
        assert len(task.id) > 0

    def test_session_id_optional(self):
        task = Task(status=TaskStatus(state="submitted"))
        assert task.session_id is None

    def test_empty_messages_by_default(self):
        task = Task(status=TaskStatus(state="submitted"))
        assert task.messages == []


class TestTaskSendParams:
    def test_minimal_valid(self):
        params = TaskSendParams(
            message=Message(role="user", parts=[TextPart(text="hello")])
        )
        assert params.session_id is None
        assert params.metadata is None

    def test_with_session_id(self):
        params = TaskSendParams(
            session_id="room-123",
            message=Message(role="user", parts=[TextPart(text="hello")]),
        )
        assert params.session_id == "room-123"

    def test_with_metadata(self):
        params = TaskSendParams(
            message=Message(role="user", parts=[TextPart(text="hi")]),
            metadata={"model": "gpt-4o-mini"},
        )
        assert params.metadata["model"] == "gpt-4o-mini"

    def test_missing_message_rejected(self):
        with pytest.raises(ValidationError):
            TaskSendParams()


class TestJsonRpcRequest:
    def test_valid_request(self):
        req = JsonRpcRequest(method="message/stream")
        assert req.jsonrpc == "2.0"

    def test_method_field(self):
        req = JsonRpcRequest(method="message/stream", id="123")
        assert req.method == "message/stream"
        assert req.id == "123"

    def test_params_optional(self):
        req = JsonRpcRequest(method="ping")
        assert req.params is None

    def test_invalid_jsonrpc_version(self):
        with pytest.raises(ValidationError):
            JsonRpcRequest(jsonrpc="1.0", method="ping")


class TestJsonRpcResponse:
    def test_success_response(self):
        resp = JsonRpcResponse(id="1", result={"status": "ok"})
        assert resp.error is None
        assert resp.result["status"] == "ok"

    def test_error_response(self):
        err = JsonRpcError(code=-32603, message="Internal error")
        resp = JsonRpcResponse(id="1", error=err)
        assert resp.result is None
        assert resp.error.code == -32603

    def test_serialization(self):
        resp = JsonRpcResponse(id="req-1", result={"ok": True})
        data = resp.model_dump()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "req-1"


class TestSseEvents:
    def test_task_status_update_event(self):
        event = TaskStatusUpdateEvent(
            task_id="t-1",
            status=TaskStatus(state="working"),
        )
        assert event.type == "task_status_update"
        assert event.final is False

    def test_task_status_update_final(self):
        event = TaskStatusUpdateEvent(
            task_id="t-1",
            status=TaskStatus(state="completed"),
            final=True,
        )
        assert event.final is True

    def test_task_artifact_update_event(self):
        event = TaskArtifactUpdateEvent(
            task_id="t-1",
            artifact=Artifact(parts=[TextPart(text="token")]),
        )
        assert event.type == "task_artifact_update"
        assert event.artifact.parts[0].text == "token"

    def test_events_serialize_to_dict(self):
        event = TaskStatusUpdateEvent(
            task_id="t-1", status=TaskStatus(state="submitted")
        )
        data = event.model_dump()
        assert data["type"] == "task_status_update"
        assert data["task_id"] == "t-1"
