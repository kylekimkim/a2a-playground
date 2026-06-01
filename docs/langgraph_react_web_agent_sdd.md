# LangGraph ReAct 기반 웹검색 에이전트 SDD
## System Design Document (SDD)

작성일: 2026-05-18

---

# 1. 시스템 개요

본 시스템은 LangGraph 기반 ReAct(Reason + Act) 패턴을 사용하는 웹검색 특화 AI 에이전트이다.

시스템은 다음 요소들을 기반으로 구성된다.

- LLM: OpenAI API
- Agent Framework: LangGraph
- 검색엔진: SearXNG
- 크롤링: Crawl4AI
- 벡터DB: OpenSearch
- 임베딩: OpenAI Embedding 또는 BGE-M3
- Retrieval: Hybrid Search (BM25 + Vector)
- Rerank: Cross Encoder 기반
- 응답 생성: ReAct Agent 기반 Multi-Step Reasoning

본 구조의 핵심 목표는 다음과 같다.

1. 최신 웹 정보 기반 응답 생성
2. 검색 결과의 정밀한 압축 및 재검색
3. Agentic Retrieval 구현
4. 토큰 비용 최적화
5. 긴 문서 기반 근거 중심 답변 생성

---

# 2. 전체 아키텍처

```text
[ User ]
    ↓
[ API Gateway ]
    ↓
[ LangGraph Agent ]
    ├── Query Planner
    ├── ReAct Reasoner
    ├── Tool Router
    ├── Reflection Node
    └── Final Synthesizer
            ↓
 ┌────────────────────────────┐
 │ Tool Layer                 │
 ├────────────────────────────┤
 │ 1. SearXNG Search Tool     │
 │ 2. Crawl4AI Fetch Tool     │
 │ 3. OpenSearch Retrieval    │
 │ 4. Reranker Tool           │
 │ 5. Compression Tool        │
 └────────────────────────────┘
            ↓
[ OpenSearch Vector Index ]
            ↓
[ Final Answer + Citations ]
```

---

# 3. 핵심 설계 철학

## 3.1 단순 검색이 아닌 Agentic Retrieval

기존 RAG:
- 검색 → 답변

본 구조:
- 검색
- 분석
- 추가 검색
- 재검증
- 압축
- 근거 통합
- 최종 생성

즉 AI가 검색 전략을 스스로 수행한다.

---

# 4. 기술 스택

| 구성 요소 | 기술 |
|---|---|
| Agent Framework | LangGraph |
| LLM | OpenAI GPT-4.1 / GPT-4o |
| Embedding | text-embedding-3-large 또는 BGE-M3 |
| Search Engine | SearXNG |
| Vector DB | OpenSearch |
| Crawl Engine | Crawl4AI |
| Backend | FastAPI |
| Queue | RabbitMQ (선택) |
| Cache | Redis |
| Observability | LangSmith / OpenTelemetry |
| Deployment | Docker + Kubernetes |

---

# 5. LangGraph 설계

## 5.1 Graph Flow

```text
START
 ↓
Planner Node
 ↓
Search Decision
 ├── Web Search
 ├── Vector Retrieval
 └── Direct Response
 ↓
Crawler Node
 ↓
Chunking Node
 ↓
Retrieval Node
 ↓
Rerank Node
 ↓
Compression Node
 ↓
Reflection Node
 ├── Need More Search?
 │        ├── YES → Search Loop
 │        └── NO
 ↓
Final Synthesizer
 ↓
END
```

---

# 6. ReAct 패턴 설계

## 6.1 구조

```text
Thought:
사용자 질문 분석

Action:
search_web("로켓랩 최근 NASA 계약")

Observation:
검색 결과 수집

Thought:
계약 규모 정보 부족

Action:
crawl_url(url)

Observation:
본문 확보

Thought:
추가 검증 필요

Action:
search_web("Rocket Lab NASA contract amount")

Observation:
정보 보강 완료

Final Answer:
최종 응답 생성
```

