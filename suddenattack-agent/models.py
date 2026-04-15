from __future__ import annotations
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field
import uuid


# ── A2A Core Types ──────────────────────────────────────────────────────────

class TextPart(BaseModel):
    type: Literal["text"] = "text"
    text: str


class Message(BaseModel):
    role: Literal["user", "agent"]
    parts: list[TextPart]


class TaskStatus(BaseModel):
    state: Literal["submitted", "working", "completed", "failed", "canceled"]
    message: Optional[Message] = None


class Artifact(BaseModel):
    index: int = 0
    parts: list[TextPart] = Field(default_factory=list)
    last_chunk: bool = False


class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: Optional[str] = None
    status: TaskStatus
    messages: list[Message] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    metadata: Optional[dict[str, Any]] = None


# ── A2A RPC Params ──────────────────────────────────────────────────────────

class TaskSendParams(BaseModel):
    id: Optional[str] = None
    session_id: Optional[str] = None
    message: Message
    metadata: Optional[dict[str, Any]] = None


class TaskGetParams(BaseModel):
    id: str


# ── JSON-RPC 2.0 ────────────────────────────────────────────────────────────

class JsonRpcRequest(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: Optional[str | int] = None
    method: str
    params: Optional[dict[str, Any]] = None


class JsonRpcError(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None


class JsonRpcResponse(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: Optional[str | int] = None
    result: Optional[Any] = None
    error: Optional[JsonRpcError] = None


# ── SSE Event Types ──────────────────────────────────────────────────────────

class TaskStatusUpdateEvent(BaseModel):
    type: Literal["task_status_update"] = "task_status_update"
    task_id: str
    status: TaskStatus
    final: bool = False


class TaskArtifactUpdateEvent(BaseModel):
    type: Literal["task_artifact_update"] = "task_artifact_update"
    task_id: str
    artifact: Artifact
