def get_agent_card() -> dict:
    return {
        "name": "Web Search ReAct Agent",
        "description": "SearXNG + Crawl4AI 기반 웹검색 전용 에이전트. LangGraph ReAct 패턴으로 검색 → 본문 추출 → 압축 → 자기 검증(reflection) → 재검색을 수행한 뒤, 근거(URL)와 함께 최종 답변을 생성합니다.",
        "url": "http://127.0.0.1:9004/chat",
        "version": "1.0.0",
        "provider": {
            "organization": "sjkim",
            "model": "gpt-5.4-mini",
        },
        "capabilities": {
            "streaming": True,
            "pushNotifications": False,
            "stateTransitionHistory": False,
            # ★ 오케스트레이터가 이 플래그를 보고 LLM 2차 합성을 건너뛰고
            #   본 에이전트의 SSE 청크를 사용자에게 그대로 forward(stream-through)합니다.
            "passthrough": True,
        },
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text"],
        "skills": [
            {
                "id": "agentic_web_search",
                "name": "Agentic Web Search",
                "description": "최신 정보가 필요한 질문에 대해 다단계 웹 검색·크롤링·자기검증을 통해 근거 기반 답변을 생성합니다.",
                "inputModes": ["text"],
                "outputModes": ["text"],
            },
            {
                "id": "url_deep_read",
                "name": "URL Deep Read",
                "description": "특정 URL(뉴스/문서)의 본문을 Crawl4AI로 추출하고 요점을 정리합니다.",
                "inputModes": ["text"],
                "outputModes": ["text"],
            },
        ],
    }
