from .datetime_tool import get_datetime
from .calculator import calculator
from .web_search import web_search

def get_all_tools():
    return [get_datetime, calculator, web_search]
