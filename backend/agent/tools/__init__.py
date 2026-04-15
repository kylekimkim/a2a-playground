from .datetime_tool import get_datetime
from .calculator import calculator
from .web_search import web_search
from .delegate import delegate_task
from .mcp_tools import get_mcp_tools

def get_all_tools():
    return [get_datetime, calculator, web_search, delegate_task] + get_mcp_tools()
