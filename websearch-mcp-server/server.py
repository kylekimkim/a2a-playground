"""
Web Search MCP Server — SearXNG + Crawl4AI 기반 웹 검색 MCP 서버.

지원 기능:
  - search_web : SearXNG JSON API로 웹 검색 (제목·URL·스니펫)
  - fetch_url  : Crawl4AI(또는 httpx+BS4 폴백)로 페이지 본문을 Markdown 추출

실행:
  python server.py
  → Streamable HTTP 서버: http://0.0.0.0:8103/mcp

전제:
  - SEARXNG_URL이 가리키는 SearXNG 인스턴스가 실행 중이어야 하고,
    settings.yml 에서 `formats: [html, json]` 이 활성화돼 있어야 함.
"""
import os
import hmac
import logging
from pathlib import Path
from urllib.parse import urlparse

import httpx
import uvicorn
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# 프로젝트 루트의 공유 .env 로드 (MCP_AUTH_TOKEN, SEARXNG_URL 등)
load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8103"))
MCP_AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN", "")

SEARXNG_URL = os.getenv("SEARXNG_URL", "http://localhost:8888").rstrip("/")
SEARXNG_TIMEOUT = float(os.getenv("SEARXNG_TIMEOUT", "10"))

FETCH_TIMEOUT = float(os.getenv("FETCH_TIMEOUT", "20"))
MAX_BODY_CHARS = int(os.getenv("FETCH_MAX_CHARS", "12000"))
MIN_FALLBACK_CHARS = int(os.getenv("FETCH_MIN_FALLBACK_CHARS", "500"))
# focus 키워드 매칭 시 ±N자 윈도우 (한쪽 폭)
FOCUS_WINDOW = int(os.getenv("FETCH_FOCUS_WINDOW", "2000"))
# max_chars의 하한 — 너무 작은 값을 받아도 의미 있는 토막은 남기도록.
MIN_MAX_CHARS = 500

mcp = FastMCP("Web Search", host=MCP_HOST, port=MCP_PORT)


# ── Bearer 인증 미들웨어 ─────────────────────────────────────────────────────

def _bearer_auth_middleware(app, token: str):
    """Bearer 토큰을 검증하는 raw ASGI 미들웨어. token이 비어 있으면 통과시킨다.

    Streamable HTTP 스트림을 건드리지 않도록 BaseHTTPMiddleware(버퍼링)가 아닌
    raw ASGI로 구현.
    """
    async def wrapped(scope, receive, send):
        if not token or scope["type"] != "http":
            await app(scope, receive, send)
            return
        headers = dict(scope.get("headers") or [])
        auth_header = headers.get(b"authorization", b"").decode("latin-1")
        valid = (
            auth_header.startswith("Bearer ")
            and hmac.compare_digest(auth_header[7:], token)
        )
        if not valid:
            await send({
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"www-authenticate", b'Bearer realm="mcp"'),
                ],
            })
            await send({
                "type": "http.response.body",
                "body": b'{"error":"unauthorized"}',
            })
            return
        await app(scope, receive, send)

    return wrapped


# ── SSRF / 내부망 차단 ───────────────────────────────────────────────────────

_BLOCKED_HOST_SUFFIXES = (".local", ".localhost", ".internal")
_BLOCKED_SCHEMES = {"file", "ftp", "data", "javascript"}
_BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def _is_blocked_host(host: str) -> bool:
    host = (host or "").lower()
    if not host:
        return True
    if host in _BLOCKED_HOSTS:
        return True
    return any(host == s.lstrip(".") or host.endswith(s) for s in _BLOCKED_HOST_SUFFIXES)


def _validate_url(url: str) -> str | None:
    """허용되지 않는 URL이면 에러 메시지를, 통과하면 None을 반환."""
    try:
        parsed = urlparse(url)
    except Exception:
        return f"잘못된 URL 형식: {url}"
    scheme = parsed.scheme.lower()
    if scheme in _BLOCKED_SCHEMES or scheme not in {"http", "https"}:
        return f"허용되지 않는 scheme: {parsed.scheme}"
    if _is_blocked_host(parsed.hostname or ""):
        return f"허용되지 않는 호스트: {parsed.hostname}"
    return None


# ── 본문 추출 (Crawl4AI + httpx 폴백) ────────────────────────────────────────

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
        logger.warning("Crawl4AI 실패, httpx 폴백 사용: %s", e)
        return None


