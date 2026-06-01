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
import room_store
from agent import planner, registry
from agent.tools.delegate import stream_delegate
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


def _to_lc_messages(db_rows: list[dict]) -> list:
    """DB 메시지 rows → LangChain HumanMessage / AIMessage 변환."""
    result = []
    for row in db_rows:
        content = row.get("content", "")
        if row["role"] == "user":
            result.append(HumanMessage(content=content))
        else:
            result.append(AIMessage(content=content))
    return result


async def _load_history(session_id: str | None) -> list:
    """채팅방 이전 메시지를 LangChain 메시지 형식으로 반환."""
    if not session_id:
        return []
    rows = await room_store.get_messages(session_id)
    return _to_lc_messages(rows)


async def _persist_user(session_id: str | None, user_text: str) -> None:
    """유저 메시지 DB 저장 및 첫 메시지 시 방 제목 자동 설정."""
    if not session_id:
        return
    room = await room_store.get_room(session_id)
    if room and room["title"] == "New Chat":
        await room_store.update_room_title(session_id, user_text[:40].strip())
    await room_store.save_message(session_id, "user", user_text)


_MCP_TOOL_NAMES: set[str] = set()


def _register_mcp_tool_names(names: list[str]) -> None:
    """MCP 툴 이름을 등록 (init 시점에 호출)."""
    _MCP_TOOL_NAMES.update(names)


