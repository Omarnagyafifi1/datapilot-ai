# Plan 010: Add thread safety locks to module-level caches

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat c5d07ba..HEAD -- backend/app/services/db_service.py backend/app/agents/graph.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED — adding locks can cause deadlocks if not done carefully; must use `threading.Lock` and never nest locks across modules
- **Depends on**: none (this plan is a prerequisite for plan 001)
- **Category**: bug / correctness
- **Planned at**: commit `c5d07ba`, 2026-07-11

## Why this matters

Four module-level mutable dicts in `db_service.py` and one in `graph.py` are accessed by concurrent API requests without synchronization:

- `_ENGINE_CACHE` — `db_service.py:14`
- `_SOURCE_CONN_STRINGS` — `db_service.py:15`
- `_SCHEMA_CACHE` — `db_service.py:16`
- `_STALE_CACHE` — `graph.py:470`

These are read and written by `get_engine`, `execute_query`, `get_source_schema`, `sql_execution_node`, and `close_engine` — all of which can be called concurrently by FastAPI's thread pool. Missing synchronization can cause:
- Corrupted dict state from concurrent writes
- Threads seeing stale values after another thread updates a path
- Race conditions where one thread's schema-cache invalidation is overwritten by another thread's cache write

## Current state

All cache access is unprotected:

```python
# db_service.py:14-16
_ENGINE_CACHE: dict[str, Engine] = {}
_SOURCE_CONN_STRINGS: dict[str, str] = {}
_SCHEMA_CACHE: dict[str, dict] = {}

# graph.py:470
_STALE_CACHE: dict[str, list[dict]] = {}
_STALE_CACHE_MAX = 50
```

Access patterns (examples):
- `get_engine`: reads `_ENGINE_CACHE`, writes to `_ENGINE_CACHE` and `_SOURCE_CONN_STRINGS`
- `get_source_schema`: reads `_SCHEMA_CACHE`, writes to `_SCHEMA_CACHE` and `_SOURCE_CONN_STRINGS`
- `sql_execution_node`: reads and writes `_STALE_CACHE`
- `close_engine`: pops from all three `db_service.py` caches

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Typecheck | `python -c "import ast; ast.parse(open('backend/app/services/db_service.py').read()); print('OK')"` | exit 0 |
| Tests | `python -m pytest backend/final_test/ -v` | all pass |

## Repo conventions

- Use `threading.Lock` (not `RLock`) for all cache locks
- One lock per cache, not a single global lock (finer granularity = less contention)
- Use `with lock:` context manager, never `.acquire()`/`.release()`
- Import `threading` at the top of each file

## Scope

**In scope**:
- `backend/app/services/db_service.py`
- `backend/app/agents/graph.py`

**Out of scope**:
- Any other file
- Changing the cache data structures or eviction policies
- Adding a distributed cache (Redis is already available but this plan uses in-process locks)

## Git workflow

- Branch: `advisor/010-thread-safety-locks`
- Commit message: `fix: add threading locks to module-level caches`
- Do NOT push or open a PR unless instructed

## Steps

### Step 1: Add locks to `db_service.py`

Add `import threading` at the top of `backend/app/services/db_service.py`.

After the cache dict declarations at lines 14-16, add:

```python
_ENGINE_CACHE: dict[str, Engine] = {}
_SOURCE_CONN_STRINGS: dict[str, str] = {}
_SCHEMA_CACHE: dict[str, dict] = {}

_ENGINE_CACHE_LOCK = threading.Lock()
_SOURCE_CONN_STRINGS_LOCK = threading.Lock()
_SCHEMA_CACHE_LOCK = threading.Lock()
```

Now wrap each function that reads/writes these caches:

**`get_engine` (line 202)** — add lock around cache read/write:

```python
def get_engine(source_id: str, conn_string: str) -> Engine:
    normalized_conn_string = _normalize_conn_string_for_sync(conn_string)
    with _ENGINE_CACHE_LOCK:
        cached = _ENGINE_CACHE.get(source_id)
        if cached is not None and _SOURCE_CONN_STRINGS.get(source_id) == normalized_conn_string:
            return cached
    # If conn_string changed, invalidate schema cache for this source
    with _SOURCE_CONN_STRINGS_LOCK:
        if _SOURCE_CONN_STRINGS.get(source_id, None) is not None and _SOURCE_CONN_STRINGS[source_id] != normalized_conn_string:
            _SCHEMA_CACHE.pop(source_id, None)
            logger.info("Schema cache invalidated for source_id=%s: conn_string changed", source_id)
    connect_args = {"timeout": 30} if _is_sqlite_conn_string(normalized_conn_string) else {}
    engine = create_engine(normalized_conn_string, connect_args=connect_args)
    if engine.dialect.name == "oracle":
        engine.dialect.exclude_tablespaces = ()
    if engine.dialect.name == "sqlite":
        _set_sqlite_pragmas(engine)
    with _ENGINE_CACHE_LOCK:
        _ENGINE_CACHE[source_id] = engine
    with _SOURCE_CONN_STRINGS_LOCK:
        _SOURCE_CONN_STRINGS[source_id] = normalized_conn_string
    return engine
```

**`get_source_schema` (line 395)** — add lock around cache check and write:

