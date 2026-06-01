from langchain_core.tools import tool
import logging
import os
import requests
import httpx
import json
import uuid
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

# delegate_task의 timeout (sub-agent의 ReAct 루프가 끝날 때까지 기다려야 함).
# requests의 timeout=(connect, read)에서 read는 청크 사이 idle 허용 시간이라,
# LLM/Crawl4AI 호출 한 단계가 끝날 때까지 충분히 길어야 한다.
_DELEGATE_CONNECT_TIMEOUT = float(os.getenv("DELEGATE_TIMEOUT_CONNECT", "10"))
_DELEGATE_READ_TIMEOUT = float(os.getenv("DELEGATE_TIMEOUT_READ", "180"))

@tool
def delegate_task(target_url: str, task_description: str) -> str:
    """
    다른 A2A (Agent-to-Agent) 오케스트레이터나 특화된 에이전트에게 작업을 위임합니다.
    target_url: (예: "http://localhost:9000") 위임할 에이전트의 서버 URL
    task_description: (예: "내 오늘의 운세를 확인해줘") 넘겨줄 작업에 대한 상세 텍스트 요청사항
    
    이 도구를 호출하면 백그라운드에서 대상 에이전트와 통신하여 대신 작업을 수행하고 그 결과를 반환받습니다.
    """

    try:
        # A2A JSON-RPC 규격에 맞게 요청 페이로드 구성
        req_id = str(uuid.uuid4())
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "message/stream",
            "params": {
                "id": req_id,
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": task_description}]
                }
            }
        }
        
        print("delegate_task called")
        print(payload)
        # 에이전트 카드의 url을 그대로 사용 (chat 엔드포인트 포함)
        response = requests.post(
            target_url,
            json=payload,
            stream=True,
            timeout=(_DELEGATE_CONNECT_TIMEOUT, _DELEGATE_READ_TIMEOUT),
        )
        response.raise_for_status()
        
        accumulated_text = ""
        
        # SSE 라인 수신 및 파싱
        for line in response.iter_lines():
            if line:
                decoded = line.decode('utf-8').strip()
                if decoded.startswith("data:"):
                    data_str = decoded[5:].strip()
                    if not data_str:
                        continue
                    try:
                        event = json.loads(data_str)
                        if "artifact" in event:
                            parts = event["artifact"].get("parts", [])
                            for p in parts:
                                if "text" in p:
                                    accumulated_text += p["text"]
                    except json.JSONDecodeError:
                        print(f"[DELEGATE SSE RAW] {data_str}")
                        
        if not accumulated_text.strip():
            return "대상 에이전트가 올바르게 실행되었으나 빈 텍스트를 반환했습니다."

        return accumulated_text
    except requests.exceptions.ConnectTimeout:
        return f"에이전트 위임 실패: {target_url} 연결 타임아웃({_DELEGATE_CONNECT_TIMEOUT}s) — 대상 에이전트가 실행 중인지 확인하세요."
    except requests.exceptions.ReadTimeout:
        return (
            f"에이전트 위임 실패: {target_url} 응답 대기 타임아웃({_DELEGATE_READ_TIMEOUT}s). "
            f"필요 시 환경변수 DELEGATE_TIMEOUT_READ를 더 크게 설정하세요."
        )
    except requests.exceptions.Timeout:
        return f"에이전트 위임 실패: {target_url} 타임아웃"
    except Exception as e:
        return f"에이전트 위임 실패: {str(e)}"


async def stream_delegate(
    target_url: str,
    task_description: str,
) -> AsyncGenerator[str, None]:
    """passthrough 에이전트의 SSE artifact를 청크 단위로 yield합니다.

    오케스트레이터 LLM을 거치지 않고 청크가 도착하는 즉시 사용자에게 forward하기
    위한 진짜 stream-through용 헬퍼. 일반 delegate_task와 달리 LangChain @tool이
    아니라 task_handler가 직접 호출합니다.
    """
    req_id = str(uuid.uuid4())
    payload = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": "message/stream",
        "params": {
            "id": req_id,
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": task_description}],
            },
        },
    }
    timeout = httpx.Timeout(
        connect=_DELEGATE_CONNECT_TIMEOUT,
        read=_DELEGATE_READ_TIMEOUT,
        write=_DELEGATE_CONNECT_TIMEOUT,
        pool=_DELEGATE_CONNECT_TIMEOUT,
    )
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", target_url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if not data_str:
                        continue
                    try:
                        event = json.loads(data_str)
                    except json.JSONDecodeError:
                        logger.debug("[STREAM_DELEGATE RAW] %s", data_str)
                        continue
                    artifact = event.get("artifact")
                    if not artifact:
                        continue
                    for p in artifact.get("parts", []):
                        text = p.get("text")
                        if text:
                            yield text
    except httpx.ConnectTimeout:
        yield f"\n\n[stream-through 실패: {target_url} 연결 타임아웃]"
    except httpx.ReadTimeout:
        yield f"\n\n[stream-through 실패: {target_url} 응답 대기 타임아웃 — DELEGATE_TIMEOUT_READ 상향 검토]"
    except httpx.HTTPStatusError as e:
        yield f"\n\n[stream-through 실패: HTTP {e.response.status_code}]"
    except Exception as e:
        logger.exception("stream_delegate 예외")
        yield f"\n\n[stream-through 실패: {e}]"
