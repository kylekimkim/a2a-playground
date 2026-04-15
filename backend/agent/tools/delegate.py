from langchain_core.tools import tool
import requests
import json
import uuid

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
            timeout=15
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
    except requests.exceptions.Timeout:
        return f"에이전트 위임 실패: {target_url} 응답 대기 시간 초과"
    except Exception as e:
        return f"에이전트 위임 실패: {str(e)}"
