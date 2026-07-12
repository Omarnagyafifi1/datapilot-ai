# Plan 031: Remove Dead `store_key` Cache Write

> **Executor instructions**: Read the target lines, confirm the code path is unreachable, delete 3 lines. No test change needed.
>
> **Drift check**: `git diff --stat 0d59108..HEAD -- backend/app/agents/graph.py`

## Status

- **Priority**: P4 (cosmetic/tech-debt)
- **Effort**: XS
- **Risk**: NONE
- **Depends on**: none
- **Category**: tech-debt
- **Planned at**: commit `0d59108`, 2026-07-12

## Why this matters

Semantic cache keys are derived from `_question_hash()` (see Plan 030). The variables `store_key` defined at `graph.py:1266-1268` are computed from `source_id` + `question`, never read by any subsequent code, and exist on a code path guarded by `if not cached_result` — meaning they only execute when there is no cache hit, making them doubly irrelevant. They waste CPU cycles (calls `_semantic_cache_key_mapping`) and mislead readers.

## Current state

```python
# graph.py:1266-1268 — inside `if not cached_result:` branch, after `cached_result` is already known to be None
store_key = _semantic_cache_key_mapping(
    state["source_id"], state["question"]
)
```

## Scope

**In scope:** `backend/app/agents/graph.py:1266-1268` — exactly 3 lines (the `store_key` assignment)

**Out of scope:** Any other cache-write logic, `_semantic_cache_key_mapping` function itself, or `_question_hash`

## Steps

### Step 1: Delete the dead assignment

Remove these 3 lines from `graph.py`:

```python
store_key = _semantic_cache_key_mapping(
    state["source_id"], state["question"]
)
```

**Verification**: `python -m py_compile backend/app/agents/graph.py` — exit 0. `pytest backend/final_test/ -v` — all pass.

## Done criteria

- [ ] Lines 1266-1268 (or the equivalent 3-line `store_key` assignment in the `if not cached_result:` branch) are removed
- [ ] `pytest backend/final_test/ -v` — all pass
- [ ] No files outside in-scope list modified
- [ ] `plans/README.md` status row updated

## STOP conditions

- The `_semantic_cache_key_mapping` function was removed entirely — plan is moot
- The cache write path was refactored to use `store_key` somewhere — stop and verify intent