---

# 7. 노드 상세 설계

# 7.1 Planner Node

역할:
- 사용자 질문 분석
- 검색 필요 여부 판단
- 툴 사용 전략 결정

입력:
- User Query

출력:
- Search Plan
- Retrieval Strategy
- Search Keywords

예시:

```json
{
  "need_web_search": true,
  "need_vector_search": true,
  "search_queries": [
    "Rocket Lab NASA contract 2026",
    "Rocket Lab launch agreement"
  ]
}
```

---

# 7.2 SearXNG Search Node

역할:
- 웹 검색 수행
- 결과 URL 수집

API 예시:

```http
GET /search?q=rocket+lab+nasa&format=json
```

반환:

```json
[
  {
    "title": "...",
    "url": "...",
    "content": "..."
  }
]
```

최적화:
- domain whitelist
- trusted source filtering
- duplicate 제거

---

# 7.3 Crawl4AI Node

역할:
- URL 본문 추출
- Markdown 변환

예시:

```python
from crawl4ai import AsyncWebCrawler

async with AsyncWebCrawler() as crawler:
    result = await crawler.arun(url=url)

markdown = result.markdown
```

출력 예시:

```markdown
# Rocket Lab signs NASA deal

Rocket Lab announced...
```

---

# 7.4 Chunking Node

전략:
- Semantic Chunking
- Recursive Splitter
- Markdown Header 기반 분할

권장 설정:

| 항목 | 값 |
|---|---|
| Chunk Size | 500~1000 |
| Chunk Overlap | 100~150 |
| Split 기준 | Header + Paragraph |

---

# 7.5 Embedding Node

선택지:

## OpenAI

- text-embedding-3-large
- text-embedding-3-small

## 로컬

- BGE-M3
- e5-large
- multilingual-e5

추천:
- BGE-M3 (Hybrid 강점)

---

# 7.6 OpenSearch 인덱스 설계

## Mapping 예시

```json
{
  "mappings": {
    "properties": {
      "content": {
        "type": "text"
      },
      "vector": {
        "type": "knn_vector",
        "dimension": 1024
      },
      "url": {
        "type": "keyword"
      },
      "title": {
        "type": "text"
      },
      "timestamp": {
        "type": "date"
      }
    }
  }
}
```

---

# 7.7 Retrieval Node

## Hybrid Search

구성:
- BM25
- Vector Similarity

예시:

```json
{
  "query": {
    "hybrid": {
      "queries": [
        {
          "match": {
            "content": "Rocket Lab NASA"
          }
        },
        {
          "knn": {
            "vector": {
              "vector": [0.12, 0.88],
              "k": 10
            }
          }
        }
      ]
    }
  }
}
```

---

# 7.8 Rerank Node

목적:
- relevance 향상
- context 최소화

추천 모델:
- BGE Reranker
- Cohere Rerank
- Cross Encoder MS-MARCO

전략:
- Top 20 → Top 5 축소

---

# 7.9 Compression Node

역할:
- 긴 context 압축
- 핵심 정보만 유지

예시:

원문:
- 4000 tokens

압축 후:
- 300 tokens

전략:
- Map Reduce Summary
- Contextual Compression
- Citation 유지

---

# 7.10 Reflection Node

핵심 기능:
- 정보 부족 판단
- 추가 검색 여부 결정

예시:

```text
현재 확보된 정보만으로는 계약 규모 검증 부족
추가 검색 수행
```

---

# 8. OpenAI API 전략

## 8.1 모델 역할 분리

| 역할 | 모델 |
|---|---|
| Planner | GPT-4o-mini |
| Retrieval 판단 | GPT-4o-mini |
| Compression | GPT-4o-mini |
| 최종 응답 | GPT-4.1 |

---

# 9. 토큰 최적화 전략

## 핵심 전략

