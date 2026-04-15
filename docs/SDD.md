# RAG Playground — 소프트웨어 설계 명세서 (SDD)

**문서 버전:** 1.0.0  
**작성일:** 2026-04-06  
**프로젝트명:** RAG Playground — A2A 멀티 에이전트 채팅 시스템

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [기술 스택](#3-기술-스택)
4. [컴포넌트 상세 설계](#4-컴포넌트-상세-설계)
   - 4.1 [오케스트레이터 백엔드](#41-오케스트레이터-백엔드-port-8000)
   - 4.2 [도메인 전문 에이전트](#42-도메인-전문-에이전트)
   - 4.3 [MCP 서버](#43-mcp-서버)
   - 4.4 [프론트엔드](#44-프론트엔드-port-5173)
5. [데이터 모델](#5-데이터-모델)
6. [통신 프로토콜](#6-통신-프로토콜-a2a--json-rpc-20)
7. [API 명세](#7-api-명세)
8. [에이전트 도구 명세](#8-에이전트-도구-명세)
9. [데이터베이스 설계](#9-데이터베이스-설계)
10. [상태 흐름 및 시퀀스 다이어그램](#10-상태-흐름-및-시퀀스-다이어그램)
11. [에러 처리](#11-에러-처리)
12. [환경 설정](#12-환경-설정)
13. [보안 설계](#13-보안-설계)
14. [확장성 및 운영](#14-확장성-및-운영)
15. [비기능 요구사항](#15-비기능-요구사항)

---

## 1. 프로젝트 개요

### 1.1 목적

RAG Playground는 **Agent-to-Agent (A2A) 프로토콜**을 기반으로 하는 멀티 에이전트 오케스트레이션 채팅 시스템이다. 단일 LLM 호출의 한계를 극복하기 위해 마스터 오케스트레이터가 도메인별 전문 에이전트에게 작업을 위임하는 계층적 위임 구조를 채택한다.

### 1.2 핵심 기능

| 기능 | 설명 |
|------|------|
| 멀티 에이전트 오케스트레이션 | 오케스트레이터가 사용자 의도를 파악해 적절한 전문 에이전트에게 위임 |
| 실시간 스트리밍 응답 | SSE(Server-Sent Events)를 통한 토큰 단위 스트리밍 |
| 대화 이력 관리 | MariaDB에 채팅방 및 메시지를 영속적으로 저장 |
| 파일 처리 | PDF, DOCX, XLSX, PPTX 파일 텍스트 추출 및 문서 생성 |
| 동적 에이전트 등록 | 런타임에 새 에이전트를 레지스트리에 등록/해제 |
| 도구 통합 | 웹 검색, 날씨, 계산기, 문서 생성 등 외부 도구 사용 |

### 1.3 시스템 범위

```
사용자 (브라우저)
    ↕ HTTP/SSE
프론트엔드 (React, Port 5173)
    ↕ HTTP/SSE
오케스트레이터 (FastAPI, Port 8000)
    ├─ MariaDB (Port 3306)
    ├─ MCP 서버들 (Ports 8100~8102)
    └─ 전문 에이전트들 (Ports 9000~9003)
```

---

## 2. 시스템 아키텍처

### 2.1 전체 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                        사용자 브라우저                            │
│                   React SPA (Port 5173)                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP POST /chat (JSON-RPC 2.0)
                           │ SSE 스트리밍 응답
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│              오케스트레이터 (FastAPI, Port 8000)                  │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ a2a_router  │  │ task_handler │  │    rooms_router        │  │
│  │ (JSON-RPC)  │  │ (SSE 스트림) │  │  (채팅방 REST API)      │  │
│  └─────────────┘  └──────────────┘  └────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              LangGraph ReAct 에이전트                      │   │
│  │  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌───────────┐   │   │
│  │  │ 계산기    │ │ 웹검색   │ │ 위임도구  │ │ MCP 도구  │   │   │
│  │  └──────────┘ └──────────┘ └───────────┘ └───────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────┬──────────────────────┬──────────────────────────────┘
            │                      │ HTTP A2A 위임
            ↓                      ↓
    ┌───────────────┐    ┌──────────────────────────────────────┐
    │   MariaDB     │    │        전문 에이전트 클러스터           │
    │  (Port 3306)  │    │  ┌───────────┐  ┌─────────────────┐  │
    │  - rooms      │    │  │ 메이플스토리│  │  서든어택 에이전트│  │
    │  - messages   │    │  │ (Port 9001)│  │  (Port 9002)    │  │
    └───────────────┘    │  └───────────┘  └─────────────────┘  │
                         │  ┌───────────┐  ┌─────────────────┐  │
    ┌──────────────────┐ │  │FC Online  │  │  운세 에이전트   │  │
    │    MCP 서버들     │ │  │(Port 9003)│  │  (Port 9000)    │  │
    │  ┌─────────────┐ │ │  └───────────┘  └─────────────────┘  │
    │  │Tika (8100)  │ │ └──────────────────────────────────────┘
    │  │Weather(8101)│ │
    │  │DocGen(8102) │ │
    │  └─────────────┘ │
    └──────────────────┘
```

### 2.2 계층 구조 정의

| 계층 | 컴포넌트 | 상태 | 역할 |
|------|---------|------|------|
| **프레젠테이션** | React SPA | - | 사용자 인터페이스, SSE 파싱 |
| **오케스트레이션** | FastAPI 오케스트레이터 | Stateful | 요청 조율, 이력 관리, 에이전트 위임 |
| **도메인 처리** | 전문 에이전트들 | Stateless | 특화 도메인 쿼리 처리 |
| **도구 레이어** | MCP 서버들 | Stateless | 파일 처리, 날씨, 문서 생성 |
| **영속성** | MariaDB | - | 채팅방 및 메시지 저장 |

---

## 3. 기술 스택

### 3.1 백엔드

| 라이브러리 | 버전 | 용도 |
|-----------|------|------|
| FastAPI | 0.135+ | REST API 프레임워크 |
| Uvicorn | 최신 | ASGI 서버 |
| LangChain | 0.3+ | LLM 추상화 계층 |
| LangGraph | 0.2+ | ReAct 에이전트 그래프 |
| langchain-openai | 최신 | OpenAI ChatGPT 연동 |
| langchain-mcp-adapters | 최신 | MCP 클라이언트 통합 |
| aiomysql | 0.2+ | 비동기 MariaDB 드라이버 |
| duckduckgo-search | 6.0+ | 웹 검색 |
| langfuse | 2.0+ | LLM 호출 관찰성 |
| pydantic | 2.0+ | 데이터 검증 |
| httpx / aiohttp | 최신 | 비동기 HTTP 클라이언트 |

### 3.2 프론트엔드

| 라이브러리 | 버전 | 용도 |
|-----------|------|------|
| React | 18.3.1 | UI 프레임워크 |
| Vite | 5.4.2 | 빌드 도구 및 개발 서버 |
| react-markdown | 10.1.0 | Markdown 렌더링 |

### 3.3 MCP 서버 의존성

| 라이브러리 | 용도 |
|-----------|------|
| fastmcp | MCP 서버 프레임워크 |
| pypdf | PDF 텍스트 추출 |
| python-docx | DOCX 처리 |
| openpyxl | XLSX 처리 |
| python-pptx | PPTX 처리 |
| pytesseract | OCR (이미지 기반 PDF) |
| httpx | 날씨 API HTTP 클라이언트 |

### 3.4 외부 API

| API | 용도 |
|-----|------|
| OpenAI API (GPT) | LLM 추론 엔진 |
| Nexon OpenAPI | 메이플스토리 캐릭터 데이터 |
| DuckDuckGo Search | 웹 검색 |
| OpenWeatherMap | 날씨 정보 |

---

## 4. 컴포넌트 상세 설계

### 4.1 오케스트레이터 백엔드 (Port 8000)

#### 4.1.1 모듈 구조

```
backend/
├── main.py               # FastAPI 앱 초기화, 라우터 등록, lifespan 훅
├── a2a_router.py         # POST /chat — JSON-RPC 2.0 파싱
├── task_handler.py       # SSE 스트리밍 생성기, 에이전트 실행 조율
├── task_store.py         # 인메모리 태스크 저장소 (UUID → Task 매핑)
├── room_store.py         # MariaDB CRUD (채팅방, 메시지)
├── database.py           # aiomysql 커넥션 풀 관리
├── rooms_router.py       # GET/POST/PATCH/DELETE /rooms 엔드포인트
├── registry_router.py    # 에이전트 레지스트리 관리 REST API
├── agent_card.py         # GET /.well-known/agent.json — 자기 소개 광고
├── models.py             # 공유 Pydantic 데이터 모델
├── upload_router.py      # POST /upload — 파일 업로드
├── download_router.py    # GET /download/{filename} — 파일 다운로드
└── agent/
    ├── planner.py        # LangGraph ReAct 에이전트 빌더
    ├── registry.py       # 서브 에이전트 탐색 및 캐싱
    └── tools/
        ├── delegate.py   # 서브 에이전트 위임 도구
        ├── web_search.py # DuckDuckGo 검색 도구
        ├── calculator.py # AST 기반 안전 계산기
        ├── datetime_tool.py # 타임존 인식 날짜/시간 도구
        └── mcp_tools.py  # MCP 클라이언트 도구 로딩
```

#### 4.1.2 요청 처리 흐름

```
① 프론트엔드 → POST /chat (JSON-RPC 2.0 페이로드)
   └─ a2a_router.py: JSON 파싱 → TaskSendParams 검증

② task_handler.py: SSE 스트리밍 시작
   ├─ task_store에 Task 생성 (state: submitted)
   ├─ room_store에서 대화 이력 로드 (session_id 있을 때)
   ├─ 사용자 메시지 DB 저장
   └─ state 전환: submitted → working

③ agent/planner.py: LLM 메시지 구성
   ├─ 시스템 프롬프트 (4단계 계획 지침 + 동적 에이전트 목록)
   ├─ DB 이력 → LangChain 메시지 변환
   └─ 현재 사용자 메시지 추가

④ LangGraph ReAct 루프 (최대 10회 반복)
   ├─ LLM 추론 (스트리밍): 도구 호출 여부 결정
   ├─ on_tool_start: 도구 호출 공지 SSE 전송
   ├─ 도구 실행 (delegate, web_search, calculator, MCP...)
   ├─ on_tool_end: 결과 반환
   └─ on_chat_model_stream: 토큰 단위 SSE 전송

⑤ 응답 완료
   ├─ 누적 에이전트 응답 DB 저장
   ├─ task_artifact_update (last_chunk=true) 전송
   └─ task_status_update (state=completed, final=true) 전송
```

#### 4.1.3 LangGraph 에이전트 설계

```python
# agent/planner.py

def build_graph(model: str) -> CompiledGraph:
    llm = ChatOpenAI(model=model, streaming=True, temperature=0.7)
    tools = get_all_tools()  # 기본 도구 + MCP 도구
    return create_react_agent(model=llm, tools=tools)

def build_messages(lc_history, user_text) -> list:
    dynamic_info = get_available_agents_prompt_snippet()
    system = BASE_SYSTEM_PROMPT + "\n\n" + dynamic_info
    return [SystemMessage(system)] + lc_history + [HumanMessage(user_text)]
```

**시스템 프롬프트 구조:**
1. **역할 정의** — 범용 AI 어시스턴트, 전문 에이전트 오케스트레이터
2. **4단계 계획 원칙** — 분석 → 계획 → 실행 → 종합
3. **도구 목록 및 사용 지침**
4. **동적 에이전트 정보** — 현재 온라인 에이전트 URL 및 설명 (요청마다 갱신)
5. **응답 가이드라인** — 출처 인용, 불확실성 인정

#### 4.1.4 에이전트 레지스트리

```python
# agent/registry.py

KNOWN_NODES = [
    "http://127.0.0.1:9001",  # 메이플스토리 전문 에이전트
    "http://127.0.0.1:9002",  # 서든어택 전문 에이전트
    "http://127.0.0.1:9003",  # FC Online 전문 에이전트
]

async def get_agent_card(base_url: str) -> dict | None:
    # GET {base_url}/.well-known/agent.json (2초 타임아웃)
    # 성공 시 _AGENT_CACHE에 저장
    # 실패 시 캐시된 카드 반환 (폴백)
```

---

### 4.2 도메인 전문 에이전트

#### 4.2.1 공통 특성

| 속성 | 값 |
|------|-----|
| 상태 | **Stateless** — DB 없음, 단일 요청 컨텍스트만 사용 |
| 프로토콜 | A2A JSON-RPC 2.0 (오케스트레이터와 동일) |
| 에이전트 광고 | `GET /.well-known/agent.json` |
| 세션 ID | 수신하지 않음 (무시) |

#### 4.2.2 에이전트 목록

| 에이전트 | Port | 도메인 | 전문 도구 |
|---------|------|--------|-----------|
| 메이플스토리 에이전트 | 9001 | 넥슨 게임 데이터 | 13개 Nexon OpenAPI 래퍼 |
| 서든어택 에이전트 | 9002 | FPS 게임 정보 | 웹 검색, 공식 API |
| FC Online 에이전트 | 9003 | 축구 게임 데이터 | 넥슨 FC Online API |
| 운세 에이전트 | 9000 | 점술/운세 | 날짜/시간, 사주 계산 |

#### 4.2.3 메이플스토리 에이전트 Nexon API 도구 목록

| 도구 | API 엔드포인트 | 설명 |
|------|--------------|------|
| `get_character_ocid` | `/maplestory/v1/id` | 캐릭터 OCID 조회 |
| `get_character_basic` | `/v1/character/basic` | 기본 정보 (레벨, 직업, 서버) |
| `get_character_stat` | `/v1/character/stat` | 능력치 (HP, MP, 공격력 등) |
| `get_character_equipment` | `/v1/character/item-equipment` | 장착 아이템 목록 |
| `get_character_ability` | `/v1/character/ability` | 어빌리티 정보 |
| `get_character_hyper_stat` | `/v1/character/hyper-stat` | 하이퍼스탯 |
| `get_character_propensity` | `/v1/character/propensity` | 성향 정보 |
| `get_character_hexa_matrix` | `/v1/character/hexamatrix` | 헥사 매트릭스 |
| `get_character_skill` | `/v1/character/skill` | 스킬 정보 |
| `get_character_link_skill` | `/v1/character/link-skill` | 링크 스킬 |
| `get_character_symbol` | `/v1/character/symbol-equipment` | 심볼 장비 |
| `get_character_pet` | `/v1/character/pet-equipment` | 펫 장비 |
| `get_character_cash_item` | `/v1/character/cashitem-equipment` | 캐시 아이템 |

---

### 4.3 MCP 서버

#### 4.3.1 Tika MCP 서버 (Port 8100)

**역할:** 다양한 형식의 파일에서 텍스트 추출

| 지원 형식 | 처리 방식 |
|----------|---------|
| PDF | pypdf 텍스트 추출 → OCR 폴백 (pytesseract) |
| DOCX | python-docx |
| XLSX | openpyxl (모든 시트) |
| PPTX | python-pptx (모든 슬라이드) |
| TXT/MD/CSV/JSON/XML/HTML | 직접 읽기 |

**제공 도구:**
- `extract_text_from_file(file_path: str) → str` — 텍스트 내용 반환
- `get_file_metadata(file_path: str) → str` — MIME 타입, 작성자, 페이지 수 등

#### 4.3.2 Weather MCP 서버 (Port 8101)

**역할:** OpenWeatherMap API 래퍼

**제공 도구:**
- `get_current_weather(city: str, units: str = "metric") → str`
- `get_weather_forecast(city: str, days: int = 5, units: str = "metric") → str`
- `get_weather_by_coords(lat: float, lon: float, units: str = "metric") → str`

#### 4.3.3 DocGen MCP 서버 (Port 8102)

**역할:** LLM 응답 기반 문서 파일 생성

**제공 도구:**
- `create_document(filename: str, content: str, format: str) → str`
  - 지원 형식: DOCX, XLSX, TXT, MD
  - Markdown 헤더(`#`~`####`) 및 리스트(`-`, `*`, `•`) 자동 파싱
  - `/output/` 디렉토리에 저장
  - 반환값: 다운로드 URL (`/download/{filename}`)

---

### 4.4 프론트엔드 (Port 5173)

#### 4.4.1 컴포넌트 구조

```
App.jsx (루트 레이아웃 + 상태 오케스트레이션)
├── Sidebar.jsx          채팅방 목록, 방 생성/삭제
├── ChatWindow.jsx       메시지 표시 영역
│   └── MessageBubble.jsx  개별 메시지 (Markdown 렌더링, 다운로드 링크)
├── InputBar.jsx         텍스트 입력 + 파일 첨부
└── AgentPanel.jsx       에이전트 레지스트리 관리 패널
```

#### 4.4.2 커스텀 훅

| 훅 | 상태 | 주요 기능 |
|----|------|---------|
| `useRooms()` | `rooms[], activeRoomId` | 채팅방 CRUD, 자동 초기 로드 |
| `useA2AClient()` | `messages[], streamingText, isStreaming` | SSE 스트리밍, 메시지 누적, abort 지원 |
| `useAgentRegistry()` | `agents[], loading` | 10초 폴링, 에이전트 추가/삭제 |

#### 4.4.3 SSE 클라이언트 설계 (`a2aClient.js`)

> EventSource API는 GET 요청만 지원하므로 사용 불가. `fetch` + `ReadableStream`을 직접 구현.

```javascript
// 핵심 로직
async function subscribeTask(text, { sessionId, model, onDelta, onDone, onError }) {
    const controller = new AbortController();
    const response = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildJsonRpcPayload(text, sessionId, model)),
        signal: controller.signal
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        // "data: {...}\n\n" 단위로 분리 및 파싱
        // task_artifact_update → onDelta(text)
        // task_status_update (final=true) → onDone()
        // error → onError(msg)
    }
    return controller; // abort 지원
}
```

#### 4.4.4 메시지 렌더링 규칙 (`MessageBubble.jsx`)

| 조건 | 렌더링 방식 |
|------|-----------|
| 일반 텍스트/Markdown | react-markdown으로 렌더링 |
| `/download/` 경로 감지 | 스타일된 다운로드 버튼 삽입 |
| `> [🔧 도구명]` 블록쿼트 | MCP 도구: 초록색, 기타: 남색 강조 |
| 스트리밍 중 | 끝에 깜빡이는 커서 표시 |
| 역할 구분 | 사용자: 파란 배경, 에이전트: 어두운 배경 |

#### 4.4.5 Vite 프록시 설정

```javascript
// vite.config.js
proxy: {
    '/.well-known': 'http://localhost:8000',
    '/rooms':       'http://localhost:8000',
    '/chat':        'http://localhost:8000',
    '/upload':      'http://localhost:8000',
    '/download':    'http://localhost:8000',
}
```

---

## 5. 데이터 모델

### 5.1 공유 Pydantic 모델 (`backend/models.py`)

```python
# 메시지 파트
class TextPart(BaseModel):
    type: Literal["text"] = "text"
    text: str

# 메시지
class Message(BaseModel):
    role: Literal["user", "agent"]
    parts: List[TextPart]

# 태스크 상태
class TaskState(str, Enum):
    SUBMITTED = "submitted"
    WORKING   = "working"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELED  = "canceled"

class TaskStatus(BaseModel):
    state: TaskState
    message: Optional[Message] = None

# 태스크
class Task(BaseModel):
    id:         str
    session_id: Optional[str]
    status:     TaskStatus
    messages:   List[Message] = []
    artifacts:  List[Artifact] = []
    metadata:   dict = {}

# 아티팩트 (응답 청크)
class Artifact(BaseModel):
    index:      int
    parts:      List[TextPart]
    last_chunk: bool = False

# JSON-RPC 2.0
class JsonRpcRequest(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id:      str
    method:  str
    params:  dict

class JsonRpcResponse(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id:      str
    result:  Optional[dict] = None
    error:   Optional[JsonRpcError] = None

class JsonRpcError(BaseModel):
    code:    int
    message: str
    data:    Optional[Any] = None

# 태스크 요청 파라미터
class TaskSendParams(BaseModel):
    session_id: Optional[str] = None
    message:    Message
    metadata:   dict = {}

# SSE 이벤트
class TaskStatusUpdateEvent(BaseModel):
    type:    Literal["task_status_update"]
    task_id: str
    status:  TaskStatus
    final:   bool = False

class TaskArtifactUpdateEvent(BaseModel):
    type:     Literal["task_artifact_update"]
    task_id:  str
    artifact: Artifact
```

### 5.2 에이전트 카드 (`agent_card.py`)

```python
{
    "name":        str,      # 에이전트 표시명
    "description": str,      # 기능 설명
    "url":         str,      # A2A 엔드포인트 URL
    "version":     str,      # 버전
    "provider": {
        "organization": str,
        "model":        str
    },
    "skills": [
        {
            "id":          str,
            "name":        str,
            "description": str
        }
    ]
}
```

---

## 6. 통신 프로토콜 (A2A / JSON-RPC 2.0)

### 6.1 요청 형식

**A2A 채팅 요청** (프론트엔드 → 오케스트레이터, 또는 오케스트레이터 → 서브 에이전트):

```json
{
  "jsonrpc": "2.0",
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "message/stream",
  "params": {
    "session_id": "room-uuid",
    "message": {
      "role": "user",
      "parts": [{"type": "text", "text": "메이플스토리 캐릭터 아케인이 궁금해"}]
    },
    "metadata": {
      "model": "gpt-5.4-mini"
    }
  }
}
```

> 서브 에이전트 위임 시: `session_id` 필드 생략 (Stateless)

### 6.2 SSE 응답 이벤트 형식

**상태 업데이트 이벤트:**
```
data: {"type":"task_status_update","task_id":"uuid","status":{"state":"submitted"},"final":false}

data: {"type":"task_status_update","task_id":"uuid","status":{"state":"working"},"final":false}

data: {"type":"task_status_update","task_id":"uuid","status":{"state":"completed"},"final":true}
```

**응답 텍스트 이벤트:**
```
data: {"type":"task_artifact_update","task_id":"uuid","artifact":{"index":0,"parts":[{"type":"text","text":"안"}],"last_chunk":false}}

data: {"type":"task_artifact_update","task_id":"uuid","artifact":{"index":0,"parts":[{"type":"text","text":"녕"}],"last_chunk":false}}

data: {"type":"task_artifact_update","task_id":"uuid","artifact":{"index":0,"parts":[{"type":"text","text":"하세요"}],"last_chunk":true}}
```

**도구 호출 공지 이벤트:**
```
data: {"type":"task_artifact_update","task_id":"uuid","artifact":{"index":0,"parts":[{"type":"text","text":"> [🔧 web_search] 호출 중..."}],"last_chunk":false}}
```

**에러 이벤트:**
```
data: {"type":"error","code":-32603,"message":"Internal server error"}
```

**HTTP 응답 헤더:**
```
Content-Type: text/event-stream
Cache-Control: no-cache
X-Accel-Buffering: no
```

### 6.3 지원 메서드

| 메서드 | 설명 |
|--------|------|
| `message/stream` | SSE 스트리밍 채팅 요청 (유일하게 지원되는 메서드) |

---

## 7. API 명세

### 7.1 오케스트레이터 REST API (Port 8000)

#### A2A 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/chat` | A2A JSON-RPC 2.0 채팅 (SSE 스트리밍) |
| `GET` | `/.well-known/agent.json` | 에이전트 카드 광고 |

#### 채팅방 API

| 메서드 | 경로 | 설명 | 요청 바디 |
|--------|------|------|---------|
| `GET` | `/rooms` | 채팅방 목록 조회 (updated_at DESC) | - |
| `POST` | `/rooms` | 새 채팅방 생성 | `{"title": "string", "model": "string"}` |
| `GET` | `/rooms/{room_id}` | 채팅방 상세 조회 | - |
| `PATCH` | `/rooms/{room_id}` | 채팅방 제목 수정 | `{"title": "string"}` |
| `DELETE` | `/rooms/{room_id}` | 채팅방 삭제 (메시지 CASCADE) | - |
| `GET` | `/rooms/{room_id}/messages` | 메시지 이력 조회 (created_at ASC) | - |

#### 에이전트 레지스트리 API

| 메서드 | 경로 | 설명 | 요청 바디 |
|--------|------|------|---------|
| `GET` | `/registry/agents` | 등록된 에이전트 목록 + 온라인 상태 조회 | - |
| `POST` | `/registry/agents` | 새 에이전트 URL 등록 | `{"url": "string"}` |
| `DELETE` | `/registry/agents` | 에이전트 URL 제거 | `{"url": "string"}` |

#### 파일 API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/upload` | 파일 업로드 (multipart/form-data) |
| `GET` | `/download/{filename}` | 파일 다운로드 |

**파일 업로드 제한:**
- 최대 크기: 50 MB
- 허용 확장자: `.pdf`, `.docx`, `.xlsx`, `.pptx`, `.txt`, `.md`, `.csv`, `.json`, `.xml`, `.html`

### 7.2 서브 에이전트 API (각 Port)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/chat` | A2A JSON-RPC 2.0 채팅 (SSE 스트리밍) |
| `GET` | `/.well-known/agent.json` | 에이전트 카드 |

### 7.3 MCP 서버 엔드포인트

| 서버 | Port | 엔드포인트 | 프로토콜 |
|------|------|-----------|---------|
| Tika | 8100 | `/sse` | MCP over SSE |
| Weather | 8101 | `/sse` | MCP over SSE |
| DocGen | 8102 | `/sse` | MCP over SSE |

---

## 8. 에이전트 도구 명세

### 8.1 오케스트레이터 도구

#### `get_datetime`

```python
@tool
def get_datetime(timezone: str = "Asia/Seoul") -> str:
    """현재 날짜와 시간을 반환합니다."""
```

- 기본 타임존: Asia/Seoul
- 반환 형식: ISO 8601 문자열

#### `calculator`

```python
@tool
def calculator(expression: str) -> str:
    """수학 표현식을 안전하게 계산합니다."""
```

- AST 파싱 기반 (eval 미사용 — 보안)
- 지원 연산: `+`, `-`, `*`, `/`, `**`, `%`, 비교 연산
- 오류 시: 에러 메시지 문자열 반환

#### `web_search`

```python
@tool
def web_search(query: str, max_results: int = 5) -> str:
    """DuckDuckGo로 웹 검색을 수행합니다."""
```

- 지역: `kr-kr`
- 결과 수: 최대 5건
- 반환: 제목 + URL + 요약 텍스트

#### `delegate_task`

```python
@tool
async def delegate_task(target_url: str, task_description: str) -> str:
    """지정된 URL의 전문 에이전트에게 작업을 위임합니다."""
```

- `target_url`: 에이전트 `/chat` 엔드포인트 URL
- `task_description`: 위임할 작업 설명 (자연어)
- 타임아웃: 15초
- SSE 응답 파싱 → `task_artifact_update` 텍스트 누적 → 문자열 반환

### 8.2 MCP 도구 (오케스트레이터에서 사용)

| 도구명 | MCP 서버 | 설명 |
|--------|---------|------|
| `extract_text_from_file` | Tika (8100) | 파일 경로 → 텍스트 내용 |
| `get_file_metadata` | Tika (8100) | 파일 경로 → 메타데이터 |
| `get_current_weather` | Weather (8101) | 도시명 → 현재 날씨 |
| `get_weather_forecast` | Weather (8101) | 도시명, 일수 → 예보 |
| `get_weather_by_coords` | Weather (8101) | 위경도 → 현재 날씨 |
| `create_document` | DocGen (8102) | 파일명, 내용, 형식 → 다운로드 URL |

---

## 9. 데이터베이스 설계

### 9.1 MariaDB 스키마

**적용 대상:** 오케스트레이터만 (서브 에이전트는 DB 없음)

```sql
-- 채팅방 테이블
CREATE TABLE rooms (
    id         CHAR(36)     NOT NULL PRIMARY KEY,      -- UUID
    title      VARCHAR(100) NOT NULL DEFAULT 'New Chat',
    model      VARCHAR(50)  NOT NULL DEFAULT 'gpt-5.4-mini',
    created_at BIGINT       NOT NULL,                  -- Unix 밀리초
    updated_at BIGINT       NOT NULL,                  -- Unix 밀리초 (새 메시지마다 갱신)
    INDEX idx_rooms_updated (updated_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 메시지 테이블
CREATE TABLE messages (
    id         CHAR(36)              NOT NULL PRIMARY KEY,
    room_id    CHAR(36)              NOT NULL,
    role       ENUM('user','agent')  NOT NULL,
    content    TEXT                  NOT NULL,
    created_at BIGINT                NOT NULL,
    FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
    INDEX idx_messages_room (room_id, created_at ASC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 9.2 커넥션 풀 설정

```python
# database.py
pool = await aiomysql.create_pool(
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
    db=DB_NAME,
    charset='utf8mb4',
    minsize=2,
    maxsize=10,
    autocommit=True
)
```

### 9.3 room_store.py 주요 연산

| 함수 | SQL | 설명 |
|------|-----|------|
| `create_room()` | `INSERT INTO rooms` | UUID 생성 후 삽입 |
| `list_rooms()` | `SELECT * ORDER BY updated_at DESC` | 최근 활동순 목록 |
| `get_messages(room_id)` | `SELECT * WHERE room_id ORDER BY created_at ASC` | 대화 이력 |
| `save_message(...)` | `INSERT INTO messages` + `UPDATE rooms SET updated_at` | 메시지 저장 + 방 갱신 |
| `update_room_title(...)` | `UPDATE rooms SET title` | 첫 메시지 기반 자동 제목 설정 |
| `delete_room(room_id)` | `DELETE FROM rooms` | 메시지 CASCADE 삭제 |

---

## 10. 상태 흐름 및 시퀀스 다이어그램

### 10.1 태스크 상태 전이

```
[submitted] → [working] → [completed]
                       ↘ [failed]
           ↘ [canceled]  (abort 신호 수신 시)
```

### 10.2 전체 채팅 시퀀스 (서브 에이전트 위임 포함)

```
사용자         프론트엔드       오케스트레이터       서브에이전트       MariaDB
  │               │                 │                  │               │
  │  메시지 입력   │                 │                  │               │
  │──────────────>│                 │                  │               │
  │               │  POST /chat     │                  │               │
  │               │  JSON-RPC 2.0   │                  │               │
  │               │────────────────>│                  │               │
  │               │                 │  이력 로드        │               │
  │               │                 │──────────────────────────────────>
  │               │                 │<──────────────────────────────────
  │               │  SSE: submitted │                  │               │
  │               │<────────────────│                  │               │
  │               │  SSE: working   │                  │               │
  │               │<────────────────│                  │               │
  │               │                 │  사용자 메시지 저장│               │
  │               │                 │──────────────────────────────────>
  │               │                 │                  │               │
  │               │                 │  LLM 추론        │               │
  │               │                 │  (도구 호출 결정) │               │
  │               │                 │                  │               │
  │               │  SSE: 🔧 도구   │                  │               │
  │               │<────────────────│                  │               │
  │               │                 │  POST /chat      │               │
  │               │                 │  delegate_task   │               │
  │               │                 │─────────────────>│               │
  │               │                 │  SSE 응답 누적    │               │
  │               │                 │<─────────────────│               │
  │               │                 │                  │               │
  │               │                 │  LLM 최종 응답   │               │
  │               │  SSE: 토큰들    │  (스트리밍)       │               │
  │               │<────────────────│                  │               │
  │ UI 실시간 출력 │                 │                  │               │
  │<──────────────│                 │                  │               │
  │               │                 │  에이전트 응답 저장│               │
  │               │                 │──────────────────────────────────>
  │               │  SSE: completed │                  │               │
  │               │<────────────────│                  │               │
```

### 10.3 에이전트 레지스트리 갱신 흐름 (프론트엔드 폴링)

```
프론트엔드                      오케스트레이터                   서브 에이전트들
    │                               │                              │
    │  [10초마다]                    │                              │
    │  GET /registry/agents          │                              │
    │──────────────────────────────>│                              │
    │                               │  GET /.well-known/agent.json │
    │                               │─────────────────────────────>│ (병렬, 2초 타임아웃)
    │                               │<─────────────────────────────│
    │  [{name, url, online, ...}]   │  (오프라인이면 캐시에서 반환)   │
    │<──────────────────────────────│                              │
    │  UI 상태 표시 갱신              │                              │
```

---

## 11. 에러 처리

### 11.1 JSON-RPC 에러 코드

| 코드 | 의미 | 발생 위치 |
|------|------|---------|
| `-32700` | Parse error (JSON 파싱 실패) | `a2a_router.py` |
| `-32601` | Method not found (`message/stream` 외) | `a2a_router.py` |
| `-32602` | Invalid params (TaskSendParams 검증 실패) | `a2a_router.py` |
| `-32603` | Internal server error (LangGraph 예외 등) | `task_handler.py` |

### 11.2 특수 에러 처리

| 상황 | 처리 방식 |
|------|---------|
| `GraphRecursionError` (도구 10회 초과) | 사용자 친화적 메시지: "도구 호출 한도에 도달했습니다" |
| 서브 에이전트 타임아웃 (15초) | 에러 문자열을 LLM에 반환, LLM이 사용자에게 안내 |
| 파일 업로드 크기 초과 | HTTP 413 응답 |
| 허용되지 않는 파일 형식 | HTTP 400 응답 |
| 에이전트 카드 조회 실패 | 캐시된 카드 사용 (폴백), 없으면 목록에서 제외 |
| 프론트엔드 AbortError | 조용히 무시 (사용자가 직접 중단한 경우) |

### 11.3 에러 SSE 이벤트 형식

```json
{
  "type": "error",
  "code": -32603,
  "message": "내부 서버 오류가 발생했습니다"
}
```

---

## 12. 환경 설정

### 12.1 `.env` 파일 항목

```ini
# OpenAI
OPENAI_API_KEY=sk-...
MODEL_NAME=gpt-5.4-mini

# MariaDB (오케스트레이터 전용)
DB_HOST=localhost
DB_PORT=3306
DB_NAME=rag-playground
DB_USER=root
DB_PASSWORD=<비밀번호>

# Langfuse (LLM 관찰성)
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3000

# 외부 API
OPENWEATHER_API_KEY=<키>
NEXON_API_KEY=<키>

# MCP 서버 URL
TIKA_MCP_URL=http://127.0.0.1:8100/sse
WEATHER_MCP_URL=http://127.0.0.1:8101/sse
DOCGEN_MCP_URL=http://127.0.0.1:8102/sse

# DocGen 서버용 백엔드 URL (다운로드 링크 생성)
BACKEND_URL=http://localhost:8000
```

### 12.2 포트 할당 요약

| 서비스 | Port |
|--------|------|
| 프론트엔드 (Vite 개발 서버) | 5173 |
| 오케스트레이터 (FastAPI) | 8000 |
| Tika MCP 서버 | 8100 |
| Weather MCP 서버 | 8101 |
| DocGen MCP 서버 | 8102 |
| 운세 에이전트 | 9000 |
| 메이플스토리 에이전트 | 9001 |
| 서든어택 에이전트 | 9002 |
| FC Online 에이전트 | 9003 |
| MariaDB | 3306 |
| Langfuse (선택) | 3000 |

---

## 13. 보안 설계

### 13.1 적용된 보안 조치

| 항목 | 조치 |
|------|------|
| **CORS** | `localhost:5173`만 허용 (프로덕션 배포 시 수정 필요) |
| **계산기 안전성** | `eval()` 미사용, AST 파싱 기반 수식 평가 |
| **파일 업로드** | 확장자 화이트리스트, 50MB 크기 제한 |
| **SQL 인젝션** | aiomysql 파라미터 바인딩 (`%s` 플레이스홀더) |
| **API 키 보안** | `.env` 파일로 분리, 코드에 하드코딩 없음 |
| **에이전트 검증** | `/.well-known/agent.json` 응답 스키마 검증 |

### 13.2 미적용 / 향후 고려 사항

| 항목 | 현황 | 권고 |
|------|------|------|
| 인증/인가 | 미적용 | JWT 또는 세션 기반 인증 추가 |
| 요청 레이트 리밋 | 미적용 | IP 기반 또는 사용자 기반 제한 |
| HTTPS | 미적용 (개발 환경) | 프로덕션: TLS 종료 (Nginx/Traefik) |
| 에이전트 신뢰 검증 | 미적용 | HMAC 서명 또는 mTLS |

---

## 14. 확장성 및 운영

### 14.1 새 에이전트 추가 방법

1. `maplestory-agent/` 구조를 복사
2. `agent_card.py`에서 이름, 설명, 포트 변경
3. `agent/planner.py`에서 도메인 전용 시스템 프롬프트 작성
4. `agent/tools/`에 전문 도구 추가
5. `main.py`에서 포트 설정
6. 서버 실행 후 오케스트레이터의 `/registry/agents`에 URL 등록

> 코드 변경 없이 런타임에 등록/해제 가능 (동적 레지스트리 설계)

### 14.2 새 MCP 서버 추가 방법

1. `fastmcp` 기반 서버 작성 (`server.py`)
2. `@mcp.tool()` 데코레이터로 도구 정의
3. `.env`에 `NEW_MCP_URL=http://127.0.0.1:81xx/sse` 추가
4. `backend/agent/tools/mcp_tools.py`의 `MCP_SERVER_URLS`에 URL 추가
5. 시스템 프롬프트에 새 도구 설명 추가

### 14.3 서비스별 실행 명령

```bash
# 데이터베이스 초기화
mariadb -u root -p < schema.sql

# MCP 서버들
cd tika-mcp-server    && python server.py &
cd weather-mcp-server && python server.py &
cd docgen-mcp-server  && python server.py &

# 서브 에이전트들
cd maplestory-agent    && python main.py &
cd suddenattack-agent  && python main.py &
cd fconline-agent      && python main.py &

# 오케스트레이터
cd backend && python main.py

# 프론트엔드 (개발)
cd frontend && npm install && npm run dev
```

---

## 15. 비기능 요구사항

### 15.1 성능

| 항목 | 목표 |
|------|------|
| 첫 토큰 응답 (TTFT) | < 2초 (LLM API 포함) |
| 서브 에이전트 위임 타임아웃 | 15초 |
| 에이전트 카드 조회 타임아웃 | 2초 |
| DB 커넥션 풀 | min 2, max 10 |
| LangGraph 최대 반복 | 10회 (GraphRecursionError 방지) |

### 15.2 가용성

| 항목 | 현황 |
|------|------|
| 에이전트 오프라인 폴백 | 캐시된 카드 사용, 오케스트레이터 계속 동작 |
| MCP 서버 장애 | 해당 도구 미제공으로 처리, 시스템 계속 동작 |
| DB 커넥션 오류 | 에러 응답 반환 (graceful degradation) |

### 15.3 관찰성

| 항목 | 도구 |
|------|------|
| LLM 호출 추적 | Langfuse (호출 횟수, 토큰 사용량, 레이턴시) |
| 에러 로깅 | 콘솔 로깅 (uvicorn access log + Python logging) |
| 에이전트 상태 | 프론트엔드 AgentPanel (10초 폴링) |

### 15.4 유지보수성

- **모듈화:** 각 에이전트/MCP 서버는 독립적으로 배포/업데이트 가능
- **동적 등록:** 코드 변경 없이 에이전트 추가/제거 가능
- **공유 모델:** `models.py`로 데이터 모델 중앙 관리
- **설정 분리:** 모든 민감 설정은 `.env`에 격리

---

*본 문서는 RAG Playground v1.0.0 기준으로 작성되었습니다.*
