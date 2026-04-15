import requests
from langchain.tools import tool

NEXON_API_KEY = "test_3a83cb9858188178ff354c49e53fe2582e78ca297a2c03f1195bd1400272455befe8d04e6d233bd35cf2fabdeb93fb0d"
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
def get_character_ocid(character_name: str) -> str:
    """메이플스토리 캐릭터 이름으로 사용자 고유식별자(ocid)를 조회합니다.

    Args:
        character_name: 조회할 메이플스토리 캐릭터 이름

    Returns:
        캐릭터의 ocid(고유식별자) 또는 오류 메시지
    """
    try:
        response = requests.get(f"{BASE_URL}/maplestory/v1/id", headers=HEADERS, params={"character_name": character_name}, timeout=10)
        response.raise_for_status()
        data = response.json()
        ocid = data.get("ocid")
        if ocid:
            return f"캐릭터 '{character_name}'의 ocid: {ocid}"
        return f"ocid를 찾을 수 없습니다. 응답: {data}"
    except requests.exceptions.HTTPError:
        return f"API 오류 (HTTP {response.status_code}): {response.text}"
    except requests.exceptions.RequestException as e:
        return f"요청 오류: {str(e)}"


@tool
def get_character_basic(ocid: str) -> str:
    """메이플스토리 캐릭터의 ocid로 캐릭터 기본 정보를 조회합니다.

    Args:
        ocid: 조회할 캐릭터의 고유식별자(ocid)

    Returns:
        캐릭터 기본 정보(이름, 직업, 레벨, 서버 등) 또는 오류 메시지
    """
    return _get("/maplestory/v1/character/basic", {"ocid": ocid})


@tool
def get_character_popularity(ocid: str) -> str:
    """메이플스토리 캐릭터의 ocid로 캐릭터 인기도 정보를 조회합니다.

    Args:
        ocid: 조회할 캐릭터의 고유식별자(ocid)

    Returns:
        캐릭터 인기도 정보 또는 오류 메시지
    """
    return _get("/maplestory/v1/character/popularity", {"ocid": ocid})


@tool
def get_character_stat(ocid: str) -> str:
    """메이플스토리 캐릭터의 ocid로 종합 능력치 정보를 조회합니다.

    Args:
        ocid: 조회할 캐릭터의 고유식별자(ocid)

    Returns:
        캐릭터 종합 능력치 정보 또는 오류 메시지
    """
    return _get("/maplestory/v1/character/stat", {"ocid": ocid})


@tool
def get_character_hyper_stat(ocid: str) -> str:
    """메이플스토리 캐릭터의 ocid로 하이퍼스탯 정보를 조회합니다.

    Args:
        ocid: 조회할 캐릭터의 고유식별자(ocid)

    Returns:
        캐릭터 하이퍼스탯 정보 또는 오류 메시지
    """
    return _get("/maplestory/v1/character/hyper-stat", {"ocid": ocid})


@tool
def get_character_propensity(ocid: str) -> str:
    """메이플스토리 캐릭터의 ocid로 성향 정보를 조회합니다.

    Args:
        ocid: 조회할 캐릭터의 고유식별자(ocid)

    Returns:
        캐릭터 성향 정보 또는 오류 메시지
    """
    return _get("/maplestory/v1/character/propensity", {"ocid": ocid})


@tool
def get_character_ability(ocid: str) -> str:
    """메이플스토리 캐릭터의 ocid로 어빌리티 정보를 조회합니다.

    Args:
        ocid: 조회할 캐릭터의 고유식별자(ocid)

    Returns:
        캐릭터 어빌리티 정보 또는 오류 메시지
    """
    return _get("/maplestory/v1/character/ability", {"ocid": ocid})


@tool
def get_character_item_equipment(ocid: str) -> str:
    """메이플스토리 캐릭터의 ocid로 장착 장비 정보를 조회합니다 (캐시 장비 제외).

    Args:
        ocid: 조회할 캐릭터의 고유식별자(ocid)

    Returns:
        캐릭터 장착 장비 정보 또는 오류 메시지
    """
    return _get("/maplestory/v1/character/item-equipment", {"ocid": ocid})


@tool
def get_character_cashitem_equipment(ocid: str) -> str:
    """메이플스토리 캐릭터의 ocid로 장착 캐시 장비 정보를 조회합니다.

    Args:
        ocid: 조회할 캐릭터의 고유식별자(ocid)

    Returns:
        캐릭터 장착 캐시 장비 정보 또는 오류 메시지
    """
    return _get("/maplestory/v1/character/cashitem-equipment", {"ocid": ocid})


@tool
def get_character_set_effect(ocid: str) -> str:
    """메이플스토리 캐릭터의 ocid로 적용 세트 효과 정보를 조회합니다.

    Args:
        ocid: 조회할 캐릭터의 고유식별자(ocid)

    Returns:
        캐릭터 적용 세트 효과 정보 또는 오류 메시지
    """
    return _get("/maplestory/v1/character/set-effect", {"ocid": ocid})


@tool
def get_character_beauty_equipment(ocid: str) -> str:
    """메이플스토리 캐릭터의 ocid로 장착 헤어, 성형, 피부 정보를 조회합니다.

    Args:
        ocid: 조회할 캐릭터의 고유식별자(ocid)

    Returns:
        캐릭터 헤어, 성형, 피부 정보 또는 오류 메시지
    """
    return _get("/maplestory/v1/character/beauty-equipment", {"ocid": ocid})


@tool
def get_character_pet_equipment(ocid: str) -> str:
    """메이플스토리 캐릭터의 ocid로 장착 펫 정보를 조회합니다.

    Args:
        ocid: 조회할 캐릭터의 고유식별자(ocid)

    Returns:
        캐릭터 장착 펫 정보 또는 오류 메시지
    """
    return _get("/maplestory/v1/character/pet-equipment", {"ocid": ocid})


@tool
def get_character_dojang(ocid: str) -> str:
    """메이플스토리 캐릭터의 ocid로 무릉도장 최고 기록 정보를 조회합니다.

    Args:
        ocid: 조회할 캐릭터의 고유식별자(ocid)

    Returns:
        캐릭터 무릉도장 최고 기록 정보 또는 오류 메시지
    """
    return _get("/maplestory/v1/character/dojang", {"ocid": ocid})
