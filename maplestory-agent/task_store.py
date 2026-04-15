from models import Task, TaskStatus, Message

_store: dict[str, Task] = {}


def create_task(task_id: str, initial_message: Message, session_id: str | None = None) -> Task:
    task = Task(
        id=task_id,
        session_id=session_id,
        status=TaskStatus(state="submitted"),
        messages=[initial_message],
    )
    _store[task_id] = task
    return task


def get_task(task_id: str) -> Task | None:
    return _store.get(task_id)


def update_status(task_id: str, state: str) -> None:
    task = _store[task_id]
    task.status = TaskStatus(state=state)


def append_message(task_id: str, message: Message) -> None:
    _store[task_id].messages.append(message)


def all_tasks() -> list[Task]:
    return list(_store.values())
