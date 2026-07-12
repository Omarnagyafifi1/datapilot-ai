"""Characterization tests for the core graph flow (app/agents/graph.py)."""
import pytest
from app.agents.state.agent_state import AgentState


class MockLLM:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.call_count = 0

    def generate(self, prompt, **kwargs):
        self.call_count += 1
        if "Your task is to analyze the context" in prompt:
            return self.responses.get("insight", '[{"ar":"بيانات","en":"Data insight"}]')
        if "follow-up questions" in prompt:
            return self.responses.get("suggestion", '[{"ar":"سؤال؟","en":"Question?"}]')
        return self.responses.get("default", "SELECT 1")


from app.agents.graph import insight_node, suggestion_node, _fallback_insights, _normalize_insights, _parse_insights


def test_insight_node_happy_path():
    llm = MockLLM(responses={"insight": '[{"ar":"نمو","en":"Growth trend"}]'})
    state = AgentState(question="Show sales", source_id="test", query_results=[{"sales": 100}])
    result = insight_node(state, llm)
    assert "insights" in result
    assert len(result["insights"]) == 1
    assert result["insights"][0]["en"] == "Growth trend"
    assert result["insights"][0]["ar"] == "نمو"


def test_insight_node_empty_results():
    llm = MockLLM()
    state = AgentState(question="Show sales", source_id="test", query_results=[])
    result = insight_node(state, llm)
    assert result["insights"] == _fallback_insights()
    assert llm.call_count == 0


def test_insight_node_parse_failure():
    llm = MockLLM(responses={"insight": "not valid json"})
    state = AgentState(question="Show sales", source_id="test", query_results=[{"sales": 100}])
    result = insight_node(state, llm)
    assert result["insights"] == _fallback_insights()


def test_suggestion_node_happy_path():
    llm = MockLLM(responses={"suggestion": '[{"ar":"المزيد","en":"Show more"}]'})
    state = AgentState(question="Show sales", source_id="test", sql="SELECT * FROM sales", query_results=[{"sales": 100}])
    result = suggestion_node(state, llm)
    assert "suggestions" in result
    assert len(result["suggestions"]) == 1


def test_suggestion_node_empty_results():
    llm = MockLLM()
    state = AgentState(question="Show sales", source_id="test", query_results=[])
    result = suggestion_node(state, llm)
    assert result["suggestions"] == []
    assert llm.call_count == 0


def test_normalize_insights_single_dict():
    result = _normalize_insights({"ar": "نص", "en": "text"})
    assert result == [{"ar": "نص", "en": "text"}]


def test_normalize_insights_empty_list():
    result = _normalize_insights([])
    assert result is None


def test_normalize_insights_missing_fields():
    result = _normalize_insights([{"ar": "", "en": ""}])
    assert result is None


def test_parse_insights_markdown_wrapped():
    result = _parse_insights('```json\n[{"ar":"أ","en":"a"}]\n```')
    assert result == [{"ar": "أ", "en": "a"}]


def test_parse_insights_raw_text():
    result = _parse_insights('plain text with no json')
    assert result is None
