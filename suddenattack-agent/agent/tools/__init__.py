from .datetime_tool import get_datetime
from .calculator import calculator
from .web_search import web_search
from .nexon_api import (
    get_user_ouid,
    get_user_basic,
    get_user_rank,
    get_user_tier,
    get_user_recent_info,
)


def get_all_tools():
    return [
        get_datetime,
        calculator,
        web_search,
        get_user_ouid,
        get_user_basic,
        get_user_rank,
        get_user_tier,
        get_user_recent_info,
    ]
