# RAG Playground — TDD(Test Driven Development) 가이드

**문서 버전:** 1.0.0  
**작성일:** 2026-04-06

---

## 목차

1. [테스트 전략](#1-테스트-전략)
2. [백엔드 테스트 구성](#2-백엔드-테스트-구성)
3. [프론트엔드 테스트 구성](#3-프론트엔드-테스트-구성)
4. [테스트 파일 목록 및 범위](#4-테스트-파일-목록-및-범위)
5. [실행 방법](#5-실행-방법)
6. [TDD 사이클 적용 가이드](#6-tdd-사이클-적용-가이드)
7. [Mock 전략](#7-mock-전략)
8. [커버리지 목표](#8-커버리지-목표)

---

## 1. 테스트 전략

### 1.1 테스트 피라미드

```
          ▲
         /E2E\           소수 / 느림 / 비용 높음
        /──────\
       /통합 테스트\       중간 / 실제 FastAPI 앱
      /────────────\
     /  단위 테스트  \     다수 / 빠름 / mock 처리
    /────────────────\
```

| 계층 | 비율 | 도구 | 특징 |
|------|------|------|------|
| 단위 테스트 | ~70% | pytest, Vitest | 외부 의존성 mock, 빠른 피드백 |
| 통합 테스트 | ~25% | pytest + FastAPI TestClient | 실제 라우터/미들웨어 검증 |
| E2E 테스트 | ~5% | 수동 / Playwright (향후) | 전체 흐름 검증 |

### 1.2 TDD Red-Green-Refactor 원칙

```
1. RED    — 실패하는 테스트를 먼저 작성
2. GREEN  — 테스트를 통과시키는 최소한의 코드 작성
3. REFACTOR — 중복 제거, 코드 명확성 향상 (테스트는 계속 통과해야 함)
```

---

## 2. 백엔드 테스트 구성

### 2.1 디렉토리 구조

```
backend/
├── tests/
│   ├── conftest.py           공유 픽스처 및 경로 설정
│   ├── test_models.py        Pydantic 모델 검증
│   ├── test_calculator.py    계산기 도구 단위 테스트
│   ├── test_datetime_tool.py 날짜/시간 도구 단위 테스트
│   ├── test_web_search.py    웹 검색 도구 단위 테스트 (mock)
│   ├── test_task_store.py    인메모리 태스크 저장소 단위 테스트
│   ├── test_room_store.py    DB 연산 단위 테스트 (aiomysql mock)
│   ├── test_registry.py      에이전트 레지스트리 단위 테스트 (HTTP mock)
│   ├── test_delegate.py      에이전트 위임 도구 단위 테스트 (HTTP mock)
│   ├── test_task_handler.py  태스크 핸들러 내부 함수 단위 테스트
│   └── test_a2a_router.py    A2A 라우터 통합 테스트 (FastAPI TestClient)
└── pytest.ini
```

### 2.2 의존성 설치

```bash
cd backend
pip install pytest pytest-asyncio httpx
# (requirements.txt에 이미 있는 경우 생략 가능)
```

### 2.3 pytest.ini 설정

```ini
[pytest]
testpaths = tests
asyncio_mode = auto       # pytest-asyncio 비동기 자동 처리
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
```

---

## 3. 프론트엔드 테스트 구성

### 3.1 디렉토리 구조

```
frontend/
├── src/
│   └── __tests__/
│       ├── setup.js              @testing-library/jest-dom 초기화
│       ├── a2aClient.test.js     SSE 스트리밍 클라이언트 테스트
│       └── roomsClient.test.js   REST 클라이언트 테스트
├── vite.config.js                vitest 설정 포함
└── package.json                  vitest 의존성 포함
```

### 3.2 의존성 설치

```bash
cd frontend
npm install
# 또는 새로 추가된 devDependencies를 설치:
# vitest, jsdom, @testing-library/react, @testing-library/jest-dom, @testing-library/user-event
```

### 3.3 vite.config.js 테스트 설정

```javascript
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",    // 브라우저 DOM 에뮬레이션
    globals: true,           // describe, it, expect 전역 사용
    setupFiles: "./src/__tests__/setup.js",
  },
  // ...
});
```

---

## 4. 테스트 파일 목록 및 범위

### 4.1 백엔드

#### `test_models.py` — Pydantic 모델 단위 테스트

| 테스트 클래스 | 검증 항목 |
|-------------|---------|
| `TestTextPart` | 기본 타입 값, 잘못된 타입 거부 |
| `TestMessage` | user/agent 역할, 잘못된 역할 거부, 복수 파트 |
| `TestTaskStatus` | 5가지 유효 상태, 잘못된 상태 거부 |
| `TestArtifact` | 기본값(index=0, last_chunk=False), 필드 값 |
| `TestTask` | ID 자동 생성, 기본값 |
| `TestTaskSendParams` | 최소 유효 형식, session_id, metadata, 필수 필드 누락 |
| `TestJsonRpcRequest` | jsonrpc 버전, 필드 검증 |
| `TestJsonRpcResponse` | 성공/에러 응답, 직렬화 |
| `TestSseEvents` | SSE 이벤트 타입, final 플래그, dict 직렬화 |

#### `test_calculator.py` — 계산기 도구 단위 테스트

| 테스트 클래스 | 검증 항목 |
|-------------|---------|
| `TestEvalBasicArithmetic` | +, -, *, /, //, %, **, 단항 연산자, 중첩 표현식 |
| `TestEvalMathFunctions` | sqrt, sin, cos, log, log2, log10, exp, abs, round, ceil, floor, factorial, pi, e |
| `TestEvalSecurityGuards` | 문자열 상수 거부, 알 수 없는 변수 거부, 지수 오버플로우, 키워드 인수 거부 |
| `TestCalculatorTool` | 결과 포맷, ^ 별칭, 정수 표시, 0나눗셈 오류, 빈 입력 오류, 복합 표현식 |

#### `test_datetime_tool.py` — 날짜/시간 도구 단위 테스트

| 테스트 클래스 | 검증 항목 |
|-------------|---------|
| `TestGetDatetimeDefault` | 문자열 반환, 연도 포함, 시간 포함, 한국어 요일, 기본 타임존 레이블 |
| `TestGetDatetimeCustomTimezone` | UTC, New York, London, Tokyo |
| `TestGetDatetimeInvalidTimezone` | 알 수 없는 타임존 폴백 메시지, 빈 문자열 처리 |

#### `test_web_search.py` — 웹 검색 도구 단위 테스트 (DDGS mock)

| 테스트 클래스 | 검증 항목 |
|-------------|---------|
| `TestWebSearchSuccess` | 문자열 반환, 제목 포함, URL 포함, 번호 매기기, kr-kr 지역, max_results=4 |
| `TestWebSearchEmpty` | 결과 없음 메시지 |
| `TestWebSearchErrors` | 예외 처리, 패키지 미설치 안내 |

#### `test_task_store.py` — 인메모리 저장소 단위 테스트

| 테스트 클래스 | 검증 항목 |
|-------------|---------|
| `TestCreateTask` | ID 저장, submitted 초기 상태, 메시지 저장, session_id, 저장소 등록 |
| `TestGetTask` | 존재하는 태스크 반환, 없으면 None |
| `TestUpdateStatus` | working/completed/failed 전환, 순차 전환 |
| `TestAppendMessage` | 에이전트 메시지 추가, 복수 추가 |
| `TestAllTasks` | 모든 태스크 반환, 빈 저장소, 테스트 격리 |

#### `test_room_store.py` — DB 연산 테스트 (aiomysql mock)

| 테스트 클래스 | 검증 항목 |
|-------------|---------|
| `TestCreateRoom` | dict 반환, 기본 제목, 커스텀 제목, 커스텀 ID, INSERT 쿼리 |
| `TestListRooms` | 목록 반환, ORDER BY updated_at DESC |
| `TestSaveMessage` | dict 반환, 2개 쿼리 실행, INSERT + UPDATE |
| `TestGetMessages` | 메시지 반환, ORDER BY created_at ASC |
| `TestDeleteRoom` | 삭제 성공 True, 없으면 False, DELETE 쿼리 |
| `TestUpdateRoomTitle` | UPDATE 쿼리, 제목 값 전달 |

#### `test_registry.py` — 에이전트 레지스트리 테스트 (requests mock)

| 테스트 클래스 | 검증 항목 |
|-------------|---------|
| `TestAddNode` | URL 추가, 중복 거부, 슬래시 정규화 |
| `TestRemoveNode` | URL 제거, 없으면 False, 캐시 정리, 슬래시 정규화 |
| `TestGetAgentsWithStatus` | 온라인 카드 반환, 오프라인 캐시 폴백, 503 처리 |
| `TestGetAvailableAgentsPromptSnippet` | 빈 캐시, 에이전트 정보 포함, 스킬 포함 |
| `TestGetAgentName` | 캐시에서 이름 반환, 미등록 URL 기본값 |

#### `test_delegate.py` — 에이전트 위임 도구 테스트 (requests mock)

| 테스트 클래스 | 검증 항목 |
|-------------|---------|
| `TestDelegateTaskSuccess` | 텍스트 청크 누적, 전체 텍스트 반환, 비아티팩트 이벤트 무시, JSON-RPC 페이로드, 15초 타임아웃, stream=True |
| `TestDelegateTaskEmpty` | 빈 응답 안내 메시지 |
| `TestDelegateTaskErrors` | Timeout 에러 메시지, ConnectionError 메시지, 잘못된 JSON 처리 |

#### `test_task_handler.py` — 태스크 핸들러 내부 함수 테스트

| 테스트 클래스 | 검증 항목 |
|-------------|---------|
| `TestToolNotice` | 각 도구별 아이콘, 쿼리/수식/타임존 포함, MCP 도구 플러그 아이콘, blockquote 형식 |
| `TestToLcMessages` | user→HumanMessage, agent→AIMessage, 교대 메시지, 빈 목록, 긴 텍스트 |
| `TestUserText` | 단일 파트, 복수 파트 조인, 빈 파트 |
| `TestRegisterMcpToolNames` | 이름 등록, 누적 등록, 빈 목록 처리 |

#### `test_a2a_router.py` — A2A 라우터 통합 테스트

| 테스트 클래스 | 검증 항목 |
|-------------|---------|
| `TestJsonRpcParseErrors` | 빈 바디, 잘못된 JSON, 잘못된 버전, params 누락 |
| `TestValidStreamingRequest` | text/event-stream 헤더, no-cache 헤더, data: 라인, 유효한 JSON 이벤트, submitted/completed 이벤트, artifact 텍스트, session_id 전달 |
| `TestAgentCard` | /.well-known 200 반환, JSON 반환, 필수 필드 |

---

### 4.2 프론트엔드

#### `a2aClient.test.js` — SSE 클라이언트 테스트

| 테스트 그룹 | 검증 항목 |
|-----------|---------|
| 기본 동작 | POST /chat, Content-Type 헤더, JSON-RPC 페이로드, session_id, model metadata |
| 스트리밍 콜백 | onDelta 호출, onDone 호출, 스트림 종료 폴백 |
| 에러 처리 | error 이벤트, HTTP 500, AbortError 무시 |
| AbortController | 컨트롤러 반환, signal 전달 |
| SSE 파싱 | data: 아닌 라인 무시, 잘못된 JSON 무시, 빈 텍스트 무시 |

#### `roomsClient.test.js` — REST 클라이언트 테스트

| 테스트 그룹 | 검증 항목 |
|-----------|---------|
| `listRooms` | GET /rooms, 배열 반환 |
| `createRoom` | POST /rooms, 방 객체 반환 |
| `deleteRoom` | DELETE /rooms/{id}, 204→null, 404 throw |
| `getRoomMessages` | GET /rooms/{id}/messages, 메시지 배열 |
| `updateRoomTitle` | PATCH /rooms/{id}, body에 title, 500 throw |
| 공통 헤더 | Content-Type: application/json |

---

## 5. 실행 방법

### 5.1 백엔드 테스트 실행

```bash
cd backend

# 전체 테스트 실행
pytest

# 특정 파일만 실행
pytest tests/test_calculator.py

# 특정 클래스/함수만 실행
pytest tests/test_calculator.py::TestCalculatorTool
pytest tests/test_calculator.py::TestCalculatorTool::test_sqrt_result

# 커버리지 리포트 포함
pytest --cov=. --cov-report=term-missing

# 실패 시 즉시 중단
pytest -x

# 자세한 출력
pytest -v --tb=long
```

### 5.2 프론트엔드 테스트 실행

```bash
cd frontend

# 의존성 설치 (최초 1회)
npm install

# 전체 테스트 실행
npm test

# 워치 모드 (코드 변경 감지)
npm run test:watch

# 특정 파일만
npx vitest run src/__tests__/a2aClient.test.js

# 커버리지 리포트
npx vitest run --coverage
```

---

## 6. TDD 사이클 적용 가이드

### 6.1 새 기능 추가 시 TDD 순서

```
예시: 새 계산기 함수 'max(a, b)' 지원 추가

① RED — 실패 테스트 먼저 작성
   # test_calculator.py에 추가:
   def test_max_function(self):
       result = calculator.invoke({"expression": "max(3, 7)"})
       assert "7" in result

② pytest 실행 → 테스트 실패 확인 (RED)

③ GREEN — calculator.py의 _SAFE_NAMES에 max 추가:
   _SAFE_NAMES = {
       ...
       "max": max,   # 추가
   }

④ pytest 실행 → 테스트 통과 확인 (GREEN)

⑤ REFACTOR — 필요 시 코드 정리 (테스트는 여전히 통과해야 함)
```

### 6.2 버그 수정 시 TDD 순서

```
① 버그를 재현하는 실패 테스트 먼저 작성
② 테스트가 실패함을 확인 (RED)
③ 버그 수정 코드 작성
④ 테스트 통과 확인 (GREEN)
⑤ 회귀 방지: 해당 테스트를 영구 보관
```

### 6.3 새 서브 에이전트 추가 시

```
새 에이전트 도구를 추가할 때:
1. tests/test_{agent_name}_tools.py 파일 생성
2. 각 API 래퍼 도구에 대한 테스트 작성 (mock HTTP 응답 사용)
3. 정상 응답, 빈 응답, API 오류, 타임아웃 케이스 모두 커버
```

---

## 7. Mock 전략

### 7.1 백엔드 Mock 대상

| 대상 | Mock 방법 | 이유 |
|------|---------|------|
| `aiomysql` 커넥션 풀 | `unittest.mock.AsyncMock` | 실제 DB 없이 테스트 |
| `requests.get/post` | `unittest.mock.patch` | 외부 HTTP 차단 |
| `DDGS` (DuckDuckGo) | `unittest.mock.patch` | 실제 검색 API 차단 |
| LangGraph 에이전트 | `task_handler.handle_tasks_send_subscribe` mock | LLM 비용 방지 |
| MCP 클라이언트 초기화 | `AsyncMock` | 통합 테스트 시 서버 불필요 |

### 7.2 프론트엔드 Mock 대상

| 대상 | Mock 방법 | 이유 |
|------|---------|------|
| `fetch` API | `vi.stubGlobal("fetch", mockFn)` | 실제 HTTP 차단 |
| `ReadableStream` | 커스텀 스트림 생성 헬퍼 | SSE 응답 시뮬레이션 |
| `AbortController` | 브라우저 내장 (jsdom 제공) | 실제 구현 사용 |

### 7.3 실제로 실행되는 코드 (Mock 미사용)

| 대상 | 이유 |
|------|------|
| `_eval()` AST 계산 로직 | 순수 함수, 외부 의존성 없음 |
| `ZoneInfo` 타임존 처리 | OS 타임존 DB 사용, 빠름 |
| Pydantic 모델 검증 | 라이브러리 동작 검증 |
| task_store 인메모리 연산 | 외부 의존성 없음 |

---

## 8. 커버리지 목표

| 모듈 | 목표 커버리지 | 우선순위 |
|------|------------|---------|
| `agent/tools/calculator.py` | 95%+ | 높음 (보안 중요) |
| `agent/tools/datetime_tool.py` | 90%+ | 중간 |
| `agent/tools/web_search.py` | 85%+ | 중간 |
| `agent/tools/delegate.py` | 85%+ | 높음 (에러 경로 중요) |
| `agent/registry.py` | 85%+ | 높음 (가용성 중요) |
| `task_store.py` | 95%+ | 높음 |
| `room_store.py` | 80%+ | 높음 |
| `task_handler.py` | 75%+ | 중간 (LLM 호출 제외) |
| `a2a_router.py` | 80%+ | 높음 |
| `models.py` | 90%+ | 높음 |
| **전체 백엔드** | **80%+** | - |
| `src/api/a2aClient.js` | 90%+ | 높음 |
| `src/api/roomsClient.js` | 95%+ | 높음 |
| **전체 프론트엔드** | **75%+** | - |

---

*본 문서는 RAG Playground v1.0.0 기준으로 작성되었습니다.*
