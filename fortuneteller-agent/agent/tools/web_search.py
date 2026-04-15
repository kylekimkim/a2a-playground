from langchain.tools import tool


@tool
def web_search(query: str) -> str:
    """인터넷에서 최신 정보를 검색합니다.
    최신 뉴스, 실시간 데이터, 사실 확인, 현재 이벤트 조회에 사용합니다.
    예: '2024년 AI 최신 동향', '오늘 날씨 서울', '파이썬 최신 버전'
    """
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=4, region="kr-kr"))

        if not results:
            return f"'{query}'에 대한 검색 결과를 찾을 수 없습니다."

        output_parts = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "제목 없음")
            body = r.get("body", "")
            href = r.get("href", "")
            output_parts.append(f"[{i}] {title}\n{body}\n출처: {href}")

        print("## web_search 툴 결과: ")
        print("\n\n".join(output_parts))
        return "\n\n".join(output_parts)
    except ImportError:
        return "오류: 'duckduckgo-search' 패키지가 설치되지 않았습니다. pip install duckduckgo-search"
    except Exception as e:
        print(f"검색 오류: {e}")
        return f"검색 오류: {e}"
