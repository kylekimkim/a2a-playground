from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agent_card import get_agent_card
from a2a_router import router as a2a_router
from rooms_router import router as rooms_router
from registry_router import router as registry_router
from upload_router import router as upload_router
from download_router import router as download_router
import database
from agent.tools.mcp_tools import init_mcp_client, close_mcp_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.init_db()
    await init_mcp_client()
    yield
    await close_mcp_client()
    await database.close_db()


app = FastAPI(title="GPT-5.4-mini A2A Agent", version="1.0.0", lifespan=lifespan)

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
app.include_router(rooms_router, prefix="/rooms")
app.include_router(registry_router, prefix="/registry/agents")
app.include_router(upload_router, prefix="/upload")
app.include_router(download_router, prefix="/download")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
