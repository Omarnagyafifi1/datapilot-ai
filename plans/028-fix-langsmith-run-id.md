# Plan 028: Fix LangSmith Evaluation Using thread_id Instead of run_id

> **Executor instructions**: Follow step by step. Verify each command.
>
> **Drift check**: `git diff --stat 0d59108..HEAD -- backend/app/services/evaluation_service.py backend/app/agents/graph.py`

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `0d59108`, 2026-07-12

## Why this matters

The `post_evaluation_to_langsmith` function (evaluation_service.py:244-310) creates feedback with `run_id=thread_id` — where `thread_id` is a LangGraph conversation UUID, not the actual LangSmith trace run ID. LangSmith silently ignores feedback posted to non-existent run IDs. All 8 feedback keys (syntax_valid, correctness, completeness, latency, overall_quality, etc.) are silently dropped. The EV-01 evaluation feature delivers zero value.

## Current state

In `backend/app/services/evaluation_service.py:260-300`, every `create_feedback` call uses thread_id:
```python
_LS_CLIENT.create_feedback(
    run_id=thread_id,  # BUG: thread_id is a LangGraph conversation UUID, not a LangSmith run_id
    key="sql_syntax_valid",
    ...
)
```

The call site in `graph.py:1234-1267` passes `resolved_thread_id` (a `str(uuid4())`) to `post_evaluation_to_langsmith`.

LangSmith's `create_feedback` needs the actual tracing `run_id` — the UUID assigned by LangSmith when a trace starts. This is available via LangGraph's internal `RunConfig` but not easily plumbed through the current architecture.

## Scope

**In scope:**
- `backend/app/services/evaluation_service.py` — `post_evaluation_to_langsmith` function
- `backend/app/agents/graph.py` — the call site in `run()` method

**Out of scope:**
- Changes to how LangSmith tracing is initialized (it works — LangGraph traces appear in LangSmith dashboard)
- Adding new evaluation metrics

## Steps

### Step 1: Determine correct approach

LangGraph's `invoke()` returns state but not the LangSmith run_id directly. Two approaches:

**Approach A**: Use the `RunnableConfig`'s `run_id` field. When LangGraph calls `add_node` callbacks, the config has a `run_id`. But this requires plumbing through `AgentState`.

**Approach B**: Use LangSmith's client API to find the latest trace run_id by thread_id tag. `_LS_CLIENT.list_runs(...)` can filter by tags.

**Approach C**: Use `langsmith.run_trees.ContextRunTree` or `langsmith.run_helpers` to get the current run context.

Recommendation: **Approach B** is simplest and least invasive. After the graph completes, query LangSmith for the run associated with the thread_id tag.

In `evaluation_service.py`, replace `run_id=thread_id` with:
```python
import uuid

def _resolve_run_id(thread_id: str) -> str | None:
    """Find the LangSmith run_id associated with a thread by listing recent runs."""
    try:
        runs = list(_LS_CLIENT.list_runs(
            run_type="chain",
            filter={"tags": [f"thread_id:{thread_id}"]},
            limit=1,
        ))
        if runs:
            return str(runs[0].id)
    except Exception:
        logger.debug("Could not resolve run_id for thread %s", thread_id, exc_info=True)
    return thread_id  # fallback: use thread_id as-is
```

Then call `_resolve_run_id(thread_id)` once at the start of `post_evaluation_to_langsmith` and use the resolved ID.

**Verify**: `python -m py_compile backend/app/services/evaluation_service.py` — exit 0. `pytest backend/final_test/ -v` — all pass.

### Step 2: Verify LangSmith tags are being applied

Check that the LangGraph configuration applies a `thread_id` tag that `list_runs` can filter on. In `graph.py:1219-1220`:
```python
config = {"configurable": {"thread_id": resolved_thread_id}}
config["configurable"]["user_id"] = source_id
```

LangGraph may or may not propagate `configurable` values as LangSmith tags. If not, add them explicitly with LangSmith's `run_on_` context manager or by setting `metadata` on the config.

**Verify**: If LangSmith tags aren't propagated, modify the config in `graph.py:1219` to set `metadata`:
```python
config = {
    "configurable": {"thread_id": resolved_thread_id, "user_id": source_id},
    "metadata": {"thread_id": resolved_thread_id},
}
```

## Test plan

Manual verification only (requires live LangSmith API access):
1. Run a query through the system
2. Check LangSmith dashboard for the trace
3. Confirm feedback keys appear on the trace (syntax_valid, correctness, etc.)

## Done criteria

- [ ] `_resolve_run_id` function added to `evaluation_service.py`
- [ ] `post_evaluation_to_langsmith` resolves run_id via LangSmith API before posting feedback
- [ ] Fallback to raw `thread_id` when resolution fails
- [ ] `graph.py` config includes `metadata` with `thread_id`
- [ ] `pytest backend/final_test/ -v` — all pass
- [ ] No files outside in-scope list modified
- [ ] `plans/README.md` status row updated

## STOP conditions

- `_LS_CLIENT` is `None` or unavailable (eval service silently disabled) — this is expected, don't change it
- The `list_runs` API signature differs from what's shown (consult LangSmith SDK docs for the current parameter shape)

## Maintenance notes

The `_resolve_run_id` fallback returns the thread_id, which continues current behavior (feedback silently dropped). This is safe but not ideal — consider adding a logger warning when resolution fails. If LangGraph adds official `run_id` access in a future version, switch to Approach A (direct plumbing) for reliability.
