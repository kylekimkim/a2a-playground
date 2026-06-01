# Web Search ReAct Agent (port 9004)

SearXNG + Crawl4AI 기반 웹검색 전용 A2A sub-agent. LangGraph ReAct 패턴으로
**검색 → 본문 추출 → 압축 → 자기검증(reflection) → (필요 시) 재검색 → 최종 응답**을 수행하며,
다른 sub-agent와 동일하게 A2A JSON-RPC 2.0 + SSE 프로토콜(`POST /chat`)을 제공합니다.

설계 근거: [`docs/langgraph_react_web_agent_sdd.md`](../docs/langgraph_react_web_agent_sdd.md)

## 사전 요구사항

- Python 3.11+
- Docker (SearXNG 컨테이너 실행용)
- 저장소 루트 `.env`에 `OPENAI_API_KEY`가 설정돼 있어야 합니다.
- (선택) Crawl4AI가 Playwright를 사용하므로 첫 실행 시 자동으로 Chromium을 받습니다.
  Playwright 설치가 실패하면 자동으로 httpx + BeautifulSoup fallback을 사용합니다.

## 실행 순서

```bash
# 1. SearXNG 컨테이너 기동 (이 디렉토리에서)
docker compose up -d
#   - http://localhost:8888 에서 SearXNG UI 확인 가능
#   - JSON API: GET http://localhost:8888/search?q=test&format=json

# 2. (최초 1회) 의존성 설치
pip install -r requirements.txt
# Crawl4AI Playwright 드라이버 설치 (선택, 권장)
python -m playwright install chromium

# 3. 에이전트 실행
python main.py
#   - http://127.0.0.1:9004/.well-known/agent.json 에서 에이전트 카드 확인
```

## 환경 변수

저장소 루트 `.env`에서 읽습니다 (없어도 기본값으로 동작).

| 변수 | 기본값 | 설명 |
|---|---|---|
| `OPENAI_API_KEY` | (필수) | LLM 호출용 |
| `MODEL_NAME` | `gpt-5.4-mini` | ReAct 에이전트 메인 모델 |
| `COMPRESSION_MODEL` | `MODEL_NAME` 동일 | compress_text 호출 시 사용할 모델 (저렴한 모델로 분리 권장) |
| `SEARXNG_URL` | `http://localhost:8888` | SearXNG 인스턴스 base URL |
| `SEARXNG_TIMEOUT` | `10` | 검색 호출 타임아웃(초) |
| `FETCH_TIMEOUT` | `20` | URL fetch 타임아웃(초) |
| `FETCH_MAX_CHARS` | `12000` | fetch_url이 반환하는 본문 최대 문자 수 |
| `COMPRESSION_MAX_INPUT` | `15000` | compress_text 입력 최대 문자 수 |
| `LANGFUSE_*` | - | Langfuse 트레이싱 (기존 .env 키 재사용) |

## 오케스트레이터 통합

`backend/agent/registry.py:KNOWN_NODES`에 `http://127.0.0.1:9004`이 추가돼 있어,
백엔드 부팅 후 오케스트레이터가 `/.well-known/agent.json`을 통해 자동 발견하고
`delegate_task` 도구로 위임 호출합니다.

## 노드 매핑 (SDD ↔ 코드)

| SDD 노드 | 구현 |
|---|---|
| Planner | `agent/planner.py:SYSTEM_PROMPT`의 6단계 절차 (LLM 자체 수행) |
| Search Decision | ReAct LLM이 `search_web` 호출 여부 결정 |
| SearXNG Search | `agent/tools/searxng_search.py:search_web` |
| Crawl4AI Fetch | `agent/tools/crawl4ai_fetch.py:fetch_url` (실패 시 httpx fallback) |
| Compression | `agent/tools/compression.py:compress_text` (별도 LLM 호출) |
| Reflection | ReAct 루프 내 LLM 자체 판단 → 추가 `search_web` 호출 |
| Final Synthesizer | ReAct 종료 시 LLM 최종 응답 (Sources 섹션 포함) |
| Retrieval / Rerank / OpenSearch / Redis | **본 구현에서 제외** (SDD §17의 풀스택 옵션) |

## 한계 및 향후 확장

- OpenSearch 인덱싱·Rerank·Redis 캐시는 의도적으로 생략했습니다 (SDD §19 "소규모" 라인).
  대규모 운영이 필요하면 OpenSearch + BGE-M3 임베딩 + Reranker를 추가하세요.
- ReAct recursion_limit은 20으로 설정돼 있습니다 (`task_handler.py`).
- Crawl4AI fallback은 JS 렌더링이 필요한 페이지는 처리하지 못합니다.
