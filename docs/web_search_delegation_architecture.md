# Web Search Delegation — 아키텍처 & 소스 구조

본 문서는 사용자가 "최근 OpenAI 뉴스 알려줘" 같은 **웹 정보 요청**을 입력했을 때,
**프론트엔드 → 오케스트레이터 → web-search-agent → SearXNG / Crawl4AI / OpenAI** 로 흘러
최종 답변이 사용자에게 토큰 스트리밍으로 돌아오는 전체 흐름을 정리합니다.

기존 `docs/architecture.md`(시스템 전체)와 `docs/langgraph_react_web_agent_sdd.md`(SDD)
를 보조하는 **위임 경로 한정** 가이드입니다.

---

## 1. 한눈에 보는 구조

```
┌────────────────────────────────────────────────────────────────────────────┐
│  Browser (React, :5173)                                                    │
│   └─ a2aClient.subscribeTask()  ── fetch POST + ReadableStream             │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   │ HTTP POST /chat  (JSON-RPC 2.0 + SSE)
                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  Orchestrator Backend  (FastAPI, :8000)                                    │
│   ├─ a2a_router.py            JSON-RPC 파싱                                 │
│   ├─ task_handler.py          SSE 스트림 생성 + LangGraph 실행              │
│   ├─ agent/planner.py         ReAct + 시스템 프롬프트                       │
│   │     └─ tools: get_datetime, calculator, delegate_task, MCP tools       │
│   │              (※ 자체 web_search 도구는 제거됨)                          │
│   ├─ agent/registry.py        매 요청마다 KNOWN_NODES의 agent.json 폴링     │
│   │     └─ KNOWN_NODES: 9001/9002/9003/9004                                │
│   └─ agent/tools/delegate.py  HTTP POST → 대상 에이전트의 /chat            │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   │ HTTP POST /chat  (JSON-RPC 2.0 + SSE,
                                   │                   session_id 없음)
                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  web-search-agent  (FastAPI, :9004)                       ★ 본 문서의 주역  │
│   ├─ a2a_router.py            JSON-RPC 파싱                                 │
│   ├─ task_handler.py          SSE 스트림 (stateless)                        │
│   └─ agent/planner.py         ReAct + 웹검색 전용 프롬프트                  │
│         └─ tools/                                                          │
│             ├─ searxng_search.py    search_web()                           │
│             ├─ crawl4ai_fetch.py    fetch_url()                            │
│             ├─ compression.py       compress_text()                        │
│             └─ datetime_tool.py     get_datetime()                         │
└──────────┬───────────────────┬──────────────────────────┬──────────────────┘
           │                   │                          │
           │ HTTP GET          │ HTTP GET (+Playwright)   │ HTTPS
           ▼                   ▼                          ▼
   ┌──────────────┐    ┌──────────────────┐      ┌──────────────────┐
   │ SearXNG      │    │ Target Web Pages │      │ OpenAI API       │
   │ (Docker      │    │  (뉴스, 블로그   │      │  (LLM completion │
   │  :8080)      │    │   문서 등)       │      │   + 압축)        │
   └──────────────┘    └──────────────────┘      └──────────────────┘
```

핵심 결정:
- **오케스트레이터에는 자체 검색 도구가 없다.** 웹 정보 요청은 모두 `delegate_task`로 9004에게 위임.
- **web-search-agent는 stateless.** session_id를 받지 않으며 DB도 없다.
- **모든 통신은 A2A JSON-RPC 2.0 + SSE.** EventSource가 아닌 `fetch` + `ReadableStream`(프론트)
  와 `requests.iter_lines`(오케스트레이터)로 직접 파싱.

---

## 2. 위임이 자동으로 일어나는 이유

오케스트레이터의 시스템 프롬프트는 매 요청마다 다음 두 부분이 합쳐져 만들어집니다.

