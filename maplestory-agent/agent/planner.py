"""
Planner Agent — LangGraph 기반 ReAct 에이전트.

흐름:
  사용자 입력
    → LangGraph ReAct Graph
        → LLM (도구 필요 여부 판단)
        → Tool 실행 (datetime / calculator / web_search)
        → LLM (결과 기반 최종 답변 생성)
    → SSE 스트리밍 응답
"""
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent

from .tools import get_all_tools

DEFAULT_MODEL = os.getenv("MODEL_NAME", "gpt-5.4-mini")

SYSTEM_PROMPT = """당신은 수년간 메이플스토리를 플레이해온 자타공인 '메이플스토리 최고 전문가' 에이전트입니다.
사용자가 의도를 파악해서 넥슨에서 제공하는 OpenAPI 관련 툴을 사용해서 답변을 제공합니다. 
만약 사용자의 의도에 맞는 툴이 없거나 툴 사용에 실패 할 경우 당신의 해박한 지식(GPT-5.4-mini의 지식)을 바탕으로 상세하고 친절하게 답변해 줍니다.

[메이플스토리 관련 툴 목록]
- get_character_ocid   : 메이플스토리 캐릭터 이름으로 사용자 고유식별자(ocid)를 조회합니다.
- get_character_basic            : ocid로 캐릭터 기본 정보(이름, 직업, 레벨, 서버 등)를 조회합니다.
- get_character_popularity       : ocid로 캐릭터 인기도 정보를 조회합니다.
- get_character_stat             : ocid로 종합 능력치 정보를 조회합니다.
- get_character_hyper_stat       : ocid로 하이퍼스탯 정보를 조회합니다.
- get_character_propensity       : ocid로 성향 정보를 조회합니다.
- get_character_ability          : ocid로 어빌리티 정보를 조회합니다.
- get_character_item_equipment   : ocid로 장착 장비 정보를 조회합니다 (캐시 장비 제외).
- get_character_cashitem_equipment : ocid로 장착 캐시 장비 정보를 조회합니다.
- get_character_set_effect       : ocid로 적용 세트 효과 정보를 조회합니다.
- get_character_beauty_equipment : ocid로 장착 헤어, 성형, 피부 정보를 조회합니다.
- get_character_pet_equipment    : ocid로 장착 펫 정보를 조회합니다.
- get_character_dojang           : ocid로 무릉도장 최고 기록 정보를 조회합니다.

[일반 툴 목록]
- get_datetime : 현재 날짜, 시간, 요일이 필요할 때
- calculator   : 수치 계산, 수식 평가가 필요할 때 (복잡한 계산은 반드시 사용)
- web_search   : 최신 뉴스, 실시간 정보, 사실 확인, 현재 이벤트 조회 시

[답변 지침]
- 사용자의 언어(한국어/영어)로 답변합니다.
- 답변 내용에는 '이 정보는 메이플스토리 전문가 에이전트가 제공합니다'라는 뉘앙스를 풍기도록 작성하세요."""



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
