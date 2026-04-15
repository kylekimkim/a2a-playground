def get_agent_card() -> dict:
    return {
        "name": "Sudden Attack Expert Agent",
        "description": "서든어택의 넥슨에서 제공하는 오픈 API를 이용해 유저 정보를 제공하며, 무기 추천, 전략, 맵 공략 등을 안내해주는 최고 전문가 에이전트입니다.",
        "url": "http://127.0.0.1:9002/chat",
        "version": "1.0.0",
        "provider": {
            "organization": "Nexon AI Mock",
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
                "id": "suddenattack_guide",
                "name": "Sudden Attack Guide",
                "description": "서든어택과 관련된 질문(무기 추천, 전략, 맵 공략 등)에 대해 전문적이고 친절한 답변을 제공합니다.",
                "inputModes": ["text"],
                "outputModes": ["text"],
            },
            {
                "id": "user_lookup",
                "name": "User Lookup",
                "description": "유저 이름으로 기본 정보, 계급, 티어, 최근 동향 등 유저 관련 상세 정보를 넥슨 오픈 API로 조회합니다.",
                "inputModes": ["text"],
                "outputModes": ["text"],
            },
        ],
    }
