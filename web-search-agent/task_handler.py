"""
task_handler — Web Search Agent용 A2A 태스크 처리 (Stateless).

LangGraph ReAct 에이전트로 검색 → 크롤 → 압축 → reflection(필요시 재검색) → 최종 응답을 수행합니다.
"""
import uuid
import logging
from typing import AsyncGenerator

import task_store
from agent import planner
from models import (
    TaskSendParams,
    Message,
    TextPart,
    Artifact,
    TaskStatus,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
)

logger = logging.getLogger(__name__)


def _make_langfuse_handler(task_id: str):
    """Langfuse CallbackHandler를 버전 호환적으로 생성. 설치/구성이 없으면 None."""
    # langfuse 3.x
    try:
        from langfuse.langchain import CallbackHandler  # type: ignore
        try:
            return CallbackHandler(trace_context={"trace_id": task_id})
        except TypeError:
            return CallbackHandler()
    except ImportError:
        pass
    # langfuse 2.x
    try:
        from langfuse.callback import CallbackHandler  # type: ignore
        return CallbackHandler()
    except ImportError:
        return None
    except Exception as e:
        logger.warning("Langfuse handler 비활성화: %s", e)
        return None


def _user_text(params: TaskSendParams) -> str:
    return " ".join(p.text for p in params.message.parts if p.type == "text")


def _tool_notice(tool_name: str, tool_input: dict) -> str:
    icons = {
        "search_web": "🔍",
        "fetch_url": "🌐",
        "compress_text": "🗜️",
        "get_datetime": "🕐",
    }
    icon = icons.get(tool_name, "🔧")

    if tool_name == "search_web":
        query = tool_input.get("query", "")
        n = tool_input.get("max_results", 5)
        detail = f'**SearXNG 검색**: "{query}" (top {n})'
    elif tool_name == "fetch_url":
        url = tool_input.get("url", "")
        detail = f"**Crawl4AI 본문 추출**: {url}"
    elif tool_name == "compress_text":
        detail = "**LLM 압축 실행**: 긴 본문을 핵심 위주로 축약합니다."
    elif tool_name == "get_datetime":
        tz = tool_input.get("timezone", "Asia/Seoul")
        detail = f"**날짜/시간 조회**: {tz}"
    else:
        detail = f"**{tool_name}** 실행..."

    return f"\n> {icon} {detail}\n\n"


def _make_artifact(task_id: str, index: int, text: str, last: bool = False) -> dict:
    return TaskArtifactUpdateEvent(
        task_id=task_id,
        artifact=Artifact(index=index, parts=[TextPart(text=text)], last_chunk=last),
    ).model_dump()


async def handle_tasks_send_subscribe(
    params: TaskSendParams,
) -> AsyncGenerator[dict, None]:
    task_id = params.id or str(uuid.uuid4())
    model = (params.metadata or {}).get("model", planner.DEFAULT_MODEL)
    user_text = _user_text(params)

    task_store.create_task(task_id, params.message, params.session_id)

    yield TaskStatusUpdateEvent(
        task_id=task_id, status=TaskStatus(state="submitted")
    ).model_dump()

    task_store.update_status(task_id, "working")
    yield TaskStatusUpdateEvent(
        task_id=task_id, status=TaskStatus(state="working")
    ).model_dump()

    graph = planner.build_graph(model)
    messages = planner.build_messages(user_text)

    langfuse_handler = _make_langfuse_handler(task_id)
    callbacks = [langfuse_handler] if langfuse_handler else []

    accumulated = ""
    chunk_index = 0

    try:
        async for event in graph.astream_events(
            {"messages": messages},
            version="v2",
            config={
                "callbacks": callbacks,
                "recursion_limit": 20,
            },
        ):
            kind = event["event"]

            if kind == "on_tool_start":
                tool_name = event.get("name", "")
                tool_input = event["data"].get("input", {})
                notice = _tool_notice(tool_name, tool_input)
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
                yield _make_artifact(task_id, chunk_index, content)
                chunk_index += 1

    except Exception as e:
        from langgraph.errors import GraphRecursionError
        if isinstance(e, GraphRecursionError):
            error_msg = "ReAct 루프 한도(20회)에 도달했습니다. 질문을 더 구체적으로 입력해 주세요."
        else:
            logger.exception("Streaming error")
            error_msg = f"검색 처리 중 오류가 발생했습니다: {e}"
        accumulated += error_msg
        yield _make_artifact(task_id, chunk_index, error_msg)
        chunk_index += 1

    yield _make_artifact(task_id, chunk_index, "", last=True)

    agent_message = Message(role="agent", parts=[TextPart(text=accumulated)])
    task_store.append_message(task_id, agent_message)
    task_store.update_status(task_id, "completed")

    yield TaskStatusUpdateEvent(
        task_id=task_id, status=TaskStatus(state="completed"), final=True
    ).model_dump()
