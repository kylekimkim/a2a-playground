"""
TDD: get_datetime 도구 단위 테스트
"""
import re
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.tools.datetime_tool import get_datetime


WEEKDAYS_KR = {"월", "화", "수", "목", "금", "토", "일"}
YEAR_PATTERN = re.compile(r"\d{4}년")
TIME_PATTERN = re.compile(r"\d{2}:\d{2}:\d{2}")


class TestGetDatetimeDefault:
    """기본 타임존(Asia/Seoul) 동작"""

    def test_returns_string(self):
        result = get_datetime.invoke({})
        assert isinstance(result, str)

    def test_contains_year(self):
        result = get_datetime.invoke({})
        assert YEAR_PATTERN.search(result), f"연도 없음: {result}"

    def test_contains_time(self):
        result = get_datetime.invoke({})
        assert TIME_PATTERN.search(result), f"시간 없음: {result}"

    def test_contains_korean_weekday(self):
        result = get_datetime.invoke({})
        has_weekday = any(f"({wd})" in result for wd in WEEKDAYS_KR)
        assert has_weekday, f"한국어 요일 없음: {result}"

    def test_contains_default_timezone_label(self):
        result = get_datetime.invoke({})
        assert "Asia/Seoul" in result


class TestGetDatetimeCustomTimezone:
    """사용자 지정 타임존"""

    def test_utc_timezone(self):
        result = get_datetime.invoke({"timezone": "UTC"})
        assert "UTC" in result
        assert YEAR_PATTERN.search(result)

    def test_new_york_timezone(self):
        result = get_datetime.invoke({"timezone": "America/New_York"})
        assert "America/New_York" in result

    def test_london_timezone(self):
        result = get_datetime.invoke({"timezone": "Europe/London"})
        assert "Europe/London" in result

    def test_tokyo_timezone(self):
        result = get_datetime.invoke({"timezone": "Asia/Tokyo"})
        assert "Asia/Tokyo" in result


class TestGetDatetimeInvalidTimezone:
    """잘못된 타임존 처리"""

    def test_unknown_timezone_returns_fallback_message(self):
        result = get_datetime.invoke({"timezone": "Invalid/Zone"})
        assert "알 수 없는 타임존" in result

    def test_unknown_timezone_still_returns_time(self):
        result = get_datetime.invoke({"timezone": "Mars/Olympus"})
        # 로컬 시간이라도 반환해야 함
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_string_timezone_returns_fallback(self):
        result = get_datetime.invoke({"timezone": ""})
        assert isinstance(result, str)
