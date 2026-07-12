# Plan 022: Fix Semantic Cache Poisoning and Parallel LLM Contention

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If anything in the "STOP conditions" section occurs, stop and report — do not improvise. When done, update the status row for this plan in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat 0d59108..HEAD -- backend/app/agents/graph.py` — if graph.py changed, compare the "Current state" excerpts against live code; on mismatch, treat it as a STOP condition.

## Status

- **Priority**: P0
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `0d59108`, 2026-07-12

## Why this matters

When insight or suggestion generation fails (e.g., LLM rate-limit during the parallel call in `_post_process_node`), the semantic cache stores the entire output including fallback messages ("No data to analyze" / "No items available"). Every subsequent identical query returns the cached fallback, even when the LLM would succeed on retry. This is the root cause of the user's reported issue where valid SQL results display but insights and suggestions are permanently blank.

## Current state

Two interacting bugs in `backend/app/agents/graph.py`:

### Bug A — Cache stores fallback output (lines 1224-1232)

```python
# Store in semantic cache on success
if not preview_only and output.get("status") == "completed" and not output.get("requires_approval"):
    store_key = _build_semantic_cache_storage_key(...)
    _SEMANTIC_CACHE[cache_key] = dict(output)
    _SEMANTIC_CACHE[store_key] = dict(output)
```

The condition only checks `status == "completed"` (which is always set). It does not verify that insights/suggestions are real — fallback values get cached permanently.

### Bug B — Parallel LLM calls cause rate-limit contention (lines 1049-1061)

```python
def run_insights(s: AgentState) -> dict:
    return insight_node(s, self.llm)

def run_suggestions(s: AgentState) -> dict:
    return suggestion_node(s, self.llm)

with ThreadPoolExecutor(max_workers=3) as pool:
    futures = {pool.submit(fn, state): key for key, fn in tasks.items()}
```

Both `insight_node` and `suggestion_node` call `self.llm.generate()` (line 847 and 876 respectively). Running them in parallel doubles the concurrent LLM requests against the same provider, triggering 429 rate-limit errors.

### Bug C — `_SEMANTIC_CACHE` never invalidated on writes (lines 723-729)

```python
else:
    # Invalidate both caches after writes
    from app.services.db_service import _SCHEMA_CACHE
    _SCHEMA_CACHE.pop(state.source_id, None)
    keys_to_remove = [k for k in _STALE_CACHE if k.startswith(f"{state.source_id}:::")]
    for k in keys_to_remove:
        _STALE_CACHE.pop(k, None)
```

This block invalidates `_SCHEMA_CACHE` and `_STALE_CACHE` on writes, but never touches `_SEMANTIC_CACHE`. Write-then-read queries return pre-write cached results.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Tests | `pytest backend/final_test/ -v` | 19 passed |
| Typecheck | `python -m py_compile backend/app/agents/graph.py` | exit 0 |

## Scope

**In scope:**
- `backend/app/agents/graph.py` — cache write logic, parallel LLM execution, write invalidation

**Out of scope:**
- `backend/app/services/evaluation_service.py` — separate plan (028)
- `backend/app/agents/prompts.py` — no prompt changes needed
- Any frontend files

## Git workflow

- Branch: `advisor/022-fix-cache-parallel-llm`
- Commits per step (3 commits total), conventional commit style: `fix: <description>`
- Do NOT push or open a PR unless instructed

## Steps

### Step 1: Run insight and suggestion sequentially to avoid rate-limit contention

In `_post_process_node` (lines 1042-1077), replace the ThreadPoolExecutor with sequential calls. The visualization node (no LLM) can run in the same thread:

```python
def _post_process_node(self, state: AgentState) -> dict:
    results: dict[str, Any] = {}
    try:
        results.update(visualization_node(state))
    except Exception:
        logger.exception("post_process_node visualization failed")
        results["visualization"] = None

    try:
        results.update(insight_node(state, self.llm))
    except Exception:
        logger.exception("post_process_node insights failed")
        results["insights"] = _fallback_insights()

    try:
        results.update(suggestion_node(state, self.llm))
    except Exception:
        logger.exception("post_process_node suggestions failed")
        results["suggestions"] = []

    return results
```

Remove the `from concurrent.futures import ThreadPoolExecutor, as_completed` import if it becomes unused. Check at line 20.

**Verify**: `python -c "import ast; ast.parse(open('backend/app/agents/graph.py').read()); print('Syntax OK')"` — exit 0. Also `pytest backend/final_test/ -v` — all pass.

### Step 2: Add fallback check before caching semantic output

In `run()` method (lines 1224-1232), change the cache-write condition to skip caching when insights or suggestions are fallback values:

```python
# Only cache if insights/suggestions are real (not fallbacks)
insights_ok = bool(output.get("insights")) and output["insights"] != _fallback_insights()
suggestions_ok = bool(output.get("suggestions"))
if not preview_only and output.get("status") == "completed" and not output.get("requires_approval") and insights_ok and suggestions_ok:
    if len(_SEMANTIC_CACHE) >= _SEMANTIC_CACHE_MAX:
        _SEMANTIC_CACHE.pop(next(iter(_SEMANTIC_CACHE)))
    _SEMANTIC_CACHE[cache_key] = dict(output)
```

Remove the `store_key` write and `_build_semantic_cache_storage_key` call. The store_key function and variable are no longer needed.

**Verify**: `pytest backend/final_test/ -v` — all pass. Also check: `git diff` should show the store_key variable removed from the `run()` method.

### Step 3: Invalidate `_SEMANTIC_CACHE` on write operations

In `sql_execution_node` (lines 723-729), add `_SEMANTIC_CACHE` invalidation alongside the existing `_SCHEMA_CACHE` and `_STALE_CACHE` invalidation:

```python
else:
    from app.services.db_service import _SCHEMA_CACHE
    _SCHEMA_CACHE.pop(state.source_id, None)
    keys_to_remove = [k for k in _STALE_CACHE if k.startswith(f"{state.source_id}:::")]
    for k in keys_to_remove:
        _STALE_CACHE.pop(k, None)
    # Invalidate semantic cache on writes — data has changed
    global _SEMANTIC_CACHE
    _SEMANTIC_CACHE.clear()
```

**Verify**: `pytest backend/final_test/ -v` — all 19 pass.

## Test plan

No new tests in this plan. The existing 19 tests must continue to pass. The `_post_process_node` isn't covered by current unit tests (see plan 027).

Manual verification: trigger a query with data, confirm insights and suggestions appear. Trigger the same query again — cache should return proper results, not fallbacks.

## Done criteria

- [ ] `pytest backend/final_test/ -v` — 19 passed
- [ ] `python -m py_compile backend/app/agents/graph.py` — exit 0
- [ ] Sequential calls in `_post_process_node` — no ThreadPoolExecutor for LLM calls
- [ ] Cache write condition checks insights != `_fallback_insights()`
- [ ] Store key variable removed from `run()` method
- [ ] `_SEMANTIC_CACHE.clear()` called on write operations in `sql_execution_node`
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

- The code at the locations above doesn't match the excerpts (codebase has drifted since this plan was written)
- A step's verification fails twice after a reasonable fix attempt
- The fix requires touching an out-of-scope file

## Maintenance notes

- If the `_fallback_insights()` function signature changes (e.g., returns different fallback structure), the cache check in step 2 must be updated to match.
- This plan is a prerequisite for plan 028 (LangSmith evaluation) — it changes the output structure that LangSmith posts about.
