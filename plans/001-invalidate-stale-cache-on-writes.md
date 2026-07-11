# Plan 001: Invalidate stale cache on write operations

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat c5d07ba..HEAD -- backend/app/agents/graph.py backend/app/services/db_service.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: plans/010-add-thread-safety-locks.md (must be done first, as it adds the lock around `_STALE_CACHE`)
- **Category**: bug
- **Planned at**: commit `c5d07ba`, 2026-07-11

## Why this matters

When a write operation (INSERT/UPDATE/DELETE) succeeds via the agent graph, the read result cache (`_STALE_CACHE`) is never invalidated. Subsequent read queries against the same source return stale cached results — the user sees pre-write data. The schema cache (`_SCHEMA_CACHE`) IS invalidated on writes, but the result cache is not, which is the bug.

## Current state

In `backend/app/agents/graph.py`, the `sql_execution_node` function (line ~478) handles caching:

```python
# Check cache (skip for write operations — they must always execute)
ck = _cache_key(state.sql, state.source_id)
if not is_write and ck in _STALE_CACHE:
    logger.debug("SQL cache hit for: %s", state.sql[:60])
    return {"query_results": list(_STALE_CACHE[ck]), "success": True}

try:
    results = execute_sql(db_service, state.sql, state.source_id) or []
    # Only cache read queries
    if not is_write:
        if len(_STALE_CACHE) >= _STALE_CACHE_MAX:
            _STALE_CACHE.pop(next(iter(_STALE_CACHE)))
        _STALE_CACHE[ck] = list(results)
    else:
        # Invalidate schema cache after writes (new tables/columns may exist)
        from app.services.db_service import _SCHEMA_CACHE
        _SCHEMA_CACHE.pop(state.source_id, None)
    return {"query_results": results, "success": True}
```

Notice the `else` branch (line 522-525): it only invalidates `_SCHEMA_CACHE`, but `_STALE_CACHE` still holds stale entries keyed by `source_id:::sql`. Future read queries matching any of those keys will get the cached pre-write results.

The `_STALE_CACHE` is a module-level dict at `graph.py:470`:
```python
_STALE_CACHE: dict[str, list[dict]] = {}
_STALE_CACHE_MAX = 50
```

The cache key function at `graph.py:474`:
```python
def _cache_key(sql: str, source_id: str) -> str:
    return f"{source_id}:::{sql.strip().lower()}"
```

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Typecheck | `python -c "import ast; ast.parse(open('backend/app/agents/graph.py').read()); print('OK')"` | exit 0, prints OK |
| Tests | `python -m pytest backend/final_test/ -v` | all pass |

## Scope

**In scope** (the only files you should modify):
- `backend/app/agents/graph.py`

**Out of scope** (do NOT touch, even though they look related):
- `backend/app/services/db_service.py` — the schema cache lives here, but plan 010 will add locks to it; do not touch it now
- `backend/app/agents/tools/sql_tool.py` — contains a legacy copy of `_STALE_CACHE`-like logic; leave it alone

## Git workflow

- Branch: `advisor/001-stale-cache-invalidate`
- Commit message style: `fix: invalidate _STALE_CACHE on write operations`
- Do NOT push or open a PR unless the operator instructed it

## Steps

### Step 1: Add cache invalidation in the write branch of `sql_execution_node`

In `backend/app/agents/graph.py`, locate the `else` block inside `sql_execution_node` that handles write operations (starts at line 522, with `else:` after `if not is_write:`). Currently it reads:

```python
    else:
        # Invalidate schema cache after writes (new tables/columns may exist)
        from app.services.db_service import _SCHEMA_CACHE
        _SCHEMA_CACHE.pop(state.source_id, None)
```

Change it to also invalidate the stale result cache by clearing all entries for this `source_id`:

```python
    else:
        # Invalidate both caches after writes — data has changed
        from app.services.db_service import _SCHEMA_CACHE
        _SCHEMA_CACHE.pop(state.source_id, None)
        # Invalidate stale read cache for this source
        keys_to_remove = [k for k in _STALE_CACHE if k.startswith(f"{state.source_id}:::")]
        for k in keys_to_remove:
            _STALE_CACHE.pop(k, None)
```

This iterates over `_STALE_CACHE` keys and removes any that start with `{source_id}:::`. For the typical case of ~50 entries this is negligible overhead.

**Verify**: Read the modified `sql_execution_node` and confirm the `else` branch now removes both `_SCHEMA_CACHE[source_id]` and all `_STALE_CACHE` entries matching that source.

### Step 2: Run typecheck and tests

```bash
python -c "import ast; ast.parse(open('backend/app/agents/graph.py').read()); print('OK')"
```

```bash
python -m pytest backend/final_test/ -v
```

## Test plan

No new tests needed for this fix. The existing integration tests in `backend/final_test/test_integrations.py` will validate that the graph still works. If you want to add a regression test:

- Add a test in `backend/final_test/test_units.py` that:
  1. Inserts an entry into `_STALE_CACHE` for a test source
  2. Calls `sql_execution_node` with a write intent
  3. Asserts the entry was removed from `_STALE_CACHE`

Model after existing test format in `test_units.py` (plain functions with `assert`, no classes).

## Done criteria

ALL must hold:

- [ ] `python -c "import ast; ast.parse(open('backend/app/agents/graph.py').read()); print('OK')"` exits 0
- [ ] `python -m pytest backend/final_test/ -v` exits 0, all tests pass
- [ ] The `else` branch in `sql_execution_node` contains both `_SCHEMA_CACHE.pop(state.source_id, None)` and a loop removing `_STALE_CACHE` entries matching `state.source_id`
- [ ] `SELECT 'ERROR: '` pattern does not appear in modified code (that's `_is_error_sql`, not related)
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated to DONE

## STOP conditions

Stop and report back (do not improvise) if:

- The code at the locations in "Current state" doesn't match the excerpts (the codebase has drifted since this plan was written).
- Plan 010 (thread safety locks) has not been applied yet — this plan depends on it; if 010 is not yet done, stop.
- A step's verification fails twice after a reasonable fix attempt.
- The fix appears to require touching an out-of-scope file.
- You discover that `_STALE_CACHE` has been renamed or removed.

## Maintenance notes

- If a TTL-based cache eviction is ever added to `_STALE_CACHE`, the write-invalidation logic here should remain as the eager path (writes always invalidate immediately, TTL is the safety net).
- The `keys_to_remove` list comprehension creates a temporary list of all matching keys. For `_STALE_CACHE_MAX=50` this is fine, but if the max grows significantly, consider a different approach.
