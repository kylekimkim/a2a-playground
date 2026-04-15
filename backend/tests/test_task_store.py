"""
TDD: task_store 인메모리 저장소 단위 테스트
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import task_store
from models import Message, TextPart


@pytest.fixture(autouse=True)
def clear_store():
    """각 테스트 전후 저장소 초기화"""
    task_store._store.clear()
    yield
    task_store._store.clear()


def _make_message(text: str = "테스트 메시지") -> Message:
    return Message(role="user", parts=[TextPart(text=text)])


class TestCreateTask:
    def test_creates_task_with_given_id(self):
        task = task_store.create_task("task-001", _make_message())
        assert task.id == "task-001"

    def test_initial_state_is_submitted(self):
        task = task_store.create_task("task-002", _make_message())
        assert task.status.state == "submitted"

    def test_initial_message_stored(self):
        msg = _make_message("hello")
        task = task_store.create_task("task-003", msg)
        assert len(task.messages) == 1
        assert task.messages[0].parts[0].text == "hello"

    def test_session_id_stored(self):
        task = task_store.create_task("task-004", _make_message(), session_id="room-abc")
        assert task.session_id == "room-abc"

    def test_no_session_id_defaults_none(self):
        task = task_store.create_task("task-005", _make_message())
        assert task.session_id is None

    def test_task_stored_in_store(self):
        task_store.create_task("task-006", _make_message())
        assert "task-006" in task_store._store


class TestGetTask:
    def test_returns_created_task(self):
        task_store.create_task("task-007", _make_message())
        retrieved = task_store.get_task("task-007")
        assert retrieved is not None
        assert retrieved.id == "task-007"

    def test_returns_none_for_unknown_id(self):
        result = task_store.get_task("nonexistent-id")
        assert result is None


class TestUpdateStatus:
    def test_status_updated_to_working(self):
        task_store.create_task("task-008", _make_message())
        task_store.update_status("task-008", "working")
        assert task_store.get_task("task-008").status.state == "working"

    def test_status_updated_to_completed(self):
        task_store.create_task("task-009", _make_message())
        task_store.update_status("task-009", "completed")
        assert task_store.get_task("task-009").status.state == "completed"

    def test_status_updated_to_failed(self):
        task_store.create_task("task-010", _make_message())
        task_store.update_status("task-010", "failed")
        assert task_store.get_task("task-010").status.state == "failed"

    def test_status_transitions_submitted_to_working_to_completed(self):
        task_store.create_task("task-011", _make_message())
        task_store.update_status("task-011", "working")
        task_store.update_status("task-011", "completed")
        assert task_store.get_task("task-011").status.state == "completed"


class TestAppendMessage:
    def test_appends_agent_message(self):
        task_store.create_task("task-012", _make_message("user input"))
        agent_msg = Message(role="agent", parts=[TextPart(text="agent reply")])
        task_store.append_message("task-012", agent_msg)
        task = task_store.get_task("task-012")
        assert len(task.messages) == 2
        assert task.messages[1].role == "agent"
        assert task.messages[1].parts[0].text == "agent reply"

    def test_multiple_appends(self):
        task_store.create_task("task-013", _make_message())
        for i in range(3):
            msg = Message(role="agent", parts=[TextPart(text=f"chunk {i}")])
            task_store.append_message("task-013", msg)
        assert len(task_store.get_task("task-013").messages) == 4  # 1 user + 3 agent


class TestAllTasks:
    def test_returns_all_tasks(self):
        task_store.create_task("t-a", _make_message())
        task_store.create_task("t-b", _make_message())
        all_tasks = task_store.all_tasks()
        ids = [t.id for t in all_tasks]
        assert "t-a" in ids
        assert "t-b" in ids

    def test_empty_store_returns_empty_list(self):
        assert task_store.all_tasks() == []

    def test_store_isolation_between_tests(self):
        # autouse fixture가 초기화했으므로 이전 테스트 데이터 없음
        assert len(task_store.all_tasks()) == 0
