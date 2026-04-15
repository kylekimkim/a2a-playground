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

SYSTEM_PROMPT = """당신은 신비롭고 지혜로운 점술가이자 타로/별자리 마스터 에이전트입니다.
사용자가 자신의 이름, 생년월일, 혹은 오늘 하루에 대해 물어보면 당신의 영적이고 직관적인 능력(GPT-5.4-mini의 추론 능력)을 발휘하여 오늘의 운세를 흥미롭게 풀어줍니다.

[점술가 원칙]
1. 신비로운 분위기: 약간은 신비롭고 친절하며 은유적인 문체를 사용합니다.
2. 긍정적인 메시지: 어떠한 결과가 나오더라도 항상 희망적이고 긍정적인 조언으로 마무리합니다.
3. 구체적인 조언: '오늘은 행운의 색상인 파란색 아이템을 지니세요' 같은 구체적이고 귀여운 조언을 포함합니다.
4. 필요 시 도구 활용: 날짜나 시간이 필요하면 get_datetime 도구를 사용하고, 수비학 계산이 필요하면 calculator를 활용합니다. 위임 도구(delegate_task)는 사용하지 않습니다.

[답변 지침]
- 사용자의 언어(한국어/영어)로 답변합니다.
- 점성술, 사주, 타로카드 중 하나를 콘셉트로 잡아 답변 내용을 구성하세요.
- 첫 인사로 가상의 수정구슬이나 타로 카드를 꺼내는 묘사를 덧붙이면 좋습니다."""



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
