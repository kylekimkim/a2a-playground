"""
Planner Agent — LangGraph 기반 ReAct 에이전트.

흐름:
  사용자 입력
    → LangGraph ReAct Graph
        → LLM (도구 필요 여부 판단)
        → Tool 실행 (datetime / calculator / delegate_task / MCP tools)
        → LLM (결과 기반 최종 답변 생성)
    → SSE 스트리밍 응답
"""
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent

from .tools import get_all_tools
from .registry import get_available_agents_prompt_snippet

DEFAULT_MODEL = os.getenv("MODEL_NAME", "gpt-5.4-mini")

_SYSTEM_PROMPT_BASE = """당신은 고급 AI 어시스턴트 겸 플래너입니다.
사용자의 요청을 분석하고, 최적의 도구를 선택하여 정확하고 유용한 답변을 제공합니다.

[플래너 원칙]
1. 요청 분석: 사용자의 의도와 필요한 정보를 파악합니다.
2. 도구 계획: 어떤 도구를 어떤 순서로 사용할지 결정합니다.
3. 실행 & 검증: 도구 결과를 확인하고 필요 시 추가 도구를 사용합니다.
4. 답변 합성: 수집된 정보를 바탕으로 명확하고 유용한 최종 답변을 작성합니다.

[도구 사용 기준]
- get_datetime : 현재 날짜, 시간, 요일이 필요할 때
- calculator   : 수치 계산, 수식 평가가 필요할 때 (복잡한 계산은 반드시 사용)
- delegate_task : 다른 특화된 에이전트에게 작업을 위임할 때 사용합니다. 사용할 수 있는 에이전트 목록은 하단을 참고하세요.
  · 본 오케스트레이터는 자체 웹 검색 도구를 보유하지 않습니다.
  · 최신 뉴스, 실시간 정보, 사실 확인, 현재 이벤트, URL 본문 읽기 등 웹에서 정보를 가져와야 하는 모든 요청은
    반드시 하단 목록의 'Web Search ReAct Agent'에게 delegate_task로 위임하세요.
{mcp_tool_descriptions}
- 직접 답변               : 일반 지식, 개념 설명, 코드 작성, 창작 등 도구 불필요 시

[답변 지침]
- 사용자의 언어(한국어/영어)로 답변합니다.
- 도구를 사용한 경우 결과를 명확히 인용하며, 다른 에이전트에게 위임한 경우 그 출처(예: '운세 에이전트에 따르면...')를 밝힙니다.
- 불확실한 정보는 솔직하게 밝힙니다.
- 답변은 간결하되 필요한 내용을 모두 포함합니다."""

_MCP_TOOL_DESCRIPTIONS = {
    "extract_text_from_file": "- extract_text_from_file  : 로컬 파일(PDF, Word, Excel, PPT, 이미지 등)에서 텍스트를 추출할 때\n",
    "extract_text_from_url":  "- extract_text_from_url   : 원격 URL의 문서에서 텍스트를 추출할 때\n",
    "get_file_metadata":      "- get_file_metadata       : 파일의 메타데이터(MIME 타입, 작성자, 페이지 수 등)를 조회할 때\n",
    "get_current_weather":    "- get_current_weather     : 도시명 또는 좌표로 현재 날씨를 조회할 때\n",
    "get_weather_forecast":   "- get_weather_forecast    : 도시명으로 최대 5일간 날씨 예보를 조회할 때\n",
    "get_weather_by_coords":  "- get_weather_by_coords   : 위도/경도로 현재 날씨를 조회할 때\n",
    "create_document":        "- create_document         : 사용자가 문서 작성·저장·다운로드를 요청할 때. format은 docx/xlsx/txt/md 중 선택.\n",
}


def _build_system_prompt() -> str:
    """현재 로드된 MCP 툴 목록을 기준으로 시스템 프롬프트를 동적으로 생성합니다."""
    from .tools.mcp_tools import get_mcp_tools
    available_mcp_names = {t.name for t in get_mcp_tools()}
    mcp_lines = "".join(
        desc for name, desc in _MCP_TOOL_DESCRIPTIONS.items()
        if name in available_mcp_names
    )
    return _SYSTEM_PROMPT_BASE.format(mcp_tool_descriptions=mcp_lines)



def build_graph(model: str = DEFAULT_MODEL):
    """LangGraph ReAct agent 그래프를 생성합니다."""
    llm = ChatOpenAI(
        model=model,
        streaming=True,
        temperature=0.7,
        api_key=os.environ["OPENAI_API_KEY"],
    )
    tools = get_all_tools()
    return create_react_agent(model=llm, tools=tools)


def build_messages(lc_history: list, user_text: str) -> list:
    """SystemMessage + 대화 히스토리 + 현재 유저 메시지를 합쳐 반환합니다."""
    dynamic_agents_info = get_available_agents_prompt_snippet()
    final_prompt = _build_system_prompt() + "\n\n" + dynamic_agents_info
    print(dynamic_agents_info)
    return [SystemMessage(content=final_prompt)] + lc_history + [HumanMessage(content=user_text)]
