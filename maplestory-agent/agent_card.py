def get_agent_card() -> dict:
    return {
        "name": "Maplestory Expert Agent",
        "description": "메이플스토리의 넥슨에서 제공하는 오픈 API를 이용해 실제 정보를 제공하며 또한,직업 추천, 보스 패턴, 아이템 세팅, 스토리 등을 안내해주는 최고 전문가 에이전트입니다.",
        "url": "http://127.0.0.1:9001/chat",
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
                "id": "maplestory_guide",
                "name": "Maplestory Guide",
                "description": "메이플스토리와 관련된 질문(직업 추천, 템셋팅, 보스 공략 등)에 대해 전문적이고 친절한 답변을 제공합니다.",
                "inputModes": ["text"],
                "outputModes": ["text"],
            },
            {
                "id": "character_lookup",
                "name": "Character Lookup",
                "description": "캐릭터 이름으로 기본 정보, 인기도, 능력치, 하이퍼스탯, 성향, 어빌리티, 장비, 캐시 장비, 세트 효과, 헤어/성형/피부, 펫, 무릉도장 기록 등 캐릭터 관련 상세 정보를 넥슨 오픈 API로 조회합니다.",
                "inputModes": ["text"],
                "outputModes": ["text"],
            },
        ],
    }
