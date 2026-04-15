from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agent import registry

router = APIRouter()


class AddAgentBody(BaseModel):
    url: str


@router.get("")
def list_agents():
    """등록된 모든 에이전트의 실시간 상태 목록을 반환합니다."""
    return registry.get_agents_with_status()


@router.post("")
def add_agent(body: AddAgentBody):
    """새 에이전트 URL을 레지스트리에 추가합니다."""
    url = body.url.strip().rstrip("/")
    if not url:
        raise HTTPException(status_code=400, detail="URL이 비어있습니다.")
    added = registry.add_node(url)
    if not added:
        raise HTTPException(status_code=409, detail="이미 등록된 에이전트입니다.")
    # 추가 후 해당 에이전트 상태 즉시 조회
    agents = registry.get_agents_with_status()
    added_agent = next((a for a in agents if a["url"] == url), None)
    return added_agent or {"url": url, "online": False, "card": None}


@router.delete("")
def remove_agent(body: AddAgentBody):
    """레지스트리에서 에이전트 URL을 제거합니다."""
    url = body.url.strip().rstrip("/")
    removed = registry.remove_node(url)
    if not removed:
        raise HTTPException(status_code=404, detail="등록되지 않은 에이전트입니다.")
    return JSONResponse(status_code=204, content=None)
