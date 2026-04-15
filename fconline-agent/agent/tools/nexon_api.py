import requests
from langchain.tools import tool

NEXON_API_KEY = "test_235597ef0b09b6a4b59bef3983c74e109fbca142930664103295d12d9917214befe8d04e6d233bd35cf2fabdeb93fb0d"
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
def get_user_ouid(nickname: str) -> str:
    """FC 온라인 유저 닉네임으로 계정 식별자(ouid)를 조회합니다.

    Args:
        nickname: 조회할 FC 온라인 유저 닉네임

    Returns:
        유저의 ouid(계정 식별자) 또는 오류 메시지
    """
    try:
        response = requests.get(
            f"{BASE_URL}/fconline/v1/id",
            headers=HEADERS,
            params={"nickname": nickname},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        ouid = data.get("ouid")
        if ouid:
            return f"유저 '{nickname}'의 ouid: {ouid}"
        return f"ouid를 찾을 수 없습니다. 응답: {data}"
    except requests.exceptions.HTTPError:
        return f"API 오류 (HTTP {response.status_code}): {response.text}"
    except requests.exceptions.RequestException as e:
        return f"요청 오류: {str(e)}"


@tool
def get_user_basic(ouid: str) -> str:
    """FC 온라인 유저의 ouid로 기본 정보를 조회합니다.

    Args:
        ouid: 조회할 유저의 계정 식별자(ouid)

    Returns:
        유저 기본 정보 또는 오류 메시지
    """
    return _get("/fconline/v1/user/basic", {"ouid": ouid})


@tool
def get_user_max_division(ouid: str) -> str:
    """FC 온라인 유저의 ouid로 역대 최고 등급을 조회합니다.

    Args:
        ouid: 조회할 유저의 계정 식별자(ouid)

    Returns:
        유저 역대 최고 등급 정보 또는 오류 메시지
    """
    return _get("/fconline/v1/user/maxdivision", {"ouid": ouid})


@tool
def get_user_trade(ouid: str, tradetype: str) -> str:
    """FC 온라인 유저의 ouid로 거래 기록을 조회합니다.

    Args:
        ouid: 조회할 유저의 계정 식별자(ouid)
        tradetype: 거래 유형 ('buy' 또는 'sell')

    Returns:
        유저 거래 기록 또는 오류 메시지
    """
    if tradetype not in ("buy", "sell"):
        return "오류: tradetype은 'buy' 또는 'sell' 이어야 합니다."
    return _get("/fconline/v1/user/trade", {"ouid": ouid, "tradetype": tradetype})
