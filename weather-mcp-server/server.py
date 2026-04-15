"""
Weather MCP Server — OpenWeatherMap API 기반 날씨 조회 MCP 서버.

지원 기능:
  - 현재 날씨 조회 (도시명 또는 위도/경도)
  - 5일 예보 조회 (3시간 단위)

실행:
  OPENWEATHER_API_KEY=<key> python server.py
  → SSE 서버: http://0.0.0.0:8101/sse
"""
import os
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# 프로젝트 루트의 .env 로드 (server.py 위치 기준 한 단계 위)
load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8101"))
API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

BASE_URL = "https://api.openweathermap.org/data/2.5"
GEO_URL = "https://api.openweathermap.org/geo/1.0"

mcp = FastMCP("Weather", host=MCP_HOST, port=MCP_PORT)


def _check_api_key() -> None:
    if not API_KEY:
        raise RuntimeError("OPENWEATHER_API_KEY 환경 변수가 설정되지 않았습니다.")


def _units_label(units: str) -> dict:
    if units == "imperial":
        return {"temp": "°F", "speed": "mph"}
    if units == "standard":
        return {"temp": "K", "speed": "m/s"}
    return {"temp": "°C", "speed": "m/s"}


def _wind_direction(deg: int) -> str:
    dirs = ["북", "북동", "동", "남동", "남", "남서", "서", "북서"]
    return dirs[round(deg / 45) % 8]


def _format_current(data: dict, units: str) -> str:
    label = _units_label(units)
    city = data["name"]
    country = data["sys"]["country"]
    desc = data["weather"][0]["description"]
    temp = data["main"]["temp"]
    feels = data["main"]["feels_like"]
    humidity = data["main"]["humidity"]
    wind_spd = data["wind"]["speed"]
    wind_deg = data["wind"].get("deg", 0)
    visibility = data.get("visibility", 0) / 1000
    clouds = data["clouds"]["all"]
    rain = data.get("rain", {}).get("1h", 0)
    snow = data.get("snow", {}).get("1h", 0)

    sunrise = datetime.fromtimestamp(data["sys"]["sunrise"], tz=timezone.utc) \
                       .astimezone(timezone(timedelta(hours=9)))
    sunset = datetime.fromtimestamp(data["sys"]["sunset"], tz=timezone.utc) \
                      .astimezone(timezone(timedelta(hours=9)))

    lines = [
        f"## {city}, {country} 현재 날씨",
        f"- 날씨: {desc}",
        f"- 기온: {temp}{label['temp']} (체감 {feels}{label['temp']})",
        f"- 습도: {humidity}%",
        f"- 바람: {wind_spd}{label['speed']} ({_wind_direction(wind_deg)}풍)",
        f"- 가시거리: {visibility:.1f}km",
        f"- 구름: {clouds}%",
    ]
    if rain:
        lines.append(f"- 강수량(1h): {rain}mm")
    if snow:
        lines.append(f"- 적설량(1h): {snow}mm")
    lines.append(f"- 일출/일몰: {sunrise.strftime('%H:%M')} / {sunset.strftime('%H:%M')} KST")
    return "\n".join(lines)


def _format_forecast(data: dict, units: str, days: int) -> str:
    label = _units_label(units)
    city = data["city"]["name"]
    country = data["city"]["country"]
    lines = [f"## {city}, {country} {days}일 예보\n"]

    kst = timezone(timedelta(hours=9))
    current_day = None

    for item in data["list"]:
        dt = datetime.fromtimestamp(item["dt"], tz=kst)
        day_str = dt.strftime("%m/%d(%a)")
        if day_str != current_day:
            if current_day is not None:
                lines.append("")
            lines.append(f"### {day_str}")
            current_day = day_str

        time_str = dt.strftime("%H:%M")
        temp = item["main"]["temp"]
        desc = item["weather"][0]["description"]
        humidity = item["main"]["humidity"]
        wind = item["wind"]["speed"]
        pop = int(item.get("pop", 0) * 100)
        lines.append(f"- {time_str}  {temp}{label['temp']}  {desc}  습도 {humidity}%  강수확률 {pop}%  바람 {wind}{label['speed']}")

    return "\n".join(lines)


