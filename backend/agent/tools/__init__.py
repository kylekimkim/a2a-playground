from .datetime_tool import get_datetime
from .calculator import calculator
from .delegate import delegate_task
from .mcp_tools import get_mcp_tools

def get_all_tools():
    return [get_datetime, calculator, delegate_task] + get_mcp_tools()
