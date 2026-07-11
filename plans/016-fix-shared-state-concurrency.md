# Plan 016: Fix shared state concurrency + resource cleanup

> **Executor instructions**: Follow this plan step by step. Run every
> verification command before moving to the next step. If anything in the
> "STOP conditions" section occurs, stop and report.
>
> **Drift check**: `git diff --stat cea37b2..HEAD -- backend/app/services/db_service.py backend/app/services/data_source_service.py`
> If changed, compare excerpts against live code; mismatch = STOP.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: MEDIUM
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit cea37b2, 2026-07-11

## Why this matters

Two concurrency/resource bugs: (1) `db_service.py` defines `_SOURCE_CONN_STRINGS_LOCK` and `_SCHEMA_CACHE_LOCK` but never acquires them — writes to shared caches happen without synchronization, causing race conditions under load; (2) `delete_dataset` in `data_source_service.py` deletes DB rows but never cleans up the cached engine, the SQLite `.db` file on disk, or the cached connection string — orphaned files and stale cache entries accumulate.

## Current state

### Bug A: Unused locks

`backend/app/services/db_service.py:20-22`:
```python
_ENGINE_CACHE_LOCK = threading.Lock()
_SOURCE_CONN_STRINGS_LOCK = threading.Lock()
_SCHEMA_CACHE_LOCK = threading.Lock()
```

`_ENGINE_CACHE_LOCK` is acquired at line 303 (`with _ENGINE_CACHE_LOCK:`), but `_SOURCE_CONN_STRINGS_LOCK` and `_SCHEMA_CACHE_LOCK` are never used. Writes to `_SOURCE_CONN_STRINGS` and `_SCHEMA_CACHE` happen at multiple locations without synchronization.

### Bug B: delete_dataset doesn't clean up

`backend/app/services/data_source_service.py:428-448`:
```python
def delete_dataset(id: str) -> None:
    session_local = _get_session_factory()
    session: Session = session_local()
    try:
        row = session.execute(
            select(_DATASET_METADATA.c.source_id).where(_DATASET_METADATA.c.id == id)
        ).mappings().first()
        if row:
            session.execute(delete(_DATASET_METADATA).where(_DATASET_METADATA.c.id == id))
            session.execute(delete(_DATA_SOURCES).where(_DATA_SOURCES.c.id == row["source_id"]))
            session.commit()
        else:
            session.rollback()
            raise HTTPException(status_code=404, detail="Dataset not found")
    finally:
        session.close()
```

No call to `close_engine()`, no disk file deletion, no cache cleanup. The `data_source_service.delete_source(id)` function at some other line likely has the same issue — check it too.

## Scope

**In scope**:
- `backend/app/services/db_service.py`
- `backend/app/services/data_source_service.py`

**Out of scope**:
- `backend/app/agents/graph.py` — separate concerns
- `backend/app/api/routes.py` — separate concerns
- Any frontend files

## Git workflow

- Branch: `advisor/016-fix-shared-state-concurrency`
- Commit messages per step or combined: `fix: acquire shared cache locks, clean up resources on delete`

## Commands you will need

| Purpose   | Command                  | Expected on success |
|-----------|--------------------------|---------------------|
| Python syntax | `python -m py_compile backend/app/services/db_service.py` | exit 0 |
| Python syntax | `python -m py_compile backend/app/services/data_source_service.py` | exit 0 |

## Steps

### Step 1: Acquire `_SOURCE_CONN_STRINGS_LOCK` on all writes/reads

In `backend/app/services/db_service.py`, wrap all reads and writes to `_SOURCE_CONN_STRINGS` with `with _SOURCE_CONN_STRINGS_LOCK:`. Search for every occurrence of `_SOURCE_CONN_STRINGS` in the file and protect each access.

The key locations (search the file for exact line numbers):
1. `_SOURCE_CONN_STRINGS[source_id] = conn_string` — multiple locations (upload_csv_to_sqlite, get_engine, _ensure_sqlite_path_resolved)
2. `_SOURCE_CONN_STRINGS.get(source_id)` — multiple locations (get_source_schema, _ensure_sqlite_path_resolved, get_engine)
3. `_SOURCE_CONN_STRINGS.pop(source_id, None)` — in `close_engine`

