from .searxng_search import search_web
from .crawl4ai_fetch import fetch_url
from .compression import compress_text
from .datetime_tool import get_datetime


def get_all_tools():
    return [search_web, fetch_url, compress_text, get_datetime]
