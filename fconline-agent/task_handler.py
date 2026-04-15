"""
task_handler — A2A 태스크 처리.

LangGraph ReAct agent를 통해 도구 선택/실행 후 응답을 생성합니다.
"""
import uuid
import logging
from typing import AsyncGenerator

from langchain_core.messages import HumanMessage, AIMessage
from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler

import task_store
from agent import planner
from models import (
    Task,
    TaskSendParams,
    Message,
    TextPart,
    Artifact,
    TaskStatus,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
)

logger = logging.getLogger(__name__)


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _user_text(params: TaskSendParams) -> str:
    return " ".join(p.text for p in params.message.parts if p.type == "text")


def _tool_notice(tool_name: str, tool_input: dict) -> str:
    """도구 실행 알림 텍스트 생성 (스트리밍 표시용, blockquote 형식)."""
    icons = {"get_datetime": "🕐", "calculator": "🧮", "web_search": "🔍"}
    icon = icons.get(tool_name, "🔧")

    if tool_name == "web_search":
        query = tool_input.get("query", "")
        detail = f'**웹 검색 툴 실행**: "{query}"'
    elif tool_name == "calculator":
        expr = tool_input.get("expression", "")
        detail = f"**계산 툴 실행**: `{expr}`"
    elif tool_name == "get_datetime":
        tz = tool_input.get("timezone", "Asia/Seoul")
        detail = f"**날짜/시간 조회 툴 실행**: {tz}"
    else:
        detail = f"**{tool_name}** 실행..."

    return f"\n> {icon} {detail}\n\n"


def _make_artifact(task_id: str, index: int, text: str, last: bool = False) -> dict:
    return TaskArtifactUpdateEvent(
        task_id=task_id,
        artifact=Artifact(index=index, parts=[TextPart(text=text)], last_chunk=last),
    ).model_dump()


# ── message/stream (SSE 스트리밍) ────────────────────────────────────────────

async def handle_tasks_send_subscribe(
    params: TaskSendParams,
) -> AsyncGenerator[dict, None]:
    task_id = params.id or str(uuid.uuid4())
    model = (params.metadata or {}).get("model", planner.DEFAULT_MODEL)
    user_text = _user_text(params)

    task = task_store.create_task(task_id, params.message, params.session_id)

    yield TaskStatusUpdateEvent(
        task_id=task_id, status=TaskStatus(state="submitted")
    ).model_dump()

    task_store.update_status(task_id, "working")
    yield TaskStatusUpdateEvent(
        task_id=task_id, status=TaskStatus(state="working")
    ).model_dump()

    graph = planner.build_graph(model)
    messages = planner.build_messages(user_text)

    langfuse_handler = LangfuseCallbackHandler(
        trace_context={"trace_id": task_id},
    )

    accumulated = ""
    streamed = ""
    chunk_index = 0

    async for event in graph.astream_events(
        {"messages": messages},
        version="v2",
        config={"callbacks": [langfuse_handler]},
    ):
        kind = event["event"]

        if kind == "on_tool_start":
            tool_name = event.get("name", "")
            print(f"[TOOL START] {tool_name}")
            tool_input = event["data"].get("input", {})
            notice = _tool_notice(tool_name, tool_input)
            streamed += notice
            yield _make_artifact(task_id, chunk_index, notice)
            chunk_index += 1

        elif kind == "on_chat_model_stream":
            chunk = event["data"].get("chunk")
            if not chunk:
                continue
            content = chunk.content
            if not isinstance(content, str) or not content:
                continue
            accumulated += content
            streamed += content
            yield _make_artifact(task_id, chunk_index, content)
            chunk_index += 1

    yield _make_artifact(task_id, chunk_index, "", last=True)

    agent_message = Message(role="agent", parts=[TextPart(text=accumulated)])
    task_store.append_message(task_id, agent_message)
    task_store.update_status(task_id, "completed")

    yield TaskStatusUpdateEvent(
        task_id=task_id, status=TaskStatus(state="completed"), final=True
    ).model_dump()
