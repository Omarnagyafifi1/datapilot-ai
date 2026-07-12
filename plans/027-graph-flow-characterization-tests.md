# Plan 027: Write Characterization Tests for Core Graph Flow

> **Executor instructions**: Follow step by step. Verify each test passes before moving on.
>
> **Drift check**: `git diff --stat 0d59108..HEAD -- backend/app/agents/graph.py backend/app/agents/state/agent_state.py backend/app/agents/nodes/`

## Status

- **Priority**: P2
- **Effort**: L
- **Risk**: LOW
- **Depends on**: none (but 022 should land first to avoid testing against known-bug state)
- **Category**: tests
- **Planned at**: commit `0d59108`, 2026-07-12

## Why this matters

The core Text-to-SQL graph (`graph.py:1350` lines, 15+ nodes) has zero test coverage. The entire pipeline — routing, schema filtering, SQL generation, execution, retries, insight/suggestion/visualization — flies without regression safety. Every change to the graph ships without automated verification. Characterization tests freeze current behavior so refactoring is safe.

## Current state

`backend/final_test/` has 19 tests across 2 files covering only utility functions (db_service helpers, visualization_service, report_service, settings_service). Zero tests call `AgentGraph.run()` or any individual node.

The repo testing pattern (from existing tests) uses:
- `pytest` with FastAPI `TestClient`
- Simple assert patterns: `assert response.status_code == 200`, `assert data.get("success")`
- Inline test data, no external fixtures

## Scope

**In scope (create):**
- `backend/final_test/test_graph.py` — new test file

**Out of scope:**
- Changes to `graph.py`, `agent_state.py`, or any production code
- Integration tests with real LLMs (all LLM calls must be mocked)
- Tests for the modification SQL flow (ADD/UPDATE/DELETE)

## Git workflow

- Branch: `advisor/027-graph-flow-tests`
- Commit message: `test: add characterization tests for core graph flow`

## Steps

### Step 1: Create mock LLM and DB service fixtures

In `backend/final_test/test_graph.py`, define a `MockLLM` class that returns deterministic responses and a `MockDBService` that returns canned results:

```python
"""Characterization tests for the core graph flow (app/agents/graph.py)."""
import pytest
from app.agents.state.agent_state import AgentState

class MockLLM:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.call_count = 0

    def generate(self, prompt, **kwargs):
        self.call_count += 1
        # Return canned response based on prompt content
        if "Your task is to analyze the context" in prompt:  # insight
            return self.responses.get("insight", '[{"ar":"بيانات","en":"Data insight"}]')
        if "Suggest logical follow-up questions" in prompt:  # suggestion
            return self.responses.get("suggestion", '[{"ar":"سؤال؟","en":"Question?"}]')
        return self.responses.get("default", "SELECT 1")


class MockDBService:
    def __init__(self, results=None):
        self.results = results or [{"col": "val"}]

    def get_dialect(self, source_id=None):
        return "sqlite"

    def run_query(self, sql, timeout=15):
        return list(self.results)

    def execute_query(self, sql, source_id, timeout=15):
        return list(self.results)
```

**Verify**: `pytest backend/final_test/test_graph.py -v` — 0 tests collected but no import errors.

### Step 2: Test `insight_node` — happy path

```python
from app.agents.graph import insight_node, suggestion_node, _fallback_insights, _normalize_insights, _parse_insights

def test_insight_node_happy_path():
    llm = MockLLM(responses={"insight": '[{"ar":"نمو","en":"Growth trend"}]'})
    state = AgentState(question="Show sales", query_results=[{"sales": 100}])
    result = insight_node(state, llm)
    assert "insights" in result
    assert len(result["insights"]) == 1
    assert result["insights"][0]["en"] == "Growth trend"
    assert result["insights"][0]["ar"] == "نمو"
```

### Step 3: Test `insight_node` — empty results fallback

```python
def test_insight_node_empty_results():
    llm = MockLLM()
    state = AgentState(question="Show sales", query_results=[])
    result = insight_node(state, llm)
    assert result["insights"] == _fallback_insights()
    assert llm.call_count == 0  # LLM should NOT be called
```

### Step 4: Test `insight_node` — LLM returns unparseable JSON

```python
def test_insight_node_parse_failure():
    llm = MockLLM(responses={"insight": "not valid json"})
    state = AgentState(question="Show sales", query_results=[{"sales": 100}])
    result = insight_node(state, llm)
    assert result["insights"] == _fallback_insights()
```

### Step 5: Test `suggestion_node` — happy path

```python
def test_suggestion_node_happy_path():
    llm = MockLLM(responses={"suggestion": '[{"ar":"المزيد","en":"Show more"}]'})
    state = AgentState(question="Show sales", sql="SELECT * FROM sales", query_results=[{"sales": 100}])
    result = suggestion_node(state, llm)
    assert "suggestions" in result
    assert len(result["suggestions"]) == 1
```

### Step 6: Test `suggestion_node` — empty results

```python
def test_suggestion_node_empty_results():
    llm = MockLLM()
    state = AgentState(question="Show sales", query_results=[])
    result = suggestion_node(state, llm)
    assert result["suggestions"] == []
    assert llm.call_count == 0
```

### Step 7: Test `_normalize_insights` edge cases

```python
def test_normalize_insights_single_dict():
    result = _normalize_insights({"ar": "نص", "en": "text"})
    assert result == [{"ar": "نص", "en": "text"}]

def test_normalize_insights_empty_list():
    result = _normalize_insights([])
    assert result is None

def test_normalize_insights_missing_fields():
    result = _normalize_insights([{"ar": "", "en": ""}])
    assert result is None
```

### Step 8: Test `_parse_insights` edge cases

```python
def test_parse_insights_markdown_wrapped():
    result = _parse_insights('```json\n[{"ar":"أ","en":"a"}]\n```')
    assert result == [{"ar": "أ", "en": "a"}]

def test_parse_insights_raw_text():
    result = _parse_insights('plain text with no json')
    assert result is None
```

### Step 9: Run all tests

**Verify**: `pytest backend/final_test/ -v` — all tests pass (existing 19 + new ~12 = ~31 total).

## Test plan

This plan IS a test plan — every step above is a test. Cover:
- Happy paths for insight and suggestion nodes
- Empty results → fallback for insights, empty list for suggestions
- LLM parse failures → graceful fallback
- JSON edge cases (markdown-wrapped, single dict, empty, missing fields)

## Done criteria

- [ ] `backend/final_test/test_graph.py` exists with MockLLM and MockDBService fixtures
- [ ] At least 10 test functions covering insight_node, suggestion_node, and parser functions
- [ ] `pytest backend/final_test/ -v` — all pass (≥29 total)
- [ ] No changes to production code files
- [ ] `plans/README.md` status row updated

## STOP conditions

- `insight_node` or `suggestion_node` function signatures changed since 0d59108 (check the import and call patterns)
- `AgentState` constructor signature changed (check dataclass fields)
- Any step requires modifying production code to make tests pass (tests should characterize EXISTING behavior)

## Maintenance notes

When new nodes are added to the graph, corresponding tests should be added here. When node behavior is intentionally changed, update the test expectations first (test-driven refactoring). The mock approach (MockLLM returning canned JSON) should be extended for any new LLM-dependent nodes. The `MAX_RETRIES` constant at `graph.py:49` is referenced in route logic but not tested here — consider adding retry-path tests when the graph flow tests are expanded.
