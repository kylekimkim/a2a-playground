def get_agent_card() -> dict:
    return {
        "name": "Fortune Teller Agent",
        "description": "운세와 점성술에 특화된 신비로운 점술가 에이전트. GPT-5.4-mini를 활용해 심도 깊은 운세를 알려줍니다.",
        "url": "http://127.0.0.1:9000/chat",
        "version": "1.0.0",
        "provider": {
            "organization": "Mystic AI",
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
                "id": "horoscope",
                "name": "Daily Horoscope",
                "description": "별자리, 사주, 타로 등의 지식을 활용하여 흥미롭고 위트있는 오늘의 운세와 조언을 제공합니다.",
                "inputModes": ["text"],
                "outputModes": ["text"],
            }
        ],
    }