1. **정적 부분** (`backend/agent/planner.py:_SYSTEM_PROMPT_BASE`)

   ```text
   ...
   - delegate_task : 다른 특화된 에이전트에게 작업을 위임할 때 사용합니다.
     · 본 오케스트레이터는 자체 웹 검색 도구를 보유하지 않습니다.
     · 최신 뉴스, 실시간 정보, 사실 확인, 현재 이벤트, URL 본문 읽기 등
       웹에서 정보를 가져와야 하는 모든 요청은 반드시 하단 목록의
       'Web Search ReAct Agent'에게 delegate_task로 위임하세요.
   ...
   ```

2. **동적 부분** (`backend/agent/registry.py:get_available_agents_prompt_snippet()`)

   요청이 들어올 때마다 `KNOWN_NODES`(9001/9002/9003/**9004**)의 `/.well-known/agent.json`을
   2초 timeout으로 폴링하고, 응답을 시스템 프롬프트 끝에 다음 형식으로 주입합니다.

   ```text
   [현재 이용 가능한 특화 에이전트 목록]
   당신은 다음 에이전트들에게 `delegate_task` 도구를 사용하여 작업을 위임할 수 있습니다.

   에이전트 이름: Web Search ReAct Agent
   대상 URL (target_url): http://127.0.0.1:9004/chat
   설명: SearXNG + Crawl4AI 기반 웹검색 전용 에이전트 ...
   보유 스킬:
   - Agentic Web Search: ...
   - URL Deep Read: ...

   [위임 지침]
   사용자의 질문이 위 에이전트들의 전문 분야와 일치한다면, 해당하는 '대상 URL'을
   target_url 인자로 삼아 delegate_task를 호출하여 위임하세요.
   ```

→ LLM은 (1) "웹 정보는 무조건 위임"이라는 강한 지침과 (2) 실제 사용 가능한 target_url을
   동시에 보게 되므로, 자연스럽게 `delegate_task(target_url="http://127.0.0.1:9004/chat", ...)` 를 호출합니다.

---

## 3. 시퀀스 다이어그램 — 사용자 질문부터 최종 답변까지

```
사용자          Frontend           Orchestrator(:8000)        web-search-agent(:9004)        SearXNG/Crawl4AI/OpenAI
  │                │                       │                          │                            │
  │ "최근 OpenAI    │                       │                          │                            │
  │  뉴스 알려줘"   │                       │                          │                            │
  │───────────────>│                       │                          │                            │
  │                │ POST /chat            │                          │                            │
  │                │ (JSON-RPC, sessionId) │                          │                            │
  │                │──────────────────────>│                          │                            │
  │                │                       │ ① a2a_router.parse        │                            │
  │                │                       │ ② task_handler.start      │                            │
  │                │                       │    - room_store.load      │                            │
  │                │                       │    - persist user msg     │                            │
  │                │ SSE: submitted/working│                          │                            │
  │                │<──────────────────────│                          │                            │
  │                │                       │                          │                            │
  │                │                       │ ③ planner.build_graph     │                            │
  │                │                       │    + registry snippet     │                            │
  │                │                       │    (9004 카드 주입)        │                            │
  │                │                       │                          │                            │
  │                │                       │ ④ astream_events 시작     │                            │
  │                │                       │    LLM: tool_call         │                            │
  │                │                       │     delegate_task(        │                            │
  │                │                       │      target_url=9004/chat │                            │
  │                │                       │      task_description=...)│                            │
  │                │ SSE: 🤖 위임 알림     │                          │                            │
  │                │<──────────────────────│                          │                            │
  │                │                       │                          │                            │
  │                │                       │ ⑤ delegate.requests.post  │                          │
  │                │                       │   stream=True             │                            │
  │                │                       │   timeout=(10, 180)       │                            │
  │                │                       │──────────────────────────>│                            │
  │                │                       │                          │ ⑥ a2a_router.parse          │
  │                │                       │                          │ ⑦ task_handler.start        │
  │                │                       │                          │   (DB 없음)                 │
  │                │                       │                          │                            │
  │                │                       │                          │ ⑧ planner.build_graph       │
  │                │                       │                          │ ⑨ ReAct 루프 시작           │
  │                │                       │                          │                            │
  │                │                       │                          │  search_web(query)          │
  │                │                       │                          │────────────────────────────>│ SearXNG /search?format=json
  │                │                       │                          │<────────────────────────────│ JSON results
  │                │                       │                          │                            │
  │                │                       │                          │  fetch_url(url)             │
  │                │                       │                          │────────────────────────────>│ Crawl4AI/httpx GET
  │                │                       │                          │<────────────────────────────│ Markdown 본문
  │                │                       │                          │                            │
  │                │                       │                          │  compress_text(text, focus) │
  │                │                       │                          │────────────────────────────>│ OpenAI (저렴한 모델)
  │                │                       │                          │<────────────────────────────│ 요약 텍스트
  │                │                       │                          │                            │
  │                │                       │                          │  Reflection: 정보 부족?     │
  │                │                       │                          │  부족하면 ⑨로 돌아가 반복   │
  │                │                       │                          │  (recursion_limit=20)       │
  │                │                       │                          │                            │
  │                │                       │                          │ ⑩ Final synthesizer (LLM)   │
  │                │                       │                          │   Sources 섹션 포함          │
  │                │                       │                          │   토큰 스트리밍              │
  │                │                       │ <───── SSE 청크들 ───────│ on_chat_model_stream         │
  │                │                       │                          │                            │
  │                │                       │ ⑪ delegate.iter_lines     │                          │
  │                │                       │    artifact.text 누적     │                          │
  │                │                       │                          │                            │
  │                │                       │                          │ ⑫ SSE completed (final=True)│
  │                │                       │ <─────────────────────────│                            │
  │                │                       │                          │                            │
  │                │                       │ ⑬ tool result(누적 텍스트)│                          │
  │                │                       │    → 오케스트레이터 LLM   │                          │
  │                │                       │    에게 반환              │                            │
  │                │                       │                          │                            │
  │                │                       │ ⑭ LLM 최종 응답 합성       │                            │
  │                │                       │   (출처 인용 등 다시 정리) │                            │
  │                │ SSE: 토큰 청크들      │                          │                            │
  │                │<──────────────────────│                          │                            │
  │ UI 실시간 출력 │                       │                          │                            │
  │<───────────────│                       │                          │                            │
  │                │                       │ ⑮ room_store.save agent  │                            │
  │                │                       │    message (MariaDB)      │                            │
  │                │ SSE: completed final  │                          │                            │
  │                │<──────────────────────│                          │                            │
```

(번호는 4·5장의 코드 추적 표와 대응됩니다.)

---

## 4. 오케스트레이터 측 코드 추적

| # | 단계 | 파일 | 함수/심볼 |
|---|---|---|---|
| ① | JSON-RPC 파싱 | `backend/a2a_router.py` | `jsonrpc_endpoint()` |
| ② | 태스크 생성·이력 로드·user 메시지 영속화 | `backend/task_handler.py` | `handle_tasks_send_subscribe()`의 상단 |
| ③ | 시스템 프롬프트 빌드 (정적 + 동적) | `backend/agent/planner.py` | `_build_system_prompt()` + `build_messages()` |
| ③' | 9004 agent.json 폴링 + 프롬프트 주입 | `backend/agent/registry.py` | `get_available_agents_prompt_snippet()`, `fetch_agent_cards()` |
| ④ | LangGraph ReAct astream_events | `backend/task_handler.py` | `graph.astream_events(...)` |
| ⑤ | delegate_task 호출 → 9004로 POST | `backend/agent/tools/delegate.py` | `delegate_task()` |
| ⑪ | 9004의 SSE 스트림 수신·텍스트 누적 | `backend/agent/tools/delegate.py` | `for line in response.iter_lines()` 루프 |
| ⑭ | 위임 결과 받은 뒤 최종 합성 토큰 SSE | `backend/task_handler.py` | `on_chat_model_stream` 분기 |
| ⑮ | agent 메시지 DB 저장 + completed | `backend/task_handler.py` | `room_store.save_message`, `update_status("completed")` |

타임아웃 / 환경변수 (오케스트레이터):

| 환경변수 | 기본값 | 의미 |
|---|---|---|
| `DELEGATE_TIMEOUT_CONNECT` | `10` | 9004와의 TCP/HTTP 연결 timeout (초) |
| `DELEGATE_TIMEOUT_READ` | `180` | SSE 청크 *사이* 최대 idle 시간 (초) |

`requests`의 `timeout=(connect, read)` 의미는 *총 응답 시간* 이 아니라 *청크 사이 idle 시간*
이라는 점이 중요합니다. ReAct 루프 한 단계(예: Crawl4AI 첫 호출 + Playwright 부팅) 가
180초 안에 끝나면 timeout이 나지 않습니다.

---

## 5. web-search-agent 측 코드 추적

| # | 단계 | 파일 | 함수/심볼 |
|---|---|---|---|
| ⑥ | JSON-RPC 파싱 (수정된 except-as-e 패턴) | `web-search-agent/a2a_router.py` | `jsonrpc_endpoint()` |
| ⑦ | 태스크 생성 (DB 없음, stateless) | `web-search-agent/task_handler.py` | `handle_tasks_send_subscribe()` |
| ⑧ | ReAct 그래프 생성 + 메시지 빌드 | `web-search-agent/agent/planner.py` | `build_graph()`, `build_messages()` |
| ⑨ | ReAct 루프 (검색 → 크롤 → 압축 → reflection) | `web-search-agent/agent/planner.py` + `prebuilt.create_react_agent` | (시스템 프롬프트의 6단계 절차로 LLM이 자체 수행) |
| ⑨-a | SearXNG 호출 | `web-search-agent/agent/tools/searxng_search.py` | `search_web()` (httpx 동기) |
| ⑨-b | URL 본문 추출 | `web-search-agent/agent/tools/crawl4ai_fetch.py` | `fetch_url()` (async @tool, Crawl4AI → httpx+BS4 fallback) |
| ⑨-c | 압축 (별도 저렴 LLM) | `web-search-agent/agent/tools/compression.py` | `compress_text()` |
| ⑩ | 최종 답변 토큰 SSE | `web-search-agent/task_handler.py` | `on_chat_model_stream` 분기, `_make_artifact()` |
| ⑫ | completed + final=True 송신 | `web-search-agent/task_handler.py` | 마지막 yield |

도구 호출 알림(SSE):
- 매 도구가 호출될 때 `on_tool_start`에서 `_tool_notice()`가 blockquote 형식의
  텍스트(예: `> 🔍 **SearXNG 검색**: "..."`)를 artifact로 보내줍니다.
- 이게 청크로 흘러나오기 때문에, 오케스트레이터의 `DELEGATE_TIMEOUT_READ` idle도
  실질적으로 잘 갱신됩니다.

타임아웃 / 환경변수 (web-search-agent):

| 환경변수 | 기본값 | 의미 |
|---|---|---|
| `SEARXNG_URL` | `http://localhost:8080` | SearXNG base URL |
| `SEARXNG_TIMEOUT` | `10` | SearXNG HTTP 호출 timeout (초) |
| `FETCH_TIMEOUT` | `20` | `fetch_url` HTTP 호출 timeout (초) |
| `FETCH_MAX_CHARS` | `12000` | fetch 결과 본문 최대 문자 수 |
| `COMPRESSION_MAX_INPUT` | `15000` | `compress_text` 입력 최대 문자 수 |
| `COMPRESSION_MODEL` | `MODEL_NAME` | 압축 단계 모델 (분리하면 비용 절감) |

LangGraph `recursion_limit`은 `task_handler.py`에서 `20` 으로 설정 — 즉
"검색→크롤→압축→reflection" 사이클을 사실상 무한히 못 돌게 막는 안전장치입니다.

---

## 6. SSE 이벤트 두 단계의 관계 — passthrough(stream-through) 적용

오케스트레이터와 web-search-agent는 **각자 자신만의 SSE 스트림**을 만듭니다.

```
브라우저 ←─────── SSE A (오케스트레이터가 만든 스트림) ─────── 오케스트레이터
                                                                  │
                                                                  │ httpx.AsyncClient.stream
                                                                  │ (passthrough: 청크 단위 forward)
                                                                  ▼
                                                  SSE B (9004가 만든 스트림) ←── web-search-agent
```

본 시스템은 **passthrough(stream-through) 분기**를 채택해, web-search-agent처럼
`capabilities.passthrough: true`로 광고하는 에이전트의 경우 **오케스트레이터 LLM의 2차 합성을 건너뜁니다.**

### 6-1. 분기 조건

오케스트레이터 LLM이 `delegate_task(target_url, task_description)`를 호출하려는 순간,
`task_handler`가 `on_tool_start` 이벤트에서 가로채 다음을 판정합니다.

```python
if tool_name == "delegate_task":
    candidate_url = tool_input.get("target_url", "")
    if registry.is_passthrough_agent(candidate_url):
        # 위임 알림만 보내고 LangGraph 종료(break)
        # 이후 stream_delegate(url, desc)로 직접 청크 forward
```

`registry.is_passthrough_agent()`는 직전 폴링으로 채워진 `_AGENT_CACHE`에서
host:port가 일치하는 카드의 `capabilities.passthrough` 플래그를 확인합니다.
trailing slash / `/chat` 유무는 무시합니다.

### 6-2. 두 가지 흐름

**(A) passthrough 경로** — web-search-agent (9004) 와 같이 `passthrough=true`인 에이전트로 위임할 때:
1. SSE A로 `submitted` → `working` → 🤖 위임 알림 전송
2. **LangGraph 그래프 즉시 중단** (tool 실행 자체를 건너뜀, LLM 2차 호출 없음)
3. `delegate.stream_delegate(url, desc)` (httpx AsyncClient + `aiter_lines`) 가 9004의
   SSE B 청크를 받자마자 **그대로** SSE A 의 artifact로 forward
4. 9004 종료 → SSE A `last_chunk=True` → `completed final=True`
5. 누적 텍스트는 그대로 DB에도 저장 (대화 이력 유지)

**(B) 일반 경로** — 그 외 모든 sub-agent(maplestory, suddenattack, fconline 등):
1. 기존 흐름 그대로. `delegate_task` 도구가 SSE B 전체를 누적해 단일 문자열로 반환
2. 그 문자열이 도구 결과로 오케스트레이터 LLM에게 들어가고
3. LLM이 다시 합성한 답을 SSE A로 토큰 스트리밍 (LLM 2회 호출 = 기존 비용)

### 6-3. 효과

passthrough 경로에서는:
- **TTFT가 9004의 첫 토큰 시점과 동일해짐** (오케스트레이터 LLM 2차 호출 1–3 s 제거)
- 오케스트레이터 LLM 한 번만 호출되므로 토큰 비용 절감
- 사용자는 9004의 답(Sources 섹션 포함)을 그대로 봄 — 합성으로 인용 손상이 없음
- 트레이드오프: 오케스트레이터가 다른 도구 결과와 *조합*해 답을 만들 수 없음 (단일 위임 케이스에 한정)

### 6-4. 다른 에이전트에도 적용하는 법

새 sub-agent의 `agent_card.py`에 다음 한 줄만 추가하면 자동으로 passthrough 경로를 탑니다.

```python
"capabilities": {
    ...
    "passthrough": True,
},
```

오케스트레이터 측 코드 변경은 필요 없습니다 (`is_passthrough_agent`가 카드 플래그를 동적으로 확인).

---

## 7. 소스 구조 (이번 위임 경로와 관련된 파일만)

```
a2a-playground/
├── docs/
│   ├── architecture.md                            # 시스템 전체 (기존)
│   ├── SDD.md                                     # 전체 SDD (기존)
│   ├── langgraph_react_web_agent_sdd.md           # 웹검색 에이전트 SDD (기존)
│   └── web_search_delegation_architecture.md      # ★ 본 문서
│
├── backend/                                       # 오케스트레이터 :8000
│   ├── a2a_router.py                              # POST /chat 파싱
│   ├── task_handler.py                            # SSE 스트리밍 메인 루프
│   ├── room_store.py / database.py                # MariaDB 채팅방·메시지
│   └── agent/
│       ├── planner.py                             # 시스템 프롬프트 (위임 강조)
│       ├── registry.py                            # KNOWN_NODES + agent.json 폴링
│       └── tools/
│           ├── __init__.py                        # get_all_tools (web_search 제거됨)
│           ├── delegate.py                        # ★ HTTP POST → 9004
│           ├── datetime_tool.py
│           ├── calculator.py
│           └── mcp_tools.py
│
└── web-search-agent/                              # ★ 신설 sub-agent :9004
    ├── main.py                                    # FastAPI 부팅 (port 9004)
    ├── a2a_router.py                              # POST /chat 파싱 (버그 수정 버전)
    ├── task_handler.py                            # SSE (stateless)
    ├── task_store.py                              # 인메모리 태스크 dict
    ├── models.py                                  # A2A Pydantic 모델
    ├── agent_card.py                              # /.well-known/agent.json
    ├── requirements.txt
    ├── docker-compose.yml                         # SearXNG 컨테이너 (사용자가 별도 인스턴스를
    │                                              #  쓰는 경우 사용 안 해도 무방)
    ├── searxng/settings.yml                       # JSON format 활성화 설정
    ├── README.md
    └── agent/
        ├── planner.py                             # ReAct + 6단계 절차 시스템 프롬프트
        └── tools/
            ├── __init__.py
            ├── searxng_search.py                  # search_web (httpx, SearXNG JSON API)
            ├── crawl4ai_fetch.py                  # fetch_url (async, Crawl4AI + fallback)
            ├── compression.py                     # compress_text (별도 LLM)
            └── datetime_tool.py
```

---

## 8. 운영자 관점 체크리스트 (위임이 작동하지 않을 때)

| 증상 | 가장 흔한 원인 | 확인 방법 |
|---|---|---|
| LLM이 "웹 검색 도구가 없습니다"라고 답변 | 9004가 떠 있지 않거나, agent.json이 응답 안 함 | `curl http://127.0.0.1:9004/.well-known/agent.json` 으로 200 + JSON 확인 |
| `에이전트 위임 실패: ... Read timed out` | ReAct 한 단계가 `DELEGATE_TIMEOUT_READ`(기본 180s)를 초과 | Playwright Chromium 사전 설치, `.env`에 `DELEGATE_TIMEOUT_READ=300` 등 상향 |
| `에이전트 위임 실패: ... Connection refused` | 9004 프로세스 미실행 | `cd web-search-agent && python main.py` |
| SearXNG 결과 0건이 자주 나옴 | 컨테이너 cold start, `outgoing.request_timeout` 5초가 짧음 | `settings.yml`의 `outgoing.request_timeout: 10` 이상으로 상향 |
| 검색은 되는데 본문 추출 실패만 발생 | Playwright Chromium 미설치 → httpx fallback, JS 페이지 처리 불가 | `python -m playwright install chromium` |
| 백엔드 재시작 후에도 9004가 발견 안 됨 | `backend/agent/registry.py:KNOWN_NODES`에 9004 누락 또는 9004 응답 timeout(2초) | 코드 확인 + 9004 응답 속도 확인 |
| 답변에 출처 URL이 빠짐 | web-search-agent 시스템 프롬프트의 'Sources' 섹션 지침이 무시됨 (LLM 변덕) | recursion_limit 또는 모델을 더 강한 것으로 |

---

## 9. 의도적으로 구현하지 않은 부분

`docs/langgraph_react_web_agent_sdd.md` 의 풀스택 구성요소 중 다음은 **본 구현에 포함되지 않음**:

- OpenSearch 벡터/하이브리드 인덱스
- BGE-M3 임베딩
- Cross-Encoder Reranker
- Redis 캐시
- RabbitMQ 큐
- Kubernetes 배포

→ 본 구현은 SDD §19의 "소규모" 라인(단일 FastAPI + 외부 SearXNG)에 해당합니다.
   대규모로 확장할 때는 위 컴포넌트들을 단계적으로 추가하면 됩니다.

---

## 10. 관련 문서

- 시스템 전체 아키텍처 — `docs/architecture.md`
- A2A 프로토콜·API·DB 전체 명세 — `docs/SDD.md`
- 웹검색 에이전트 원본 SDD — `docs/langgraph_react_web_agent_sdd.md`
- 웹검색 에이전트 실행 가이드 — `web-search-agent/README.md`
- 리포지토리 onboarding — `CLAUDE.md`
