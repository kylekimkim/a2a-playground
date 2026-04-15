from .datetime_tool import get_datetime
from .calculator import calculator
from .web_search import web_search
from .nexon_api import (
    get_character_ocid,
    get_character_basic,
    get_character_popularity,
    get_character_stat,
    get_character_hyper_stat,
    get_character_propensity,
    get_character_ability,
    get_character_item_equipment,
    get_character_cashitem_equipment,
    get_character_set_effect,
    get_character_beauty_equipment,
    get_character_pet_equipment,
    get_character_dojang,
)

def get_all_tools():
    return [
        get_datetime,
        calculator,
        web_search,
        get_character_ocid,
        get_character_basic,
        get_character_popularity,
        get_character_stat,
        get_character_hyper_stat,
        get_character_propensity,
        get_character_ability,
        get_character_item_equipment,
        get_character_cashitem_equipment,
        get_character_set_effect,
        get_character_beauty_equipment,
        get_character_pet_equipment,
        get_character_dojang,
    ]