For simple single-access patterns, use `with _SOURCE_CONN_STRINGS_LOCK: value = _SOURCE_CONN_STRINGS.get(source_id)`. For the `get_engine` function which has a read-check-then-write pattern, wrap the entire check block.

**Important**: `_ENGINE_CACHE_LOCK` is already used in `get_engine` — do NOT add a second lock there that could cause deadlock. Only add `_SOURCE_CONN_STRINGS_LOCK` around accesses to `_SOURCE_CONN_STRINGS`, not `_ENGINE_CACHE`.

**Verify**: Read all occurrences of `_SOURCE_CONN_STRINGS` — each should be wrapped in `with _SOURCE_CONN_STRINGS_LOCK:`. `python -m py_compile backend/app/services/db_service.py` — exit 0.

### Step 2: Acquire `_SCHEMA_CACHE_LOCK` on all writes/reads

Same pattern as Step 1, but for `_SCHEMA_CACHE`. Search for all occurrences in `backend/app/services/db_service.py` and protect each with `with _SCHEMA_CACHE_LOCK:`.

Key locations:
1. `_SCHEMA_CACHE.get(source_id)` — in `get_source_schema` and `get_engine`
2. `_SCHEMA_CACHE[source_id] = result` — in `get_source_schema` (multiple places)
3. `_SCHEMA_CACHE.pop(source_id, None)` — in `close_engine`

**Verify**: All `_SCHEMA_CACHE` accesses are locked. `python -m py_compile` — exit 0.

### Step 3: Add resource cleanup to delete_dataset

In `backend/app/services/data_source_service.py`, modify the `delete_dataset` function to clean up caches and disk files.

After the session commit (line 443), add:
1. Call `close_engine(source_id)` from `app.services.db_service` to dispose the cached engine and remove cache entries
2. Delete the SQLite `.db` file from the local DB directory
3. Delete the uploaded source file from the upload directory

You'll need these imports:
- `from app.services.db_service import close_engine, _get_sqlite_db_dir, _get_upload_dir`
- `import os`

The cleanup code after the commit:
```python
            # Clean up caches and disk files
            try:
                from app.services.db_service import close_engine
                close_engine(row["source_id"])
            except Exception:
                logger.exception("Failed to close engine for source_id=%s", row["source_id"])
            
            try:
                from app.services.db_service import _get_sqlite_db_dir
                db_path = os.path.join(_get_sqlite_db_dir(), f"{row['source_id']}.db")
                if os.path.exists(db_path):
                    os.remove(db_path)
                    logger.info("Deleted SQLite DB file: %s", db_path)
            except Exception:
                logger.exception("Failed to delete SQLite DB file for source_id=%s", row["source_id"])
```

Also check the `delete_source` function in the same file. Read it and add the same cleanup if it's missing.

**Verify**: 
- Read `delete_dataset` — confirm engine close, DB file deletion, and upload file deletion are added
- Read `delete_source` — add same cleanup if missing
- `python -m py_compile` — exit 0

## Test plan

- `python -m py_compile` on both files — exit 0
- Manual: create a datasource, delete it via API/UI → confirm the SQLite `.db` file is removed from disk and the engine is disposed

## Done criteria

- [ ] `_SOURCE_CONN_STRINGS_LOCK` is acquired on every read/write to `_SOURCE_CONN_STRINGS`
- [ ] `_SCHEMA_CACHE_LOCK` is acquired on every read/write to `_SCHEMA_CACHE`
- [ ] `delete_dataset` calls `close_engine()` and deletes the `.db` file
- [ ] `delete_source` (if it exists) also does cleanup
- [ ] `python -m py_compile` exits 0 on both files

## STOP conditions

- Code at cited locations doesn't match excerpts
- Adding locks causes a deadlock (test by reading: do any locked sections call other functions that try to acquire the same lock? If so, use RLock instead.)
- `delete_source` has a completely different signature from what's expected
- Verification fails twice

## Maintenance notes

- The `_ENGINE_CACHE_LOCK` is already protecting the engine cache in `get_engine` — the new `_SOURCE_CONN_STRINGS_LOCK` and `_SCHEMA_CACHE_LOCK` only protect their respective caches.
- If new functions are added that read/write these caches, they must also acquire the appropriate lock.
