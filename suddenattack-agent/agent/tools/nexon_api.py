import requests
from langchain.tools import tool

NEXON_API_KEY = "test_8bfaeec338c0300cb351c3a332bf51cdcb70378a1e627f068a06936d9429ad52efe8d04e6d233bd35cf2fabdeb93fb0d"
BASE_URL = "https://open.api.nexon.com"

HEADERS = {
    "x-nxopen-api-key": NEXON_API_KEY
}


def _get(endpoint: str, params: dict) -> str:
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()
        return str(response.json())
    except requests.exceptions.HTTPError:
        return f"API 오류 (HTTP {response.status_code}): {response.text}"
    except requests.exceptions.RequestException as e:
        return f"요청 오류: {str(e)}"


@tool
def get_user_ouid(user_name: str) -> str:
    """서든어택 유저 이름으로 계정 식별자(ouid)를 조회합니다.

    Args:
        user_name: 조회할 서든어택 유저 이름

    Returns:
        유저의 ouid(계정 식별자) 또는 오류 메시지
    """
    try:
        response = requests.get(
            f"{BASE_URL}/suddenattack/v1/id",
            headers=HEADERS,
            params={"user_name": user_name},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        ouid = data.get("ouid")
        if ouid:
            return f"유저 '{user_name}'의 ouid: {ouid}"
        return f"ouid를 찾을 수 없습니다. 응답: {data}"
    except requests.exceptions.HTTPError:
        return f"API 오류 (HTTP {response.status_code}): {response.text}"
    except requests.exceptions.RequestException as e:
        return f"요청 오류: {str(e)}"


@tool
def get_user_basic(ouid: str) -> str:
    """서든어택 유저의 ouid로 기본 정보를 조회합니다.

    Args:
        ouid: 조회할 유저의 계정 식별자(ouid)

    Returns:
        유저 기본 정보 또는 오류 메시지
    """
    return _get("/suddenattack/v1/user/basic", {"ouid": ouid})


@tool
def get_user_rank(ouid: str) -> str:
    """서든어택 유저의 ouid로 계급 정보를 조회합니다.

    Args:
        ouid: 조회할 유저의 계정 식별자(ouid)

    Returns:
        유저 계급 정보 또는 오류 메시지
    """
    return _get("/suddenattack/v1/user/rank", {"ouid": ouid})


@tool
def get_user_tier(ouid: str) -> str:
    """서든어택 유저의 ouid로 티어 정보를 조회합니다.

    Args:
        ouid: 조회할 유저의 계정 식별자(ouid)

    Returns:
        유저 티어 정보 또는 오류 메시지
    """
    return _get("/suddenattack/v1/user/tier", {"ouid": ouid})


@tool
def get_user_recent_info(ouid: str) -> str:
    """서든어택 유저의 ouid로 최근 동향 정보를 조회합니다.

    Args:
        ouid: 조회할 유저의 계정 식별자(ouid)

    Returns:
        유저 최근 동향 정보 또는 오류 메시지
    """
    return _get("/suddenattack/v1/user/recent-info", {"ouid": ouid})
