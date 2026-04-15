"""
TDD: agent registry 단위 테스트 (HTTP 요청 mock 처리)
"""
import pytest
from unittest.mock import patch, MagicMock
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import agent.registry as registry


@pytest.fixture(autouse=True)
def reset_registry():
    """각 테스트 전후 레지스트리 상태 초기화"""
    original_nodes = registry.KNOWN_NODES.copy()
    registry._AGENT_CACHE.clear()
    yield
    registry.KNOWN_NODES.clear()
    registry.KNOWN_NODES.extend(original_nodes)
    registry._AGENT_CACHE.clear()


MOCK_CARD = {
    "name": "테스트 에이전트",
    "description": "테스트용 에이전트",
    "url": "http://127.0.0.1:9099/chat",
    "version": "1.0.0",
    "skills": [
        {"id": "skill1", "name": "스킬1", "description": "테스트 스킬"}
    ],
}


class TestAddNode:
    def test_adds_new_url(self):
        result = registry.add_node("http://127.0.0.1:9099")
        assert result is True
        assert "http://127.0.0.1:9099" in registry.KNOWN_NODES

    def test_duplicate_url_returns_false(self):
        registry.add_node("http://127.0.0.1:9099")
        result = registry.add_node("http://127.0.0.1:9099")
        assert result is False

    def test_trailing_slash_normalized(self):
        registry.add_node("http://127.0.0.1:9099/")
        assert "http://127.0.0.1:9099" in registry.KNOWN_NODES

    def test_duplicate_with_slash_variant_returns_false(self):
        registry.add_node("http://127.0.0.1:9099")
        result = registry.add_node("http://127.0.0.1:9099/")
        assert result is False


class TestRemoveNode:
    def test_removes_existing_url(self):
        registry.add_node("http://127.0.0.1:9098")
        result = registry.remove_node("http://127.0.0.1:9098")
        assert result is True
        assert "http://127.0.0.1:9098" not in registry.KNOWN_NODES

    def test_remove_nonexistent_returns_false(self):
        result = registry.remove_node("http://127.0.0.1:9000")
        assert result is False

    def test_remove_also_clears_cache(self):
        url = "http://127.0.0.1:9097/chat"
        registry._AGENT_CACHE[url] = MOCK_CARD
        registry.add_node("http://127.0.0.1:9097")
        registry.remove_node("http://127.0.0.1:9097")
        assert url not in registry._AGENT_CACHE

    def test_trailing_slash_normalized_on_remove(self):
        registry.add_node("http://127.0.0.1:9096")
        result = registry.remove_node("http://127.0.0.1:9096/")
        assert result is True


class TestGetAgentsWithStatus:
    def test_online_agent_returns_card(self):
        registry.KNOWN_NODES.clear()
        registry.add_node("http://127.0.0.1:9099")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_CARD

        with patch("agent.registry.requests.get", return_value=mock_resp):
            agents = registry.get_agents_with_status()

        assert len(agents) == 1
        assert agents[0]["online"] is True
        assert agents[0]["card"]["name"] == "테스트 에이전트"

    def test_offline_agent_returns_cached_card(self):
        registry.KNOWN_NODES.clear()
        registry.add_node("http://127.0.0.1:9099")
        registry._AGENT_CACHE["http://127.0.0.1:9099/chat"] = MOCK_CARD

        with patch("agent.registry.requests.get", side_effect=Exception("Connection refused")):
            agents = registry.get_agents_with_status()

        assert agents[0]["online"] is False
        assert agents[0]["card"] == MOCK_CARD

    def test_offline_agent_no_cache_returns_none_card(self):
        registry.KNOWN_NODES.clear()
        registry.add_node("http://127.0.0.1:9099")

        with patch("agent.registry.requests.get", side_effect=Exception("Connection refused")):
            agents = registry.get_agents_with_status()

        assert agents[0]["online"] is False
        assert agents[0]["card"] is None

    def test_non_200_response_treated_as_offline(self):
        registry.KNOWN_NODES.clear()
        registry.add_node("http://127.0.0.1:9099")

        mock_resp = MagicMock()
        mock_resp.status_code = 503

        with patch("agent.registry.requests.get", return_value=mock_resp):
            agents = registry.get_agents_with_status()

        assert agents[0]["online"] is False


class TestGetAvailableAgentsPromptSnippet:
    def test_returns_empty_string_when_no_agents(self):
        with patch("agent.registry.fetch_agent_cards"):
            registry._AGENT_CACHE.clear()
            snippet = registry.get_available_agents_prompt_snippet()
        assert snippet == ""

    def test_returns_snippet_with_agent_info(self):
        with patch("agent.registry.fetch_agent_cards"):
            registry._AGENT_CACHE["http://127.0.0.1:9099/chat"] = MOCK_CARD
            snippet = registry.get_available_agents_prompt_snippet()

        assert "테스트 에이전트" in snippet
        assert "http://127.0.0.1:9099/chat" in snippet
        assert "delegate_task" in snippet

    def test_snippet_contains_skills(self):
        with patch("agent.registry.fetch_agent_cards"):
            registry._AGENT_CACHE["http://127.0.0.1:9099/chat"] = MOCK_CARD
            snippet = registry.get_available_agents_prompt_snippet()

        assert "스킬1" in snippet


class TestGetAgentName:
    def test_returns_cached_name(self):
        registry._AGENT_CACHE["http://127.0.0.1:9099/chat"] = MOCK_CARD
        name = registry.get_agent_name("http://127.0.0.1:9099/chat")
        assert name == "테스트 에이전트"

    def test_returns_default_for_unknown_url(self):
        name = registry.get_agent_name("http://unknown.url/chat")
        assert name == "특화 에이전트"