def _tool_notice(tool_name: str, tool_input: dict) -> str:
    """도구 실행 알림 텍스트 생성 (스트리밍 표시용, blockquote 형식)."""
    # MCP 툴 여부 먼저 확인
    if tool_name in _MCP_TOOL_NAMES:
        if tool_name == "extract_text_from_file":
            file_path = tool_input.get("file_path", "")
            import os
            file_name = os.path.basename(file_path) if file_path else ""
            detail = f"**MCP 호출**  `extract_text_from_file`: {file_name}"
        elif tool_name == "get_file_metadata":
            file_path = tool_input.get("file_path", "")
            import os
            file_name = os.path.basename(file_path) if file_path else ""
            detail = f"**MCP 호출**  `get_file_metadata`: {file_name}"
        elif tool_name == "get_current_weather":
            city = tool_input.get("city", "")
            detail = f"**MCP 호출**  `get_current_weather`: {city}"
        elif tool_name == "get_weather_forecast":
            city = tool_input.get("city", "")
            days = tool_input.get("days", 3)
            detail = f"**MCP 호출**  `get_weather_forecast`: {city} ({days}일)"
        elif tool_name == "get_weather_by_coords":
            lat = tool_input.get("lat", "")
            lon = tool_input.get("lon", "")
            detail = f"**MCP 호출**  `get_weather_by_coords`: ({lat}, {lon})"
        elif tool_name == "create_document":
            fname = tool_input.get("filename", "")
            fmt = tool_input.get("format", "docx")
            detail = f"**MCP 호출**  `create_document`: {fname}.{fmt}"
        else:
            detail = f"**MCP 호출**  `{tool_name}`"
        return f"\n> 🔌 {detail}\n\n"

    icons = {"get_datetime": "🕐", "calculator": "🧮", "delegate_task": "🤖"}
    icon = icons.get(tool_name, "🔧")

    if tool_name == "calculator":
        expr = tool_input.get("expression", "")
        detail = f"**계산 툴 실행**: `{expr}`"
    elif tool_name == "get_datetime":
        tz = tool_input.get("timezone", "Asia/Seoul")
        detail = f"**날짜/시간 조회 툴 실행**: {tz}"
    elif tool_name == "delegate_task":
        target_url = tool_input.get("target_url", "")
        from agent import registry
        agent_name = registry.get_agent_name(target_url)
        detail = f"**{agent_name}**에게 작업을 위임하고 있습니다..."
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

    # 히스토리 로드 → 유저 메시지 저장 (순서 중요: 히스토리 먼저)
    lc_history = await _load_history(params.session_id)
    await _persist_user(params.session_id, user_text)

    yield TaskStatusUpdateEvent(
        task_id=task_id, status=TaskStatus(state="submitted")
    ).model_dump()

    task_store.update_status(task_id, "working")
    yield TaskStatusUpdateEvent(
        task_id=task_id, status=TaskStatus(state="working")
    ).model_dump()

    # LangGraph 그래프 생성 및 메시지 구성 시작
    graph = planner.build_graph(model)
    messages = planner.build_messages(lc_history, user_text)

    langfuse_handler = LangfuseCallbackHandler()

    accumulated = ""   # DB 저장용 (LLM 텍스트만)
    streamed = ""      # 화면 표시용 (툴 알림 포함)
    chunk_index = 0

    # passthrough 에이전트로 위임 시 그래프 중단 후 직접 forward할 정보
    passthrough_url: str | None = None
    passthrough_task_desc: str | None = None

    try:
        async for event in graph.astream_events(
            {"messages": messages},
            version="v2",
            config={"callbacks": [langfuse_handler], "recursion_limit": 10},
        ):
            kind = event["event"]

            # ── 도구 실행 시작 알림 ──────────────────────────────────────
            if kind == "on_tool_start":
                tool_name = event.get("name", "")
                print(f"[TOOL START] {tool_name}")
                tool_input = event["data"].get("input", {})

                # passthrough 분기: 대상이 stream-through 가능한 에이전트면
                # 위임 알림만 보내고 그래프를 즉시 중단 → 아래에서 직접 SSE forward
                if tool_name == "delegate_task":
                    candidate_url = tool_input.get("target_url", "")
                    if candidate_url and registry.is_passthrough_agent(candidate_url):
                        notice = _tool_notice(tool_name, tool_input)
                        streamed += notice
                        yield _make_artifact(task_id, chunk_index, notice)
                        chunk_index += 1
                        passthrough_url = candidate_url
                        passthrough_task_desc = (
                            tool_input.get("task_description") or user_text
                        )
                        break

                notice = _tool_notice(tool_name, tool_input)
                streamed += notice
                yield _make_artifact(task_id, chunk_index, notice)
                chunk_index += 1

            # ── 도구 실행 완료 — 다운로드 링크 직접 주입 ────────────────
            elif kind == "on_tool_end":
                tool_name = event.get("name", "")
                if tool_name == "create_document":
                    import re as _re

                    def _to_str(v) -> str:
                        if isinstance(v, str):
                            return v
                        if isinstance(v, list):
                            return " ".join(_to_str(i) for i in v)
                        if hasattr(v, "content"):
                            return _to_str(v.content)
                        return str(v)

                    output_str = _to_str(event["data"].get("output", ""))
                    # 파일명만 추출 ("/download/파일명.확장자" 패턴)
                    fname_match = _re.search(r'/download/([A-Za-z0-9_\-]+\.[a-z]+)', output_str)
                    if fname_match:
                        filename = fname_match.group(1)
                        url = f"/download/{filename}"
                        link = f"\n\n[⬇ {filename} 다운로드]({url})\n\n"
                        accumulated += link
                        streamed += link
                        yield _make_artifact(task_id, chunk_index, link)
                        chunk_index += 1

            # ── LLM 토큰 스트리밍 ────────────────────────────────────────
            elif kind == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                if not chunk:
                    continue
                content = chunk.content
                # tool_call JSON 스트림(빈 문자열 또는 list 타입)은 건너뜀
                if not isinstance(content, str) or not content:
                    continue
                accumulated += content
                streamed += content
                yield _make_artifact(task_id, chunk_index, content)
                chunk_index += 1

    except Exception as e:
        from langgraph.errors import GraphRecursionError
        if isinstance(e, GraphRecursionError):
            error_msg = "요청을 처리하는 중 도구 호출 한도에 도달했습니다. 질문을 더 구체적으로 입력하거나 다시 시도해 주세요."
        else:
            logger.exception("Streaming error")
            error_msg = "요청을 처리하는 중 오류가 발생했습니다. 다시 시도해 주세요."
        accumulated += error_msg
        yield _make_artifact(task_id, chunk_index, error_msg)
        chunk_index += 1

    # ── passthrough stream-through: 오케스트레이터 LLM 2차 합성을 건너뜀 ─────
    if passthrough_url:
        try:
            async for chunk in stream_delegate(passthrough_url, passthrough_task_desc):
                accumulated += chunk
                streamed += chunk
                yield _make_artifact(task_id, chunk_index, chunk)
                chunk_index += 1
        except Exception as e:
            logger.exception("passthrough stream-through 실패")
            err = f"\n\n[stream-through 실패: {e}]"
            accumulated += err
            yield _make_artifact(task_id, chunk_index, err)
            chunk_index += 1

    # ── 종료 ─────────────────────────────────────────────────────────
    yield _make_artifact(task_id, chunk_index, "", last=True)

    agent_message = Message(role="agent", parts=[TextPart(text=accumulated)])
    task_store.append_message(task_id, agent_message)
    task_store.update_status(task_id, "completed")

    if params.session_id:
        await room_store.save_message(params.session_id, "agent", accumulated)

    yield TaskStatusUpdateEvent(
        task_id=task_id, status=TaskStatus(state="completed"), final=True
    ).model_dump()