async def _crawl_fallback(url: str) -> str:
    from bs4 import BeautifulSoup
    from markdownify import markdownify as html_to_md

    async with httpx.AsyncClient(
        timeout=FETCH_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": "a2a-websearch-mcp/1.0"},
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        html = resp.text

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "aside"]):
        tag.decompose()
    main = soup.find("article") or soup.find("main") or soup.body or soup
    return html_to_md(str(main), heading_style="ATX").strip()


def _clamp_max_chars(requested: int | None) -> int:
    """호출자가 준 max_chars를 [MIN_MAX_CHARS, MAX_BODY_CHARS] 범위로 정규화."""
    if requested is None or requested <= 0:
        return MAX_BODY_CHARS
    return max(MIN_MAX_CHARS, min(int(requested), MAX_BODY_CHARS))


def _focus_extract(md: str, focus: str, window: int) -> tuple[str, int]:
    """focus 키워드(대소문자 무시) 등장 위치 ±window 글자 윈도우를 모두 추출.

    인접/겹치는 윈도우는 자동 병합. 여러 윈도우는 '---' 로 구분해 연결.
    매치가 없으면 (원본, 0) 반환.
    """
    if not focus:
        return md, 0
    lower = md.lower()
    q = focus.lower()
    positions: list[int] = []
    start = 0
    while True:
        idx = lower.find(q, start)
        if idx == -1:
            break
        positions.append(idx)
        start = idx + max(1, len(q))
    if not positions:
        return md, 0
    spans = [
        (max(0, p - window), min(len(md), p + len(focus) + window))
        for p in positions
    ]
    merged: list[list[int]] = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    parts = [md[s:e] for s, e in merged]
    return "\n\n---\n\n".join(parts), len(positions)


