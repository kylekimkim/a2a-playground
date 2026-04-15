# RAG Playground — 아키텍처 문서

## 목차
1. [시스템 개요](#1-시스템-개요)
2. [컴포넌트 구성](#2-컴포넌트-구성)
3. [프로토콜 규격 (A2A / JSON-RPC 2.0)](#3-프로토콜-규격-a2a--json-rpc-20)
4. [메시지 흐름 전체도](#4-메시지-흐름-전체도)
5. [오케스트레이터 내부 구조](#5-오케스트레이터-내부-구조)
6. [하위 에이전트 내부 구조](#6-하위-에이전트-내부-구조)
7. [에이전트 레지스트리 & 디스커버리](#7-에이전트-레지스트리--디스커버리)
8. [위임(Delegation) 실행 흐름](#8-위임delegation-실행-흐름)
9. [프론트엔드 구조](#9-프론트엔드-구조)
10. [데이터베이스 스키마](#10-데이터베이스-스키마)
11. [오케스트레이터 vs 하위 에이전트 비교](#11-오케스트레이터-vs-하위-에이전트-비교)
12. [에러 처리](#12-에러-처리)
13. [파일 구조 요약](#13-파일-구조-요약)

---

## 1. 시스템 개요

이 프로젝트는 **Agent-to-Agent (A2A) 프로토콜** 기반의 멀티 에이전트 오케스트레이션 시스템입니다.

- 사용자는 프론트엔드 채팅 UI를 통해 질문을 입력합니다.
- **오케스트레이터 백엔드**가 질문을 받아 LangGraph ReAct 에이전트로 처리합니다.
- 오케스트레이터는 질문의 성격에 따라 직접 답변하거나, 전문 **하위 에이전트**에게 위임합니다.
- 모든 통신은 **JSON-RPC 2.0** 요청 + **Server-Sent Events (SSE)** 스트리밍 응답으로 이루어집니다.
- 채팅 기록은 MariaDB에 저장되고 세션 간 유지됩니다. 하위 에이전트는 무상태(stateless)로 동작합니다.

```
[사용자]
   ↕ HTTP (SSE 스트리밍)
[프론트엔드 React, :5173]
   ↕ HTTP POST /chat (JSON-RPC 2.0)
[오케스트레이터 FastAPI, :8000]
   ↕ HTTP POST /chat (JSON-RPC 2.0, 위임 시)
[하위 에이전트들 FastAPI, :9001~9003]
   ↕ 외부 API (Nexon OpenAPI 등)
```

---

## 2. 컴포넌트 구성

| 컴포넌트 | 포트 | 역할 |
|---|---|---|
| `frontend/` | 5173 | React 채팅 UI |
| `backend/` | 8000 | 오케스트레이터 에이전트 |
| `maplestory-agent/` | 9001 | 메이플스토리 전문 에이전트 |
| `suddenattack-agent/` | 9002 | 서든어택 전문 에이전트 |
| `fconline-agent/` | 9003 | FC온라인 전문 에이전트 |
| `fortuneteller-agent/` | 9000 | 운세 전문 에이전트 (레지스트리 미등록) |
| MariaDB | 3306 | 채팅방 & 메시지 영속 저장 |

각 에이전트는 `/.well-known/agent.json` 엔드포인트를 통해 자신의 이름, 설명, 스킬 목록을 광고합니다.

---

## 3. 프로토콜 규격 (A2A / JSON-RPC 2.0)

### 3-1. 요청 형식

프론트엔드 → 오케스트레이터, 오케스트레이터 → 하위 에이전트 모두 동일한 형식을 사용합니다.

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "message/stream",
  "params": {
    "session_id": "room-uuid",
    "message": {
      "role": "user",
      "parts": [{ "type": "text", "text": "메이플스토리 루시다 캐릭터 정보 알려줘" }]
    },
    "metadata": { "model": "gpt-4o-mini" }
  }
}
```

> **참고**: 오케스트레이터 → 하위 에이전트 위임 시에는 `session_id`가 포함되지 않습니다. 하위 에이전트는 무상태이므로 히스토리를 사용하지 않습니다.

### 3-2. SSE 이벤트 타입

응답은 `text/event-stream` 형식으로 스트리밍됩니다. 이벤트는 크게 세 종류입니다.

**① 상태 변경 이벤트**
```
data: {
  "type": "task_status_update",
  "task_id": "uuid",
  "status": { "state": "submitted" },
  "final": false
}
```
- `state` 값: `submitted` → `working` → `completed` | `failed` | `canceled`
- `final: true`이면 스트림 종료를 의미합니다.

**② 응답 청크 이벤트**
```
data: {
  "type": "task_artifact_update",
  "task_id": "uuid",
  "artifact": {
    "index": 0,
    "parts": [{ "type": "text", "text": "루시다 캐릭터의 레벨은..." }],
    "last_chunk": false
  }
}
```
- 텍스트 토큰 단위로 스트리밍됩니다.
- 툴 실행 알림도 이 이벤트로 전달됩니다 (예: `> 🔍 웹 검색 툴 실행: "..."`).

**③ 에러 이벤트**
```
data: {
  "type": "error",
  "code": -32603,
  "message": "Internal error"
}
```

---

## 4. 메시지 흐름 전체도

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Frontend (React, :5173)                                                 │
│                                                                          │
│  useA2AClient.send(text)                                                 │
│    └─ a2aClient.subscribeTask(text, { sessionId, model })                │
│         └─ POST /chat  (JSON-RPC 2.0)                                    │
│              SSE ←─────────────────────────────────────────────────────  │
│              onDelta(chunk) → streamingText 업데이트                      │
│              onDone()       → messages[]에 최종 응답 추가                  │
└──────────────────────────────────────────────────────────────────────────┘
                │ POST /chat
                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Orchestrator Backend (FastAPI, :8000)                                   │
│                                                                          │
│  a2a_router.py                                                           │
│    └─ POST /chat                                                         │
│         ├─ JSON-RPC 파싱 및 검증                                          │
│         └─ StreamingResponse(event_generator())                          │
│                                                                          │
│  task_handler.py  handle_tasks_send_subscribe(params)                    │
│    ├─ [1] task 생성 (UUID)                                               │
│    ├─ [2] room_store에서 채팅 히스토리 로드 (session_id 기반)             │
│    ├─ [3] 사용자 메시지 DB 저장                                           │
│    ├─ [4] yield → task_status_update (submitted)                         │
│    ├─ [5] yield → task_status_update (working)                           │
│    │                                                                     │
│    └─ [6] agent.planner.build_graph() 실행                               │
│              ├─ LLM (GPT) 호출                                           │
│              │                                                           │
│              │   [직접 답변]                                              │
│              │     on_chat_model_stream 이벤트                           │
│              │       └─ yield → task_artifact_update (토큰 청크)         │
│              │                                                           │
│              │   [툴 호출]                                               │
│              │     on_tool_start 이벤트                                  │
│              │       └─ yield → task_artifact_update (툴 실행 알림)      │
│              │                                                           │
│              │     툴 실행:                                              │
│              │       ├─ get_datetime  → 현재 시각 반환                    │
│              │       ├─ calculator   → AST 기반 수식 계산                 │
│              │       ├─ web_search   → DuckDuckGo 검색                   │
│              │       └─ delegate_task → 하위 에이전트 호출 ──────────────┐│
│              │                                                           ││
│              └─ [7] 응답 완성                                            ││
│                   ├─ agent 메시지 DB 저장                                ││
│                   └─ yield → task_status_update (completed, final=true)  ││
│                                                                          ││
└──────────────────────────────────────────────────────────────────────────┘│
                                                                            │
                │ POST /chat (JSON-RPC 2.0, 위임)                          │
                ▼                                                           │
┌──────────────────────────────────────────────────────────────────────────┤
│  Sub-Agent (예: Maplestory Expert, :9001)                                │
│                                                                          │
│  a2a_router.py (오케스트레이터와 동일한 구조)                             │
│    └─ POST /chat                                                         │
│                                                                          │
│  task_handler.py  (무상태 버전)                                          │
│    ├─ DB 히스토리 로드 없음                                               │
│    ├─ DB 저장 없음                                                       │
│    └─ agent.planner.build_graph() 실행                                   │
│              ├─ 도메인 특화 시스템 프롬프트                               │
│              ├─ 도메인 특화 툴 (예: 13개 Nexon API 래퍼)                  │
│              └─ SSE 이벤트 스트리밍                                       │
│                                                                          │
│  delegate.py가 SSE 스트림을 수신·파싱하여                                 │
│  텍스트를 누적한 뒤 LLM 툴 결과로 반환                    ───────────────┘
└──────────────────────────────────────────────────────────────────────────┘
                │ Nexon OpenAPI, DuckDuckGo 등 외부 API
                ▼
          [외부 서비스]
```

---

## 5. 오케스트레이터 내부 구조

### 5-1. 라우터 구성 (`main.py`)

```
FastAPI app
  ├─ POST   /chat                  ← a2a_router (메인 스트리밍)
  ├─ GET    /.well-known/agent.json ← 자기 자신을 광고
  ├─ GET    /rooms                 ← rooms_router
  ├─ POST   /rooms
  ├─ PATCH  /rooms/{id}
  ├─ DELETE /rooms/{id}
  ├─ GET    /rooms/{id}/messages
  ├─ GET    /registry/agents       ← registry_router
  ├─ POST   /registry/agents
  └─ DELETE /registry/agents
```

### 5-2. task_handler 처리 흐름

```python
async def handle_tasks_send_subscribe(params):
    # 1. 태스크 초기화
    task = task_store.create_task()

    # 2. DB에서 채팅 히스토리 로드
    history = await room_store.get_messages(session_id)

    # 3. 사용자 메시지 DB 저장
    await room_store.save_message(session_id, role="user", content=...)

    # 4~5. 상태 이벤트 yield
    yield task_status_update("submitted")
    yield task_status_update("working")

    # 6. LangGraph 에이전트 실행 (스트리밍)
    graph = build_graph()
    async for event in graph.astream_events(messages, version="v2"):
        if event["name"] == "on_tool_start":
            yield task_artifact_update(tool_notice)   # 툴 실행 알림
        elif event["name"] == "on_chat_model_stream":
            yield task_artifact_update(token)         # LLM 토큰

    # 7. 완료
    await room_store.save_message(session_id, role="agent", content=accumulated)
    yield task_artifact_update("", last_chunk=True)
    yield task_status_update("completed", final=True)
```

### 5-3. LangGraph 에이전트 (`agent/planner.py`)

- **모델**: `gpt-4o-mini` (ChatOpenAI, temperature=0.7, streaming=True)
- **에이전트 타입**: LangGraph `create_react_agent` (ReAct 패턴)
- **시스템 프롬프트 구성**:
  1. 4단계 플래닝 원칙 (분석 → 계획 → 실행 → 합성)
  2. 사용 가능한 툴 목록 설명
  3. 응답 가이드라인 (한국어)
  4. **동적으로 주입**: 현재 온라인 상태인 하위 에이전트 목록 + 위임 지침
- **메시지 구성**: `[SystemMessage, ...history, HumanMessage(user_text)]`

### 5-4. 툴 목록

| 툴 이름 | 파일 | 설명 |
|---|---|---|
| `get_datetime` | `tools/datetime_tool.py` | 현재 날짜/시각 (타임존 지원) |
| `calculator` | `tools/calculator.py` | AST 기반 안전한 수식 계산 |
| `web_search` | `tools/web_search.py` | DuckDuckGo 웹 검색 (kr-kr) |
| `delegate_task` | `tools/delegate.py` | 하위 에이전트에게 작업 위임 |

---

## 6. 하위 에이전트 내부 구조

모든 하위 에이전트는 오케스트레이터와 **동일한 A2A 프로토콜 구조**를 공유하며, 다음 두 가지 점에서만 다릅니다.

### 6-1. 오케스트레이터와의 차이점

| 항목 | 오케스트레이터 | 하위 에이전트 |
|---|---|---|
| DB 히스토리 로드 | O (session_id로 조회) | X |
| DB 메시지 저장 | O | X |
| `delegate_task` 툴 | O | X (재위임 없음) |
| 시스템 프롬프트 | 범용 플래너 | 도메인 전문가 |
| 툴 구성 | 범용 4개 | 도메인 특화 툴 + 범용 툴 |
| 상태 | Stateful (세션 유지) | Stateless |

### 6-2. 하위 에이전트별 전문 툴

**maplestory-agent (:9001)**
- Nexon OpenAPI 래퍼 13종
- `get_character_ocid`, `get_character_basic`, `get_character_stat`, `get_character_equipment` 등

**suddenattack-agent (:9002)**
- 서든어택 관련 전문 툴

**fconline-agent (:9003)**
- FC온라인 Nexon OpenAPI 래퍼

**fortuneteller-agent (:9000)**
- 운세 관련 전문 툴
- 현재 레지스트리 `KNOWN_NODES`에 미등록 상태

---

## 7. 에이전트 레지스트리 & 디스커버리

### 7-1. KNOWN_NODES 초기값

```python
# backend/agent/registry.py
KNOWN_NODES = [
    "http://127.0.0.1:9001",  # maplestory-agent
    "http://127.0.0.1:9002",  # suddenattack-agent
    "http://127.0.0.1:9003",  # fconline-agent
]
```

런타임에 `POST /registry/agents`로 동적 추가/삭제가 가능합니다.

### 7-2. 에이전트 상태 조회 흐름

`GET /registry/agents`가 호출될 때마다:

```
for each node in KNOWN_NODES:
    GET {node}/.well-known/agent.json  (timeout=2s)
      ├─ 200 OK  → online=True,  card=응답 JSON, 캐시에 저장
      └─ 실패     → online=False, card=캐시에서 fallback
```

### 7-3. 시스템 프롬프트 동적 주입

오케스트레이터는 **매 요청마다** `get_available_agents_prompt_snippet()`을 호출하여 현재 온라인 에이전트 목록을 시스템 프롬프트에 주입합니다.

```
[현재 이용 가능한 특화 에이전트 목록]
당신은 다음 에이전트들에게 delegate_task 도구를 사용하여 작업을 위임할 수 있습니다.

에이전트 이름: Maplestory Expert Agent
대상 URL (target_url): http://localhost:9001/chat
설명: ...
보유 스킬:
- Maplestory Guide: ...
- Character Lookup: ...
```

이를 통해 LLM이 언제 어떤 에이전트에게 위임할지를 스스로 결정합니다.

### 7-4. agent.json 광고 형식

각 에이전트의 `agent_card.py`가 반환하는 구조:

```json
{
  "name": "Maplestory Expert Agent",
  "description": "메이플스토리 전문 에이전트",
  "url": "http://localhost:9001/chat",
  "version": "0.1.0",
  "provider": {
    "organization": "sjkim",
    "model": "gpt-4o-mini"
  },
  "capabilities": {
    "streaming": true,
    "pushNotifications": false
  },
  "skills": [
    { "id": "maplestory_guide", "name": "Maplestory Guide", "description": "..." },
    { "id": "character_lookup", "name": "Character Lookup",  "description": "..." }
  ]
}
```

---

## 8. 위임(Delegation) 실행 흐름

`delegate_task` 툴이 호출될 때의 상세 흐름입니다.

```python
# backend/agent/tools/delegate.py
async def delegate_task(target_url: str, task_description: str) -> str:

    # 1. JSON-RPC 요청 구성 (session_id 없음 — 무상태 호출)
    payload = {
        "jsonrpc": "2.0",
        "method": "message/stream",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": task_description}]
            }
        }
    }

    # 2. POST {target_url}  (timeout=15s)
    response = requests.post(target_url, json=payload, stream=True)

    # 3. SSE 스트림 파싱
    accumulated = ""
    for line in response.iter_lines():
        if line.startswith("data: "):
            event = json.loads(line[6:])
            if event["type"] == "task_artifact_update":
                for part in event["artifact"]["parts"]:
                    if part["type"] == "text":
                        accumulated += part["text"]

    # 4. 누적된 텍스트를 LLM 툴 결과로 반환
    return accumulated
```

오케스트레이터 LLM은 이 결과를 받아 최종 응답에 합성합니다.

---

## 9. 프론트엔드 구조

### 9-1. 핵심 파일 구성

```
frontend/src/
  ├─ App.jsx                    # 레이아웃, 패널 상태 관리
  ├─ hooks/
  │   ├─ useA2AClient.js        # 스트리밍 상태 관리 (messages, streamingText)
  │   ├─ useRooms.js            # 채팅방 CRUD 상태 관리
  │   └─ useAgentRegistry.js    # 에이전트 레지스트리 상태 (10초 폴링)
  ├─ api/
  │   ├─ a2aClient.js           # 저수준 SSE 스트리밍 클라이언트
  │   ├─ roomsClient.js         # 채팅방 REST API 호출
  │   └─ agentRegistryClient.js # 에이전트 레지스트리 REST API 호출
  └─ components/
      ├─ Sidebar.jsx            # 채팅방 목록
      ├─ ChatWindow.jsx         # 메시지 표시 영역
      ├─ InputBar.jsx           # 입력창 + 전송
      ├─ AgentPanel.jsx         # 에이전트 레지스트리 패널
      └─ MessageBubble.jsx      # 메시지 말풍선
```

### 9-2. 채팅 전송 흐름

```
사용자 입력
  └─ InputBar.onSend(text)
       └─ App.handleSendMessage(text, model)
            └─ useA2AClient.send(text, model, roomId)
                 ├─ messages에 user 메시지 추가
                 └─ a2aClient.subscribeTask(text, { sessionId: roomId, model })
                      ├─ fetch POST /chat  (JSON-RPC 2.0)
                      ├─ response.body.getReader() → 수동 SSE 파싱
                      │    ├─ onDelta(chunk) → streamingText 누적
                      │    └─ onDone()       → messages에 최종 응답 추가, streamingText 초기화
                      └─ AbortController 반환 (취소 지원)
```

### 9-3. SSE 수동 파싱 (`a2aClient.js`)

EventSource API를 사용하지 않고 `fetch` + `ReadableStream`으로 직접 파싱합니다. POST 요청을 사용해야 하기 때문입니다.

```javascript
const reader = response.body.getReader();
let buffer = "";

while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value);

    const events = buffer.split("\n\n");
    buffer = events.pop();  // 마지막 미완성 청크는 버퍼에 유지

    for (const event of events) {
        const dataLine = event.split("\n").find(l => l.startsWith("data: "));
        const parsed = JSON.parse(dataLine.slice(6));

        if (parsed.type === "task_artifact_update") {
            onDelta(parsed.artifact.parts[0].text);
        } else if (parsed.type === "task_status_update" && parsed.final) {
            onDone();
        }
    }
}
```

---

## 10. 데이터베이스 스키마

오케스트레이터만 MariaDB를 사용합니다. 하위 에이전트는 DB를 사용하지 않습니다.

```sql
-- 채팅방
CREATE TABLE rooms (
    id         VARCHAR(36)  PRIMARY KEY,
    title      VARCHAR(255) NOT NULL DEFAULT '새 채팅',
    created_at BIGINT       NOT NULL,  -- Unix ms
    updated_at BIGINT       NOT NULL
);

-- 메시지 (첫 user 메시지 40자가 방 제목으로 자동 설정됨)
CREATE TABLE messages (
    id         VARCHAR(36)  PRIMARY KEY,
    room_id    VARCHAR(36)  NOT NULL REFERENCES rooms(id),
    role       ENUM('user', 'agent') NOT NULL,
    content    LONGTEXT     NOT NULL,
    created_at BIGINT       NOT NULL
);
```

**연결 설정**: 환경변수 `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`로 구성하며 `aiomysql` 비동기 커넥션 풀을 사용합니다.

---

## 11. 오케스트레이터 vs 하위 에이전트 비교

```
                     ┌─────────────────────────────────────────────────────┐
                     │  공통 구조 (모든 에이전트)                           │
                     │                                                     │
                     │  main.py          → FastAPI 앱 + CORS + 라우터      │
                     │  a2a_router.py    → POST /chat (JSON-RPC 파싱)      │
                     │  task_handler.py  → SSE 스트리밍 로직               │
                     │  agent/planner.py → LangGraph ReAct 에이전트        │
                     │  models.py        → 공유 데이터 모델                │
                     │  task_store.py    → 인메모리 태스크 저장소           │
                     │  agent_card.py    → /.well-known/agent.json 광고    │
                     └─────────────────────────────────────────────────────┘

┌──────────────────────────────────┐  ┌────────────────────────────────────┐
│  오케스트레이터만의 구성          │  │  하위 에이전트만의 구성             │
│                                  │  │                                    │
│  rooms_router.py   채팅방 REST   │  │  도메인 특화 시스템 프롬프트        │
│  room_store.py     MariaDB 연동  │  │  도메인 특화 툴 모음               │
│  database.py       DB 커넥션 풀  │  │  (Nexon API, 운세 API 등)          │
│  registry_router.py 에이전트 관리│  │                                    │
│  agent/registry.py 디스커버리    │  │  무상태 처리                       │
│  agent/tools/delegate.py 위임    │  │  (히스토리 로드/저장 없음)          │
│                                  │  │                                    │
│  Stateful (세션 + DB)            │  │  Stateless (요청 단위)             │
└──────────────────────────────────┘  └────────────────────────────────────┘
```

---

## 12. 에러 처리

### JSON-RPC 에러 코드

| 코드 | 원인 | 발생 위치 |
|---|---|---|
| -32700 | JSON 파싱 실패 | a2a_router |
| -32601 | 지원하지 않는 method | a2a_router |
| -32602 | params 형식 오류 | a2a_router |
| -32603 | 내부 서버 오류 | task_handler |

### 위임 에러

`delegate_task`는 timeout(15초) 또는 연결 실패 시 에러 메시지 문자열을 LLM에게 반환합니다. LLM이 에러 내용을 인식하고 사용자에게 안내하는 방식으로 처리됩니다.

### 프론트엔드 에러

- `AbortError`: 사용자가 취소 버튼을 누른 경우 — 조용히 처리
- 기타 네트워크 오류: 에러 배너로 표시
- 에이전트 레지스트리 조회 실패: 패널 내 에러 메시지 표시

---

## 13. 파일 구조 요약

```
rag-playground/
├─ backend/                          # 오케스트레이터
│   ├─ main.py                       # FastAPI 진입점 (port 8000)
│   ├─ a2a_router.py                 # POST /chat — JSON-RPC 파싱 + SSE 응답
│   ├─ task_handler.py               # 핵심 스트리밍 로직 (LangGraph 실행)
│   ├─ task_store.py                 # 인메모리 태스크 저장소
│   ├─ rooms_router.py               # 채팅방 REST API
│   ├─ room_store.py                 # MariaDB 채팅 히스토리 CRUD
│   ├─ database.py                   # aiomysql 커넥션 풀
│   ├─ registry_router.py            # 에이전트 레지스트리 REST API
│   ├─ models.py                     # 공유 Pydantic 모델
│   ├─ agent_card.py                 # /.well-known/agent.json 반환
│   └─ agent/
│       ├─ planner.py                # LangGraph ReAct 에이전트 빌더
│       ├─ registry.py               # 에이전트 디스커버리 & 캐시
│       └─ tools/
│           ├─ delegate.py           # 하위 에이전트 위임 툴
│           ├─ web_search.py         # DuckDuckGo 검색 툴
│           ├─ calculator.py         # AST 계산기 툴
│           └─ datetime_tool.py      # 현재 시각 툴
│
├─ maplestory-agent/                 # 메이플스토리 전문 에이전트 (port 9001)
├─ suddenattack-agent/               # 서든어택 전문 에이전트 (port 9002)
├─ fconline-agent/                   # FC온라인 전문 에이전트 (port 9003)
├─ fortuneteller-agent/              # 운세 전문 에이전트 (port 9000, 미등록)
│   └─ [각 에이전트 구조 동일]
│       ├─ main.py
│       ├─ a2a_router.py
│       ├─ task_handler.py
│       ├─ task_store.py
│       ├─ models.py
│       ├─ agent_card.py
│       └─ agent/
│           ├─ planner.py
│           └─ tools/
│               ├─ [도메인 특화 툴들]
│               ├─ web_search.py
│               ├─ calculator.py
│               └─ datetime_tool.py
│
├─ frontend/                         # React 채팅 UI (port 5173)
│   └─ src/
│       ├─ App.jsx
│       ├─ hooks/
│       │   ├─ useA2AClient.js       # 스트리밍 채팅 상태 관리
│       │   ├─ useRooms.js           # 채팅방 상태 관리
│       │   └─ useAgentRegistry.js   # 에이전트 레지스트리 폴링
│       ├─ api/
│       │   ├─ a2aClient.js          # SSE 스트리밍 클라이언트
│       │   ├─ roomsClient.js        # 채팅방 REST 클라이언트
│       │   └─ agentRegistryClient.js
│       └─ components/
│           ├─ AgentPanel.jsx
│           ├─ ChatWindow.jsx
│           ├─ InputBar.jsx
│           ├─ MessageBubble.jsx
│           └─ Sidebar.jsx
│
├─ schema.sql                        # MariaDB 초기화 스크립트
└─ docs/
    └─ architecture.md               # 이 문서
```