```python
def get_source_schema(source_id: str) -> dict:
    conn_string = _SOURCE_CONN_STRINGS.get(source_id)
    if conn_string is None:
        raise HTTPException(status_code=404, detail="Data source not found")
    # ... (path resolution code unchanged) ...
    
    with _SCHEMA_CACHE_LOCK:
        if source_id in _SCHEMA_CACHE:
            return _SCHEMA_CACHE[source_id]
    
    try:
        # ... (inspector code unchanged) ...
        with _SCHEMA_CACHE_LOCK:
            _SCHEMA_CACHE[source_id] = result
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed schema fetch for source_id=%s", source_id)
        raise HTTPException(status_code=500, detail=f"Failed to fetch schema: {str(exc)}")
```

**`close_engine` (line 344)** — add locks:

```python
def close_engine(source_id: str) -> None:
    with _ENGINE_CACHE_LOCK:
        engine = _ENGINE_CACHE.pop(source_id, None)
    if engine is not None:
        try:
            engine.dispose()
        except Exception:
            logger.exception("Failed to dispose engine for source_id=%s", source_id)
    with _SOURCE_CONN_STRINGS_LOCK:
        _SOURCE_CONN_STRINGS.pop(source_id, None)
    with _SCHEMA_CACHE_LOCK:
        _SCHEMA_CACHE.pop(source_id, None)
```

**`_ensure_sqlite_path_resolved` (line 222)** — lock around `_SOURCE_CONN_STRINGS` write:

```python
    if found_path != db_path:
        normalized_path = os.path.abspath(found_path)
        with _SOURCE_CONN_STRINGS_LOCK:
            _SOURCE_CONN_STRINGS[source_id] = f"sqlite:///{normalized_path}"
        return f"sqlite:///{normalized_path}"
```

Note: `_SOURCE_CONN_STRINGS` reads outside locks (like `conn_string = _SOURCE_CONN_STRINGS.get(source_id)` in `get_source_schema`) are intentionally non-blocking — reading a stale-but-valid path is acceptable since the path is re-resolved on each call. Only writes need synchronization.

### Step 2: Add lock to `graph.py` for `_STALE_CACHE`

Add `import threading` at the top of `backend/app/agents/graph.py`.

After `_STALE_CACHE_MAX = 50` (line 471), add:

```python
_STALE_CACHE_LOCK = threading.Lock()
```

In `sql_execution_node`, wrap the cache read and write sections:

```python
def sql_execution_node(state: AgentState, db_service: DBService) -> dict:
    # ... (validation code unchanged) ...
    
    ck = _cache_key(state.sql, state.source_id)
    if not is_write:
        with _STALE_CACHE_LOCK:
            if ck in _STALE_CACHE:
                logger.debug("SQL cache hit for: %s", state.sql[:60])
                return {"query_results": list(_STALE_CACHE[ck]), "success": True}

    try:
        results = execute_sql(db_service, state.sql, state.source_id) or []
        if not is_write:
            with _STALE_CACHE_LOCK:
                if len(_STALE_CACHE) >= _STALE_CACHE_MAX:
                    _STALE_CACHE.pop(next(iter(_STALE_CACHE)))
                _STALE_CACHE[ck] = list(results)
        else:
            from app.services.db_service import _SCHEMA_CACHE
            _SCHEMA_CACHE.pop(state.source_id, None)
        return {"query_results": results, "success": True}
    except Exception as e:
        # ... (error handling unchanged) ...
```

### Step 3: Run tests

```bash
python -m pytest backend/final_test/ -v
```

## Test plan

No new tests needed for this change — it's an infrastructure improvement that existing tests validate (no regression). If you want to be thorough, add a concurrency test to `backend/final_test/test_units.py`:

```python
import threading

def test_cache_lock_basic():
    """Verify that cache locks don't block simple operations."""
    from app.services.db_service import _ENGINE_CACHE_LOCK, _SOURCE_CONN_STRINGS_LOCK, _SCHEMA_CACHE_LOCK
    for lock in [_ENGINE_CACHE_LOCK, _SOURCE_CONN_STRINGS_LOCK, _SCHEMA_CACHE_LOCK]:
        with lock:
            pass  # No deadlock on simple acquire/release
```

## Done criteria

ALL must hold:

- [ ] `python -c "import ast; ast.parse(open('backend/app/services/db_service.py').read()); print('OK')"` exits 0
- [ ] `python -c "import ast; ast.parse(open('backend/app/agents/graph.py').read()); print('OK')"` exits 0
- [ ] `python -m pytest backend/final_test/ -v` exits 0, all tests pass
- [ ] `db_service.py` has `_ENGINE_CACHE_LOCK`, `_SOURCE_CONN_STRINGS_LOCK`, `_SCHEMA_CACHE_LOCK` declared and used in `get_engine`, `get_source_schema`, `close_engine`, `_ensure_sqlite_path_resolved`
- [ ] `graph.py` has `_STALE_CACHE_LOCK` declared and used in `sql_execution_node`
- [ ] No nested lock acquisitions between `db_service.py` and `graph.py`
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated to DONE

## STOP conditions

Stop and report back if:

- The code at the locations in "Current state" doesn't match the excerpts.
- A step's verification fails twice after a reasonable fix attempt.
- The fix appears to require touching an out-of-scope file.
- You discover any lock is already present (don't add a second).
- You discover a lock ordering issue (e.g., `_ENGINE_CACHE_LOCK` acquired inside `_SCHEMA_CACHE_LOCK`).

## Maintenance notes

- These are in-process locks only. If the app scales to multiple processes, the caches become per-process and locks are still correct (but cached data is per-process).
- Never acquire locks from `db_service.py` and `graph.py` in the same call chain — they are independent caches.
- If a distributed cache (Redis) is added later, these locks can be removed in favor of Redis's own atomic operations.
