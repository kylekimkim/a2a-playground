import json
import logging
import traceback
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

logger = logging.getLogger(__name__)

import task_handler
import task_store
from models import (
    JsonRpcRequest,
    JsonRpcResponse,
    JsonRpcError,
    TaskSendParams,
    TaskGetParams,
)

router = APIRouter()

ERROR_PARSE = JsonRpcError(code=-32700, message="Parse error")
ERROR_METHOD = JsonRpcError(code=-32601, message="Method not found")
ERROR_PARAMS = JsonRpcError(code=-32602, message="Invalid params")
ERROR_INTERNAL = JsonRpcError(code=-32603, message="Internal error")


def _ok(req_id, result) -> JSONResponse:
    return JSONResponse(
        JsonRpcResponse(id=req_id, result=result).model_dump(mode="json")
    )


def _err(req_id, error: JsonRpcError) -> JSONResponse:
    return JSONResponse(
        JsonRpcResponse(id=req_id, error=error).model_dump(mode="json"),
        status_code=200,
    )


@router.post("/chat")
async def jsonrpc_endpoint(request: Request):
    try:
        body = await request.json()
        rpc = JsonRpcRequest.model_validate(body)
    except Exception as e:
        print(f"[PARSE ERROR] {e}")
        return _err(None, ERROR_PARSE)

    req_id = rpc.id
    params_raw = rpc.params or {}

    try:
        params = TaskSendParams.model_validate(params_raw)
    except Exception:
        return _err(req_id, ERROR_PARAMS)

    async def event_generator():
        try:
            async for event in task_handler.handle_tasks_send_subscribe(params):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.error("Streaming error: %s\n%s", e, traceback.format_exc())
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
