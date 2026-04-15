def get_agent_card() -> dict:
    return {
        "name": "GPT A2A Agent",
        "description": "A2A 프로토콜 호환 에이전트. OpenAI GPT 모델을 사용하며 텍스트 스트리밍 응답을 지원합니다.",
        "url": "http://127.0.0.1:8000",
        "version": "1.0.0",
        "provider": {
            "organization": "OpenAI",
            "model": "gpt-5.4-mini",
        },
        "capabilities": {
            "streaming": True,
            "pushNotifications": False,
            "stateTransitionHistory": False,
        },
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text"],
        "skills": [
            {
                "id": "chat",
                "name": "General Chat",
                "description": "GPT-5.4-mini 기반 대화형 AI 어시스턴트. 질문 답변, 코드 작성, 개념 설명 등을 지원합니다.",
                "inputModes": ["text"],
                "outputModes": ["text"],
            }
        ],
    }
