from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_core.tools import tool


@tool
def get_datetime(timezone: str = "Asia/Seoul") -> str:
    """지정 타임존의 현재 날짜·시각·요일을 ISO 8601 형식으로 반환합니다."""
    try:
        now = datetime.now(ZoneInfo(timezone))
    except Exception:
        now = datetime.now(ZoneInfo("Asia/Seoul"))
        timezone = "Asia/Seoul (fallback)"
    weekday_ko = ["월", "화", "수", "목", "금", "토", "일"][now.weekday()]
    return f"{now.isoformat()} ({weekday_ko}요일, {timezone})"
