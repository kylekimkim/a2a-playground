# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A multi-service **A2A (Agent-to-Agent) orchestration playground**. A FastAPI orchestrator (port 8000) runs a LangGraph ReAct agent that streams responses over SSE and can delegate to domain-specialized sub-agents (ports 9000–9004) via the same A2A JSON-RPC protocol. MCP servers (ports 8100–8102) provide file-extraction, weather, and document-generation tools. A React/Vite frontend (port 5173) is the chat UI. MariaDB persists rooms and messages for the orchestrator only.

Full design is in `docs/architecture.md` and `docs/SDD.md` — consult those first for protocol details, sequence diagrams, and full API/tool tables.

## Running the system

Every service has its own process. The orchestrator's `lifespan` calls `init_mcp_client()`, so **MCP servers must be running before the backend starts**, otherwise their tools won't be loaded (the backend will still run, just without those tools).

```bash
# 1. Database
mariadb -u root -p < schema.sql           # creates `a2a_chat` DB (note: code uses DB_NAME from .env, default rag-playground)

# 2. MCP servers (run each in its own shell; SSE transport on 8100/8101/8102)
cd tika-mcp-server     && python server.py
cd weather-mcp-server  && python server.py
cd docgen-mcp-server   && python server.py

# 3. Sub-agents (each in its own shell)
cd maplestory-agent    && python main.py   # :9001
cd suddenattack-agent  && python main.py   # :9002
cd fconline-agent      && python main.py   # :9003
cd web-search-agent    && docker compose up -d && python main.py   # :9004  (SearXNG container on :8888 required)
cd fortuneteller-agent && python main.py   # :9000  (NOT in KNOWN_NODES — orchestrator won't see it unless POST /registry/agents)

# 4. Orchestrator
cd backend && python main.py               # :8000  (uvicorn --reload)

# 5. Frontend
cd frontend && npm install && npm run dev  # :5173
```

The `.env` lives at the **repo root** and is loaded by every Python service via `load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))`. There is one shared `.env`, not one per service.

## Tests

```bash
# Backend (pytest, asyncio_mode=auto — no @pytest.mark.asyncio needed)
cd backend && pytest                       # all tests
cd backend && pytest tests/test_task_handler.py::test_name   # single test

# Frontend (vitest + jsdom)
cd frontend && npm test                    # one-shot
cd frontend && npm run test:watch
```

There are no tests for sub-agents or MCP servers.

## Build / lint

- Frontend production build: `cd frontend && npm run build`
- No linter or formatter is configured for either Python or JS — don't add one unless asked.

## Architecture facts that aren't obvious from the file tree

**Orchestrator vs sub-agent asymmetry.** All five FastAPI services share the same skeleton (`main.py`, `a2a_router.py`, `task_handler.py`, `task_store.py`, `agent_card.py`, `models.py`, `agent/planner.py`). The orchestrator additionally has `rooms_router.py`, `room_store.py`, `database.py`, `registry_router.py`, `upload_router.py`, `download_router.py`, `agent/registry.py`, and `agent/tools/delegate.py`. Sub-agents are **stateless** — they ignore `session_id`, never touch a DB, and never re-delegate.

**Delegation protocol.** When the orchestrator's LLM calls `delegate_task(target_url, task_description)`, `agent/tools/delegate.py` POSTs an A2A JSON-RPC request to `target_url` (which is the sub-agent's `/chat` endpoint as advertised in its agent card), parses the SSE stream, concatenates every `artifact.parts[].text`, and returns the joined string back to the LLM as the tool result. No `session_id` is sent — sub-agents are single-turn.

**Dynamic agent prompt injection.** `agent/registry.py:KNOWN_NODES` hardcodes `9001/9002/9003/9004`. On **every** chat request, `get_available_agents_prompt_snippet()` polls each known node's `/.well-known/agent.json` (2 s timeout), caches the card, and injects the resulting agent list + skills into the system prompt. This is why `delegate_task` works without any code change when a new agent is added via `POST /registry/agents`. Fortuneteller (:9000) is intentionally not in `KNOWN_NODES` — register it at runtime to make it discoverable. Note: runtime additions are stored only in the orchestrator process and are lost on restart.

**MCP tools are loaded once at startup.** `agent/tools/mcp_tools.py:init_mcp_client()` connects to all three MCP servers over SSE via `MultiServerMCPClient` and caches the tool list. `planner.build_graph()` rebuilds the LangGraph per request but reuses the cached tools (`get_all_tools()` = local tools + cached MCP tools). To add a new MCP server, extend `MCP_SERVER_URLS` and the system prompt's `_MCP_TOOL_DESCRIPTIONS` map in `planner.py`.

**SSE on the frontend uses fetch + ReadableStream, not EventSource.** EventSource doesn't support POST, and the A2A protocol requires POST with a JSON-RPC body. See `frontend/src/api/a2aClient.js`. The Vite dev server proxies `/.well-known`, `/rooms`, `/chat`, `/upload`, `/download` → `localhost:8000`.

**Only `message/stream` is implemented.** `a2a_router.py` validates the body as JSON-RPC 2.0 + `TaskSendParams` and always streams via `task_handler.handle_tasks_send_subscribe`. There is no `tasks/get`, no `tasks/cancel`, no non-streaming variant. The router's `method` field is currently not even branched on.

**Two parallel "streamed" strings in `task_handler.py`.** `accumulated` (LLM tokens + injected download links) is what gets persisted to the DB as the agent message; `streamed` (additionally includes tool-call notices like `> 🔍 web_search ...`) is what the user sees over SSE. Don't conflate them when changing the streaming path.

**`create_document` tool result is post-processed.** When the LLM calls the `create_document` MCP tool, `task_handler` intercepts `on_tool_end`, parses the `/download/<filename>` path out of the tool output, and yields a Markdown download link as an extra artifact chunk so the frontend renders a button. Keep this in mind if you change the DocGen server's return format.

## Conventions

- **Default model is `gpt-5.4-mini`.** This is the literal string used in `.env`, `agent_card.py`, and `planner.DEFAULT_MODEL`. It is intentional — do **not** "correct" it to a real OpenAI model name unless explicitly asked.
- **All user-facing strings (prompts, tool notices, errors) are Korean.** Match that when editing them.
- Pydantic v2, Python 3.11+ syntax (`str | None`, `list[dict]`).
- Database timestamps are **Unix milliseconds (BIGINT)**, not DATETIME — see `_now_ms()` in `room_store.py`.
- The `output/` directory at the repo root is where DocGen MCP writes files; `/download/{filename}` serves from there.
- `backend/uploads/` is where the upload endpoint writes; file names are UUID-rewritten.
