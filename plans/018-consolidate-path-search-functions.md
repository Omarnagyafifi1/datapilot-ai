# Plan 018: Consolidate duplicate path-search functions

> **Executor instructions**: Follow this plan step by step. Run every
> verification command before moving to the next step. If anything in the
> "STOP conditions" section occurs, stop and report.
>
> **Drift check**: `git diff --stat cea37b2..HEAD -- backend/app/services/db_service.py backend/app/services/data_source_service.py`
> If changed, compare excerpts against live code; mismatch = STOP.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: MEDIUM
- **Depends on**: none
- **Category**: tech-debt
- **Planned at**: commit cea37b2, 2026-07-11

## Why this matters

Two functions exist that search for SQLite database files across common locations: `_find_sqlite_db_path` in `db_service.py` and `_find_sqlite_path_in_common_locations` in `data_source_service.py`. They use different search path lists, meaning a SQLite file found by one function may not be found by the other. This causes intermittent "file not found" errors depending on which code path resolves the path. Consolidating to a single function eliminates the inconsistency.

## Current state

### Function A: `db_service.py:463-494` — `_find_sqlite_db_path(db_path)`
Searches 10 candidate paths including CWD, CWD/backend, uploads/, app/services/uploads/, and project-root-relative paths.

### Function B: `data_source_service.py:118-145` — `_find_sqlite_path_in_common_locations(db_path)`
Searches 12 candidate paths including all of the above plus some additional backend/ variants.

Both return `str | None` and accept a `db_path: str` parameter. The unification should keep the more comprehensive search list (the one from `data_source_service.py`) and have both call sites use the same function.

## Scope

**In scope**:
- `backend/app/services/db_service.py`
- `backend/app/services/data_source_service.py`

**Out of scope**:
- Any other files
- Changes to the search logic itself (just merge, don't redesign)

## Git workflow

- Branch: `advisor/018-consolidate-path-search-functions`
- Commit message: `refactor: consolidate duplicate SQLite path-search functions`

## Commands you will need

| Purpose   | Command                  | Expected on success |
|-----------|--------------------------|---------------------|
| Python syntax | `python -m py_compile backend/app/services/db_service.py` | exit 0 |
| Python syntax | `python -m py_compile backend/app/services/data_source_service.py` | exit 0 |

## Steps

### Step 1: Read both functions

Read `_find_sqlite_db_path` in `db_service.py` (around line 463) and `_find_sqlite_path_in_common_locations` in `data_source_service.py` (around line 118). Note the search path lists in each and the `_get_project_root()` helper used.

### Step 2: Make the db_service.py function the canonical one

In `backend/app/services/db_service.py`, update `_find_sqlite_db_path` to include all the search paths that `_find_sqlite_path_in_common_locations` has but `_find_sqlite_db_path` doesn't. Read both functions and merge the search lists, keeping the union of all paths without duplicates.

The combined search path list should include all paths from both functions. Order by likelihood — most likely paths first.

### Step 3: Have data_source_service.py import the canonical function

In `backend/app/services/data_source_service.py`:
1. Remove the `_find_sqlite_path_in_common_locations` function entirely
2. Add an import at the top: `from app.services.db_service import _find_sqlite_db_path`
3. Find all call sites of `_find_sqlite_path_in_common_locations` and replace with `_find_sqlite_db_path`

Search for all references to `_find_sqlite_path_in_common_locations` in `data_source_service.py` (likely 1-2 calls) and replace each.

**Verify**:
- Read `data_source_service.py` — confirm no remaining references to `_find_sqlite_path_in_common_locations`
- `python -m py_compile backend/app/services/data_source_service.py` — exit 0
- `python -m py_compile backend/app/services/db_service.py` — exit 0

## Test plan

- `python -m py_compile` on both files — exit 0
- Manual: any operation that resolves a SQLite path (query, schema fetch, datasource connect) should work as before

## Done criteria

- [ ] `db_service.py` — `_find_sqlite_db_path` includes the union of both search lists
- [ ] `data_source_service.py` — imports `_find_sqlite_db_path` from `db_service`
- [ ] `data_source_service.py` — `_find_sqlite_path_in_common_locations` function removed
- [ ] `data_source_service.py` — all call sites use `_find_sqlite_db_path`
- [ ] `python -m py_compile` exits 0 on both files

## STOP conditions

- Code at cited locations doesn't match excerpts
- The functions have different signatures or return types
- `_find_sqlite_db_path` is not exported/accessible from `db_service.py` by the name used (it's a module-level function, so `from app.services.db_service import _find_sqlite_db_path` should work; if the leading underscore causes import issues, verify by checking if other module-private functions are imported elsewhere in the codebase)
- Verification fails twice

## Maintenance notes

- If new directories are added for SQLite storage in the future, the unified search list in `_find_sqlite_db_path` is the single place to update.
- Consider making this function public (remove leading underscore) if it becomes a widely-used utility across the codebase.