@mcp.tool()
def get_current_weather(city: str, units: str = "metric") -> str:
    """
    도시명으로 현재 날씨를 조회합니다.

    Args:
        city: 도시명 (한글 또는 영문). 예: "서울", "Seoul", "Tokyo", "New York"
        units: 단위계. "metric"(섭씨, 기본값) / "imperial"(화씨) / "standard"(켈빈)

    Returns:
        현재 기온, 날씨 상태, 습도, 바람, 가시거리, 일출/일몰 등을 포함한 날씨 정보.
    """
    _check_api_key()
    logger.info(f"현재 날씨 조회: {city} (units={units})")

    with httpx.Client(timeout=10) as client:
        resp = client.get(f"{BASE_URL}/weather", params={
            "q": city, "appid": API_KEY, "units": units, "lang": "kr",
        })

    if resp.status_code == 404:
        return f"'{city}' 도시를 찾을 수 없습니다. 도시명을 확인해주세요."
    if resp.status_code == 401:
        return "API 키가 유효하지 않습니다."
    resp.raise_for_status()

    return _format_current(resp.json(), units)


@mcp.tool()
def get_weather_forecast(city: str, days: int = 3, units: str = "metric") -> str:
    """
    도시명으로 날씨 예보를 조회합니다 (3시간 단위, 최대 5일).

    Args:
        city: 도시명 (한글 또는 영문). 예: "서울", "Seoul", "Tokyo"
        days: 예보 기간 (1~5일, 기본값 3)
        units: 단위계. "metric"(섭씨, 기본값) / "imperial"(화씨) / "standard"(켈빈)

    Returns:
        3시간 단위 기온, 날씨, 강수확률 등을 포함한 예보.
    """
    _check_api_key()
    days = max(1, min(5, days))
    cnt = days * 8  # 3시간 × 8 = 24시간
    logger.info(f"날씨 예보 조회: {city} ({days}일, units={units})")

    with httpx.Client(timeout=10) as client:
        resp = client.get(f"{BASE_URL}/forecast", params={
            "q": city, "appid": API_KEY, "units": units, "lang": "kr", "cnt": cnt,
        })

    if resp.status_code == 404:
        return f"'{city}' 도시를 찾을 수 없습니다. 도시명을 확인해주세요."
    if resp.status_code == 401:
        return "API 키가 유효하지 않습니다."
    resp.raise_for_status()

    return _format_forecast(resp.json(), units, days)


@mcp.tool()
def get_weather_by_coords(lat: float, lon: float, units: str = "metric") -> str:
    """
    위도/경도로 현재 날씨를 조회합니다.

    Args:
        lat: 위도 (예: 37.5665 for 서울)
        lon: 경도 (예: 126.9780 for 서울)
        units: 단위계. "metric"(섭씨, 기본값) / "imperial"(화씨) / "standard"(켈빈)

    Returns:
        현재 날씨 정보.
    """
    _check_api_key()
    logger.info(f"좌표 날씨 조회: ({lat}, {lon})")

    with httpx.Client(timeout=10) as client:
        resp = client.get(f"{BASE_URL}/weather", params={
            "lat": lat, "lon": lon, "appid": API_KEY, "units": units, "lang": "kr",
        })

    resp.raise_for_status()
    return _format_current(resp.json(), units)


if __name__ == "__main__":
    if not API_KEY:
        logger.warning("OPENWEATHER_API_KEY 환경 변수가 설정되지 않았습니다. 날씨 조회가 실패합니다.")
    logger.info(f"Weather MCP 서버 시작: http://{MCP_HOST}:{MCP_PORT}/sse")
    mcp.run(transport="sse")