1. HTML 제거
2. Markdown 기반 정제
3. Chunk Retrieval
4. Top-K 제한
5. Rerank 적용
6. Compression 적용

목표:
- 최종 context 5k tokens 이하 유지

---

# 10. 캐싱 전략

## Redis 캐시

대상:
- 검색 결과
- 크롤링 결과
- 임베딩 결과
- 압축 결과

TTL:
- 뉴스: 1시간
- 일반 문서: 24시간

---

# 11. 비동기 처리 구조

권장:
- asyncio 기반
- Crawl 병렬화
- Search 병렬화

예시:

```python
results = await asyncio.gather(*tasks)
```

---

# 12. 장애 대응 전략

| 문제 | 대응 |
|---|---|
| 검색 실패 | fallback query |
| 크롤링 실패 | retry |
| 토큰 초과 | compression |
| hallucination | citation validation |
| timeout | partial response |

---

# 13. 보안 고려사항

- URL Allow/Deny 정책
- SSRF 차단
- Private IP 차단
- robots.txt 고려
- Prompt Injection 방어

---

# 14. Prompt Injection 방어

필수 적용 사항:

1. HTML Script 제거
2. Ignore Previous Instruction 패턴 제거
3. 시스템 프롬프트 격리
4. Tool Output Sanitization

예시 차단 문구:

```text
Ignore previous instructions
System prompt reveal
Execute arbitrary code
```

---

# 15. 관측성(Observability)

추천 구성:
- LangSmith
- OpenTelemetry
- Grafana
- Prometheus

추적 대상:
- 검색 횟수
- Tool 호출
- Token 사용량
- Latency
- 실패율

---

# 16. API 설계 예시

## Query API

```http
POST /agent/query
```

요청:

```json
{
  "query": "로켓랩 최근 NASA 계약 분석"
}
```

응답:

```json
{
  "answer": "...",
  "citations": [
    {
      "title": "...",
      "url": "..."
    }
  ]
}
```

---

# 17. 추천 디렉토리 구조

```text
project/
 ├── app/
 │    ├── agents/
 │    ├── graph/
 │    ├── tools/
 │    ├── retrievers/
 │    ├── prompts/
 │    ├── embeddings/
 │    ├── rerank/
 │    ├── compression/
 │    └── api/
 │
 ├── infra/
 │    ├── docker/
 │    ├── kubernetes/
 │    └── monitoring/
 │
 ├── tests/
 └── docs/
```

---

# 18. 향후 확장 방향

## 향후 추가 가능 기능

- Multi-Agent
- Deep Research Mode
- Browser Automation
- PDF Parsing
- YouTube Retrieval
- Long-term Memory
- Knowledge Graph
- MCP Tool Integration

---

# 19. 권장 운영 구조

## 소규모

- 단일 FastAPI
- 단일 OpenSearch

## 중대형

- Kubernetes
- RabbitMQ
- Separate Retrieval Worker
- Separate Crawl Worker

---

# 20. 최종 권장 아키텍처

```text
User
 ↓
FastAPI
 ↓
LangGraph Agent
 ↓
SearXNG
 ↓
Crawl4AI
 ↓
Chunking
 ↓
Embedding
 ↓
OpenSearch
 ↓
Rerank
 ↓
Compression
 ↓
Reflection
 ↓
Final GPT-4.1 Response
```

---

# 21. 결론

본 구조는 단순 RAG 시스템이 아닌:

- Agentic Retrieval
- ReAct 기반 추론
- Multi-Step Search
- Reflection Loop
- Hybrid Retrieval
- Context Compression

을 모두 포함한 차세대 웹검색 AI 에이전트 구조이다.

특히:
- SearXNG
- Crawl4AI
- OpenSearch
- LangGraph

조합은 오픈소스 기반으로 매우 강력한 구조를 만들 수 있으며,
FlowAI 같은 워크플로우 시스템과도 높은 궁합을 가진다.
