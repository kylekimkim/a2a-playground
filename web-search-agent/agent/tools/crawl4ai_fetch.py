"""
Crawl4AI Fetch Tool — SDD §7.3.

URL의 본문을 Markdown으로 추출합니다. crawl4ai가 설치돼 있으면 AsyncWebCrawler를 사용하고,
설치/실행 환경 문제(Playwright 미설치 등)로 실패하면 httpx + BeautifulSoup 기반 fallback을 사용합니다.
"""
import os
import logging
from urllib.parse import urlparse

import httpx
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

FETCH_TIMEOUT = float(os.getenv("FETCH_TIMEOUT", "20"))
MAX_BODY_CHARS = int(os.getenv("FETCH_MAX_CHARS", "12000"))
# httpx-first 모드: 1차로 httpx+BS4 시도. 본문이 이 길이보다 짧을 때만 Crawl4AI(Playwright) 폴백.
MIN_FALLBACK_CHARS = int(os.getenv("FETCH_MIN_FALLBACK_CHARS", "500"))

_BLOCKED_HOST_SUFFIXES = (".local", ".localhost", ".internal")
_BLOCKED_SCHEMES = {"file", "ftp", "data", "javascript"}


def _validate_url(url: str) -> str | None:
    """허용되지 않는 URL이면 에러 메시지를, 통과하면 None을 반환."""
    try:
        parsed = urlparse(url)
    except Exception:
        return f"잘못된 URL 형식: {url}"
    if parsed.scheme.lower() in _BLOCKED_SCHEMES or parsed.scheme not in {"http", "https"}:
        return f"허용되지 않는 scheme: {parsed.scheme}"
    host = (parsed.hostname or "").lower()
    if not host:
        return "URL에 호스트가 없습니다."
    if any(host == s.lstrip(".") or host.endswith(s) for s in _BLOCKED_HOST_SUFFIXES):
        return f"내부 도메인은 접근할 수 없습니다: {host}"
    if host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
        return f"localhost는 접근할 수 없습니다: {host}"
    return None


async def _crawl_with_crawl4ai(url: str) -> str | None:
    try:
        from crawl4ai import AsyncWebCrawler
    except ImportError:
        return None
    try:
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url=url)
        md = getattr(result, "markdown", None) or getattr(result, "fit_markdown", None)
        return md if md else None
    except Exception as e:
        logger.warning("Crawl4AI 실패, fallback 사용: %s", e)
        return None


async def _crawl_fallback(url: str) -> str:
    from bs4 import BeautifulSoup
    from markdownify import markdownify as html_to_md

    async with httpx.AsyncClient(
        timeout=FETCH_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": "a2a-web-search-agent/1.0"},
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        html = resp.text

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "aside"]):
        tag.decompose()
    main = soup.find("article") or soup.find("main") or soup.body or soup
    return html_to_md(str(main), heading_style="ATX").strip()


async def _do_fetch(url: str) -> str:
    """httpx-first 전략.

    1) httpx + BeautifulSoup 으로 먼저 시도 (정적 페이지는 0.5~2s 안에 충분).
    2) 본문이 MIN_FALLBACK_CHARS 미만이면 JS 렌더링 페이지로 보고 Crawl4AI 폴백.
    이 순서가 (i) Playwright 부팅 비용을 대부분 회피하고
            (ii) Windows asyncio subprocess 충돌 빈도를 줄여줍니다.
    """
    md: str | None = None
    try:
        md = await _crawl_fallback(url)
    except Exception as e:
        logger.warning("httpx fetch 실패, Crawl4AI 폴백 시도: %s", e)

    if not md or len(md.strip()) < MIN_FALLBACK_CHARS:
        crawl_md = await _crawl_with_crawl4ai(url)
        if crawl_md and (not md or len(crawl_md) > len(md)):
            md = crawl_md

    if not md or not md.strip():
        return f"[fetch_url] {url} 에서 본문을 추출하지 못했습니다."
    truncated = False
    if len(md) > MAX_BODY_CHARS:
        md = md[:MAX_BODY_CHARS]
        truncated = True
    header = f"[Fetched from {url}]" + (" (truncated)" if truncated else "")
    return f"{header}\n\n{md}"


@tool
async def fetch_url(url: str) -> str:
    """주어진 URL의 본문을 Crawl4AI로 가져와 Markdown으로 반환합니다.
    Crawl4AI 실행에 실패하면 httpx + BeautifulSoup fallback을 사용합니다.
    내부/localhost/허용되지 않는 scheme은 차단됩니다.

    Args:
        url: 가져올 페이지의 절대 URL (http/https).

    Returns:
        Markdown 본문 (최대 12,000자, 초과 시 잘림 표시). 실패 시 에러 메시지.
    """
    err = _validate_url(url)
    if err:
        return f"[fetch_url] 거부됨: {err}"
    try:
        return await _do_fetch(url)
    except httpx.HTTPStatusError as e:
        return f"[fetch_url] HTTP {e.response.status_code}: {url}"
    except httpx.HTTPError as e:
        return f"[fetch_url] 네트워크 오류: {e}"
    except Exception as e:
        logger.exception("fetch_url 예외")
        return f"[fetch_url] 처리 실패: {e}"
