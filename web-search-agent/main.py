# ── Windows asyncio 이벤트 루프 정책 ─────────────────────────────────────
# Playwright(Crawl4AI 내부)는 자식 프로세스(Chromium)를 띄우기 위해
# asyncio.create_subprocess_exec 를 사용한다. Windows에서 SelectorEventLoop
# 위에 있으면 subprocess가 NotImplementedError 로 실패하므로 ProactorEventLoop
# 정책을 명시한다. (uvicorn import 전에 설정해야 한다)
import sys
import asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from dotenv import load_dotenv
import os

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agent_card import get_agent_card
from a2a_router import router as a2a_router

app = FastAPI(title="Web Search ReAct A2A Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/.well-known/agent.json")
def agent_card():
    return JSONResponse(get_agent_card())


app.include_router(a2a_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=9004, reload=True)
