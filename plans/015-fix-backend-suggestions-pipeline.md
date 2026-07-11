# Plan 015: Fix backend suggestions pipeline resilience

> **Executor instructions**: Follow this plan step by step. Run every
> verification command before moving to the next step. If anything in the
> "STOP conditions" section occurs, stop and report.
>
> **Drift check**: `git diff --stat cea37b2..HEAD -- backend/app/agents/graph.py backend/app/api/routes.py`
> If changed, compare excerpts against live code; mismatch = STOP.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MEDIUM
- **Depends on**: none
- **Category**: bug / perf
- **Planned at**: commit cea37b2, 2026-07-11

## Why this matters

Three issues make the suggestions pipeline unreliable: (1) `_post_process_node` silently swallows all exceptions and returns empty suggestions — users see "No items available" when the LLM rate-limits or times out, with no feedback; (2) the suggestions cache at `routes.py` has a check-then-set race and no TTL — stale suggestions persist forever and concurrent calls duplicate LLM work; (3) `suggestion_node` skips suggestions entirely for queries with ≤1 row, even when meaningful follow-ups exist.

## Current state

### Issue A: Swallowed exceptions in _post_process_node

`backend/app/agents/graph.py:861-871`:
```python
                except Exception as exc:
                    logger.warning("post_process_node %s failed: %s", key, exc)
                    if key == "insights":
                        results["insights"] = _fallback_insights()
                    elif key == "suggestions":
                        results["suggestions"] = []
                    elif key == "visualization":
                        results["visualization"] = None
```

### Issue B: Suggestions cache race + no TTL

`backend/app/api/routes.py:312`:
```python
_SUGGESTIONS_CACHE: dict[str, list[dict[str, str]]] = {}
```

Lines 333-360 — `_generate_and_cache_suggestions()` checks `if source_id in _SUGGESTIONS_CACHE` then sets `_SUGGESTIONS_CACHE[source_id]` — check-then-set with no lock. Also no TTL — once cached, suggestions are never refreshed.

### Issue C: ≤1 row queries get zero suggestions

`backend/app/agents/graph.py:640-642`:
```python
    if not state.query_results or len(state.query_results) <= 1:
        return {"suggestions": []}
```

A query like "How many employees?" (1 row result) gets zero suggestions, even though "Show departments" or "List top earners" are valid follow-ups.

## Scope

**In scope**:
- `backend/app/agents/graph.py`
- `backend/app/api/routes.py`

**Out of scope**:
- Any frontend files
- `backend/app/services/db_service.py` — the engine cache locking is covered in Plan 016

## Git workflow

- Branch: `advisor/015-fix-backend-suggestions-pipeline`
- Commit message: `fix: improve suggestions pipeline error handling, caching, and single-row handling`

## Commands you will need

| Purpose   | Command                  | Expected on success |
|-----------|--------------------------|---------------------|
| Python syntax | `python -m py_compile backend/app/agents/graph.py` | exit 0 |
| Python syntax | `python -m py_compile backend/app/api/routes.py` | exit 0 |

## Steps

### Step 1: Improve _post_process_node error logging and user feedback

In `backend/app/agents/graph.py`, change the exception handler at lines 861-871:

1. Upgrade `logger.warning` to `logger.error` so it's visible in production logs
2. Instead of silently setting `suggestions: []`, set a `suggestion_error` field on state that the frontend can render as a non-intrusive notice

The suggestion error should be placed on the state so the documentation step can include it. Look at how `AgentState` is structured (read the state model at `backend/app/agents/state/agent_state.py`) — add a `suggestion_error` field if it doesn't exist, or use `documentation._suggestion_error`.

Actually, simpler approach: instead of adding a new state field, leave `suggestions` as empty array but change the log level to `ERROR` and include more context (source_id, question snippet) so operators can diagnose. Also add a `logger.exception(...)` call to capture the full traceback.

Replace:
```python
                except Exception as exc:
                    logger.warning("post_process_node %s failed: %s", key, exc)
                    if key == "insights":
                        results["insights"] = _fallback_insights()
                    elif key == "suggestions":
                        results["suggestions"] = []
                    elif key == "visualization":
                        results["visualization"] = None
```

With:
```python
                except Exception as exc:
                    logger.exception("post_process_node %s failed", key)
                    if key == "insights":
                        results["insights"] = _fallback_insights()
                    elif key == "suggestions":
                        results["suggestions"] = []
                    elif key == "visualization":
                        results["visualization"] = None
```

