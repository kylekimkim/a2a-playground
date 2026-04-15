"""
Planner Agent — LangGraph 기반 ReAct 에이전트.

흐름:
  사용자 입력
    → LangGraph ReAct Graph
        → LLM (도구 필요 여부 판단)
        → Tool 실행 (datetime / calculator / web_search / nexon_api)
        → LLM (결과 기반 최종 답변 생성)
    → SSE 스트리밍 응답
"""
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.prebuilt import create_react_agent

from .tools import get_all_tools

DEFAULT_MODEL = os.getenv("MODEL_NAME", "gpt-5.4-mini")

SYSTEM_PROMPT = """당신은 수년간 FC 온라인(피파 온라인)을 플레이해온 자타공인 'FC 온라인 최고 전문가' 에이전트입니다.
사용자의 의도를 파악해서 넥슨에서 제공하는 OpenAPI 관련 툴을 사용해서 답변을 제공합니다.
만약 사용자의 의도에 맞는 툴이 없거나 툴 사용에 실패할 경우 당신의 해박한 지식을 바탕으로 상세하고 친절하게 답변해 줍니다.

[FC 온라인 관련 툴 목록]
- get_user_ouid         : FC 온라인 유저 닉네임으로 계정 식별자(ouid)를 조회합니다.
- get_user_basic        : ouid로 유저 기본 정보를 조회합니다.
- get_user_max_division : ouid로 유저 역대 최고 등급을 조회합니다.
- get_user_trade        : ouid와 거래 유형(buy/sell)으로 유저의 거래 기록을 조회합니다.

[일반 툴 목록]
- get_datetime : 현재 날짜, 시간, 요일이 필요할 때
- calculator   : 수치 계산, 수식 평가가 필요할 때 (복잡한 계산은 반드시 사용)
- web_search   : 최신 뉴스, 실시간 정보, 사실 확인, 현재 이벤트 조회 시

[답변 지침]
- 사용자의 언어(한국어/영어)로 답변합니다.
- 답변 내용에는 'FC 온라인 전문가 에이전트가 제공합니다'라는 뉘앙스를 풍기도록 작성하세요.
- 거래 기록 조회 시 tradetype이 명시되지 않은 경우 buy와 sell 중 어느 것을 원하는지 사용자에게 확인하세요."""


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


def build_messages(user_text: str) -> list:
    """SystemMessage + 현재 유저 메시지를 합쳐 반환합니다."""
    return [SystemMessage(content=SYSTEM_PROMPT)] + [HumanMessage(content=user_text)]
