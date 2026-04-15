from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from langchain.tools import tool


@tool
def get_datetime(timezone: str = "Asia/Seoul") -> str:
    """현재 날짜와 시간을 반환합니다. timezone 파라미터로 타임존 지정 가능 (기본값: Asia/Seoul).
    예: 'Asia/Seoul', 'America/New_York', 'Europe/London', 'UTC'
    """
    try:
        tz = ZoneInfo(timezone)
        now = datetime.now(tz)
        weekdays = ["월", "화", "수", "목", "금", "토", "일"]
        weekday = weekdays[now.weekday()]

        print("## get_datetime 툴 결과: ")
        print(f"{now.year}년 {now.month}월 {now.day}일 ({weekday}) ")
        print(f"{now.hour:02d}:{now.minute:02d}:{now.second:02d} ({timezone})") 
        return (
            f"{now.year}년 {now.month}월 {now.day}일 ({weekday}) "
            f"{now.hour:02d}:{now.minute:02d}:{now.second:02d} ({timezone})"
        )
    except ZoneInfoNotFoundError:
        now = datetime.now()
        print(f"[get_datetime ERROR] {timezone}는 알 수 없는 타임존입니다.")
        return f"알 수 없는 타임존 '{timezone}'. 로컬 시간: {now.strftime('%Y-%m-%d %H:%M:%S')}"