**Verify**: Read the modified lines — confirm `logger.exception` with traceback is used instead of `logger.warning`. `python -m py_compile backend/app/agents/graph.py` — exit 0.

### Step 2: Fix ≤1 row skip to allow single-row queries

In `backend/app/agents/graph.py` line 641, change the condition:
```python
    if not state.query_results or len(state.query_results) <= 1:
```
To:
```python
    if not state.query_results:
```

This means single-row results still get suggestions, while empty results still skip.

**Verify**: Read line 641 — confirm it's `if not state.query_results:`. `python -m py_compile backend/app/agents/graph.py` — exit 0.

### Step 3: Add cache lock and TTL to suggestions cache

In `backend/app/api/routes.py`:

1. Add a threading lock for the cache near `_SUGGESTIONS_CACHE`:
```python
_SUGGESTIONS_CACHE: dict[str, list[dict[str, str]]] = {}
_SUGGESTIONS_CACHE_LOCK = threading.Lock()
_SUGGESTIONS_CACHE_TTL = 3600  # 1 hour
```
Add `import threading` if not already present.

2. In `_generate_and_cache_suggestions` (line 331), wrap the check-then-set in the lock:
```python
def _generate_and_cache_suggestions(source_id: str, graph) -> None:
    with _SUGGESTIONS_CACHE_LOCK:
        if source_id in _SUGGESTIONS_CACHE:
            cached_at, cached_val = _SUGGESTIONS_CACHE[source_id]
            if time.time() - cached_at < _SUGGESTIONS_CACHE_TTL:
                return
    # ... existing generation logic ...
    with _SUGGESTIONS_CACHE_LOCK:
        if parsed:
            _SUGGESTIONS_CACHE[source_id] = (time.time(), parsed[:4])
            return
    # ... fallback ...
    with _SUGGESTIONS_CACHE_LOCK:
        _SUGGESTIONS_CACHE[source_id] = (time.time(), fallback[:4])
```

This changes the cache value from `list[dict]` to `tuple[float, list[dict]]`. Also need to add `import time` if not present.

3. In `get_datasource_suggestions` (line 377), update the cache read to handle the new tuple format:
```python
    with _SUGGESTIONS_CACHE_LOCK:
        cached = _SUGGESTIONS_CACHE.get(id)
    if cached:
        cached_at, cached_val = cached
        if time.time() - cached_at < _SUGGESTIONS_CACHE_TTL:
            return _resp(success=True, message="Suggestions fetched", data=cached_val)
```

4. Also in the `get_datasource_suggestions` handler, the inline check at line 383-384 should be removed and replaced with the TTL-aware check above. The function should call `_generate_and_cache_suggestions` if cache is missing or expired.

**Verify**: 
- Read the modified `_generate_and_cache_suggestions` — confirm it uses the lock and TTL
- Read `get_datasource_suggestions` — confirm TTL-aware cache reads
- `python -m py_compile backend/app/api/routes.py` — exit 0

## Test plan

- `python -m py_compile` on both modified files — exit 0
- Manual: load a datasource page → suggestions should appear on first load and be served from cache on subsequent loads
- Manual: wait 1+ hour → suggestions should regenerate

## Done criteria

- [ ] `graph.py` — `_post_process_node` uses `logger.exception` for suggestion/insight/viz failures
- [ ] `graph.py` — `suggestion_node` allows single-row queries to generate suggestions
- [ ] `routes.py` — `_SUGGESTIONS_CACHE_LOCK` and `_SUGGESTIONS_CACHE_TTL` defined
- [ ] `routes.py` — `_generate_and_cache_suggestions` uses the lock and stores `(timestamp, data)` tuples
- [ ] `routes.py` — `get_datasource_suggestions` is TTL-aware
- [ ] `python -m py_compile` exits 0 on both files

## STOP conditions

- Code at cited locations doesn't match excerpts
- `AgentState` is a TypedDict and adding `suggestion_error` would break other consumers (skip state changes, just fix logging)
- `_SUGGESTIONS_CACHE` is accessed in other places not mentioned here (search the file for all references)
- Validation fails twice

## Maintenance notes

- The TTL of 3600s (1 hour) is a reasonable default. If the datasource's schema changes, the cache becomes stale until TTL expires. Consider adding cache invalidation on schema-change events in a future plan.
- The tuple format change `(timestamp, data)` is backward-incompatible with any existing cache state, but since the cache is in-memory and resets on restart, this is safe.
