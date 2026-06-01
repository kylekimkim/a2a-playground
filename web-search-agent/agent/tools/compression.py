"""
Compression Tool — SDD §7.9.

긴 본문을 focus 기준으로 핵심만 추려 압축합니다. 별도의 (저렴한) LLM 호출을 사용해
ReAct 메인 LLM의 context 사용량을 줄입니다.
"""
import os
import logging

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

COMPRESSION_MODEL = os.getenv("COMPRESSION_MODEL", os.getenv("MODEL_NAME", "gpt-5.4-mini"))
MAX_INPUT_CHARS = int(os.getenv("COMPRESSION_MAX_INPUT", "15000"))

_SYSTEM = """당신은 긴 문서를 압축하는 전문가입니다. 다음 규칙을 따르세요.
1. 'focus'에 직접 관련된 사실·수치·고유명사·날짜만 남깁니다.
2. 출처 URL이 본문에 포함돼 있으면 그대로 보존합니다.
3. 불릿 형태로 압축하고, 추측·평가·의견은 추가하지 않습니다.
4. 한국어로 출력하되, 영어 고유명사는 그대로 둡니다.
5. 출력은 1,000자 이내로 제한합니다."""


@tool
def compress_text(text: str, focus: str) -> str:
    """긴 본문을 focus 주제 기준으로 압축합니다.

    Args:
        text: 압축할 원문 (Markdown 또는 평문).
        focus: 어떤 관점에서 압축할지의 키워드/질문.

    Returns:
        압축된 텍스트 (최대 약 1,000자, 불릿 형식).
    """
    if not text or not text.strip():
        return "[compress_text] 빈 입력은 압축할 수 없습니다."
    if not focus or not focus.strip():
        focus = "사용자 질문의 핵심"

    if len(text) > MAX_INPUT_CHARS:
        text = text[:MAX_INPUT_CHARS] + "\n…(이하 입력 길이 제한으로 잘림)"

    try:
        llm = ChatOpenAI(
            model=COMPRESSION_MODEL,
            temperature=0.0,
            api_key=os.environ["OPENAI_API_KEY"],
        )
        user = f"[focus]\n{focus}\n\n[원문]\n{text}"
        resp = llm.invoke([SystemMessage(content=_SYSTEM), HumanMessage(content=user)])
        content = resp.content if isinstance(resp.content, str) else str(resp.content)
        return content.strip() or "[compress_text] 압축 결과가 비어 있습니다."
    except Exception as e:
        logger.exception("compress_text 실패")
        return f"[compress_text] 압축 실패: {e}"