async def _do_fetch(url: str, focus: str | None, max_chars: int | None) -> str:
    """httpx-first 전략.

    1) httpx + BeautifulSoup 으로 먼저 시도 (정적 페이지는 0.5~2s 안에 충분).
    2) 본문이 MIN_FALLBACK_CHARS 미만이면 JS 렌더링 페이지로 보고 Crawl4AI 폴백.
    이 순서가 (i) Playwright 부팅 비용을 대부분 회피하고
            (ii) Windows asyncio subprocess 충돌 빈도를 줄여줍니다.

    이후 (선택) focus 키워드 윈도우 발췌 → max_chars 상한 적용 순으로 후처리.
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

    notes: list[str] = []

    if focus and focus.strip():
        focus_kw = focus.strip()
        extracted, hits = _focus_extract(md, focus_kw, FOCUS_WINDOW)
        if hits > 0:
            md = extracted
            notes.append(f"focused on '{focus_kw}', {hits} match{'es' if hits > 1 else ''}")
        else:
            notes.append(f"focus '{focus_kw}' not found — returning full body")

    cap = _clamp_max_chars(max_chars)
    if len(md) > cap:
        md = md[:cap]
        notes.append("truncated")

    suffix = f" ({'; '.join(notes)})" if notes else ""
    header = f"[Fetched from {url}]{suffix}"
    return f"{header}\n\n{md}"


# ── MCP 툴 ───────────────────────────────────────────────────────────────────

@mcp.tool()
def search_web(query: str, max_results: int = 5) -> str:
    """
    SearXNG로 웹 검색을 수행하고 제목·URL·스니펫을 반환합니다.

    Args:
        query: 검색 쿼리 문자열 (한글/영문 모두 가능).
        max_results: 반환할 결과 수 (1~10, 기본 5).

    Returns:
        제목·URL·스니펫이 번호 매겨진 텍스트 블록. 검색 실패 시 에러 메시지.
    """
    if not query or not query.strip():
        return "에러: 비어 있는 쿼리는 검색할 수 없습니다."
    n = max(1, min(int(max_results or 5), 10))
    logger.info(f"SearXNG 검색: '{query}' (top {n})")

    try:
        with httpx.Client(timeout=SEARXNG_TIMEOUT) as client:
            resp = client.get(
                f"{SEARXNG_URL}/search",
                params={
                    "q": query,
                    "format": "json",
                    "safesearch": 1,
                    "language": "ko",
                },
                headers={"User-Agent": "a2a-websearch-mcp/1.0"},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        return f"SearXNG 호출 실패 (HTTP {e.response.status_code}). settings.yml에서 JSON format이 활성화됐는지 확인하세요."
    except httpx.HTTPError as e:
        return f"SearXNG 연결 실패: {e}. 컨테이너가 실행 중인지 확인하세요 ({SEARXNG_URL})."
    except ValueError:
        return "SearXNG 응답을 JSON으로 파싱할 수 없습니다. settings.yml에서 JSON format이 활성화됐는지 확인하세요."

    results = data.get("results", [])
    if not results:
        return f"'{query}'에 대한 검색 결과가 없습니다."

    lines: list[str] = [f"[검색 결과 — '{query}' (top {n})]"]
    seen_urls: set[str] = set()
    count = 0
    for r in results:
        url = (r.get("url") or "").strip()
        if not url or url in seen_urls:
            continue
        host = (urlparse(url).hostname or "").lower()
        if _is_blocked_host(host):
            continue
        seen_urls.add(url)
        title = (r.get("title") or "").strip() or "(no title)"
        snippet = (r.get("content") or "").strip().replace("\n", " ")
        if len(snippet) > 300:
            snippet = snippet[:300] + "…"
        count += 1
        lines.append(f"{count}. {title}\n   URL: {url}\n   요약: {snippet}")
        if count >= n:
            break

    if count == 0:
        return f"'{query}': 모든 결과가 허용되지 않는 도메인입니다."
    return "\n\n".join(lines)


@mcp.tool()
async def fetch_url(url: str, focus: str | None = None, max_chars: int | None = None) -> str:
    """
    주어진 URL의 본문을 Markdown으로 추출합니다. 1차 httpx+BeautifulSoup,
    필요 시 Crawl4AI(Playwright)로 폴백합니다.

    출력 토큰 절약을 위해 두 가지 결정론적 옵션을 제공합니다 (LLM 호출 없음):

      - focus: 키워드가 주어지면 본문에서 그 키워드가 등장하는 위치
               ±2,000자 윈도우만 추출하여 반환합니다 (FETCH_FOCUS_WINDOW로 조정).
               여러 번 등장하면 각 윈도우가 '---' 로 구분돼 합쳐지고,
               인접/겹치는 윈도우는 자동으로 병합됩니다. 매치가 없으면
               전체 본문을 그대로 반환하며 헤더에 매치 실패가 표기됩니다.
      - max_chars: 최종 출력을 자를 글자 수 상한. 서버 최대 12,000자,
                   최소 500자로 클램프되며, None이면 서버 기본값(12,000) 사용.

    내부망/localhost/file·ftp·data·javascript scheme은 SSRF 방지를 위해 차단됩니다.

    Args:
        url: 가져올 페이지의 절대 URL (http/https).
        focus: (선택) 본문에서 발췌할 키워드. 토큰 절약용.
        max_chars: (선택) 출력 글자 수 상한 (500~12,000).

    Returns:
        Markdown 본문. 헤더에 focus 매치 수와 잘림 여부가 표기됩니다.
        실패 시 에러 메시지.
    """
    err = _validate_url(url)
    if err:
        return f"[fetch_url] 거부됨: {err}"
    logger.info(f"본문 추출: {url} (focus={focus!r}, max_chars={max_chars})")
    try:
        return await _do_fetch(url, focus, max_chars)
    except httpx.HTTPStatusError as e:
        return f"[fetch_url] HTTP {e.response.status_code}: {url}"
    except httpx.HTTPError as e:
        return f"[fetch_url] 네트워크 오류: {e}"
    except Exception as e:
        logger.exception("fetch_url 예외")
        return f"[fetch_url] 처리 실패: {e}"


if __name__ == "__main__":
    if not MCP_AUTH_TOKEN:
        logger.warning("MCP_AUTH_TOKEN이 설정되지 않았습니다 — 인증 없이 모든 요청을 허용합니다.")
    else:
        logger.info("MCP_AUTH_TOKEN 활성화 — Bearer 인증이 필요합니다.")
    logger.info(f"SearXNG endpoint: {SEARXNG_URL}")
    logger.info(f"Web Search MCP 서버 시작 (Streamable HTTP): http://{MCP_HOST}:{MCP_PORT}/mcp")

    app = _bearer_auth_middleware(mcp.streamable_http_app(), MCP_AUTH_TOKEN)
    uvicorn.run(app, host=MCP_HOST, port=MCP_PORT, log_level="info")
