"""
TDD: web_search 도구 단위 테스트 (DuckDuckGo mock 처리)
"""
import pytest
from unittest.mock import patch, MagicMock
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.tools.web_search import web_search


MOCK_RESULTS = [
    {
        "title": "파이썬 최신 버전",
        "body": "파이썬 3.13이 출시되었습니다.",
        "href": "https://python.org",
    },
    {
        "title": "파이썬 공식 문서",
        "body": "공식 문서에서 최신 기능을 확인하세요.",
        "href": "https://docs.python.org",
    },
]


class TestWebSearchSuccess:
    def test_returns_string(self):
        with patch("agent.tools.web_search.DDGS") as mock_ddgs_cls:
            mock_ddgs = MagicMock()
            mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
            mock_ddgs.__exit__ = MagicMock(return_value=False)
            mock_ddgs.text.return_value = MOCK_RESULTS
            mock_ddgs_cls.return_value = mock_ddgs

            result = web_search.invoke({"query": "파이썬 최신 버전"})

        assert isinstance(result, str)

    def test_includes_result_titles(self):
        with patch("agent.tools.web_search.DDGS") as mock_ddgs_cls:
            mock_ddgs = MagicMock()
            mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
            mock_ddgs.__exit__ = MagicMock(return_value=False)
            mock_ddgs.text.return_value = MOCK_RESULTS
            mock_ddgs_cls.return_value = mock_ddgs

            result = web_search.invoke({"query": "파이썬"})

        assert "파이썬 최신 버전" in result
        assert "파이썬 공식 문서" in result

    def test_includes_source_urls(self):
        with patch("agent.tools.web_search.DDGS") as mock_ddgs_cls:
            mock_ddgs = MagicMock()
            mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
            mock_ddgs.__exit__ = MagicMock(return_value=False)
            mock_ddgs.text.return_value = MOCK_RESULTS
            mock_ddgs_cls.return_value = mock_ddgs

            result = web_search.invoke({"query": "파이썬"})

        assert "https://python.org" in result
        assert "https://docs.python.org" in result

    def test_results_numbered(self):
        with patch("agent.tools.web_search.DDGS") as mock_ddgs_cls:
            mock_ddgs = MagicMock()
            mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
            mock_ddgs.__exit__ = MagicMock(return_value=False)
            mock_ddgs.text.return_value = MOCK_RESULTS
            mock_ddgs_cls.return_value = mock_ddgs

            result = web_search.invoke({"query": "파이썬"})

        assert "[1]" in result
        assert "[2]" in result

    def test_uses_kr_region(self):
        with patch("agent.tools.web_search.DDGS") as mock_ddgs_cls:
            mock_ddgs = MagicMock()
            mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
            mock_ddgs.__exit__ = MagicMock(return_value=False)
            mock_ddgs.text.return_value = MOCK_RESULTS
            mock_ddgs_cls.return_value = mock_ddgs

            web_search.invoke({"query": "테스트"})

            call_kwargs = mock_ddgs.text.call_args
            assert call_kwargs[1].get("region") == "kr-kr" or "kr-kr" in str(call_kwargs)

    def test_max_results_is_4(self):
        with patch("agent.tools.web_search.DDGS") as mock_ddgs_cls:
            mock_ddgs = MagicMock()
            mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
            mock_ddgs.__exit__ = MagicMock(return_value=False)
            mock_ddgs.text.return_value = MOCK_RESULTS
            mock_ddgs_cls.return_value = mock_ddgs

            web_search.invoke({"query": "테스트"})

            call_kwargs = mock_ddgs.text.call_args
            assert call_kwargs[1].get("max_results") == 4


class TestWebSearchEmpty:
    def test_no_results_returns_not_found_message(self):
        with patch("agent.tools.web_search.DDGS") as mock_ddgs_cls:
            mock_ddgs = MagicMock()
            mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
            mock_ddgs.__exit__ = MagicMock(return_value=False)
            mock_ddgs.text.return_value = []
            mock_ddgs_cls.return_value = mock_ddgs

            result = web_search.invoke({"query": "존재하지않는쿼리xyz"})

        assert "찾을 수 없습니다" in result


class TestWebSearchErrors:
    def test_ddgs_exception_returns_error_message(self):
        with patch("agent.tools.web_search.DDGS", side_effect=Exception("네트워크 오류")):
            result = web_search.invoke({"query": "테스트"})

        assert "오류" in result or "error" in result.lower()

    def test_missing_package_returns_install_hint(self):
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "duckduckgo_search":
                raise ImportError("No module named 'duckduckgo_search'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = web_search.invoke({"query": "테스트"})

        assert "pip install" in result or "설치" in result
