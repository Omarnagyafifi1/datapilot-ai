# Plan 026: Enforce Programmatic Row Limit in SQL Execution

> **Executor instructions**: Follow step by step. Verify each command. Stop and report on drift.
>
> **Drift check**: `git diff --stat 0d59108..HEAD -- backend/app/services/db_service.py backend/app/agents/prompts.py`

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: MED
- **Depends on**: none
- **Category**: perf / bug
- **Planned at**: commit `0d59108`, 2026-07-12

## Why this matters

`db_service.py:394` uses `result.mappings().fetchmany(1000)` which silently caps ALL queries at 1000 rows at the Python driver level. Two problems: (1) queries with `LIMIT 2000` or no LIMIT get truncated but the UI says 1000 rows are complete; (2) pagination (`/query/page`) re-fetches using the original SQL without the driver cap — page 2 answers show rows 1001+ that were never in the initial response, causing data inconsistency. The fix: remove the driver-level cap and programmatically append `LIMIT 1000` to SQL that has no LIMIT clause.

## Current state

In `backend/app/services/db_service.py:394`:
```python
return [dict(row) for row in result.mappings().fetchmany(1000)]
```

In `backend/app/services/db_service.py:366-396`, the `execute_query` function:
```python
def execute_query(sql, source_id, timeout=15):
    ...
    conn = get_connection(source_id)
    result = conn.execute(text(sql))
    return [dict(row) for row in result.mappings().fetchmany(1000)]
```

The SQL prompt at `prompts.py:34` says `LIMIT {max_rows}` but only "when appropriate" — exempting aggregation queries and ORDER BY queries. The LLM can (and does) generate queries without LIMIT.

## Scope

**In scope:**
- `backend/app/services/db_service.py` — `execute_query` function

**Out of scope:**
- `backend/app/agents/prompts.py` — the prompt suggestion stays as-is
- Pagination endpoint (`/query/page`) — already handles its own LIMIT; fix 024 adds validation
- Any changes to the semantic cache (plan 022) or graph logic

## Git workflow

- Branch: `advisor/026-enforce-programmatic-row-limit`
- Commit message: `fix: replace fetchmany(1000) with programmatic LIMIT enforcement`

## Steps

### Step 1: Replace `fetchmany(1000)` with `.all()` and add LIMIT enforcement

Replace:
```python
return [dict(row) for row in result.mappings().fetchmany(1000)]
```
with:
```python
rows = [dict(row) for row in result.mappings().all()]
return rows
```

Then, BEFORE the `result = conn.execute(...)` line, add a LIMIT-enforcement step for non-pagination queries:

```python
# Enforce a default LIMIT if none exists (prevents full table scans)
_DEFAULT_LIMIT = 5000
upper_sql = sql.strip().upper().rstrip(";").strip()
has_limit = bool(re.search(r'\bLIMIT\s+\d+', upper_sql))
has_top = upper_sql.startswith("SELECT TOP")
has_fetch = bool(re.search(r'\bFETCH\s+(FIRST|NEXT)\s+\d+', upper_sql))
if not has_limit and not has_top and not has_fetch:
    sql = f"{sql.rstrip(';')} LIMIT {_DEFAULT_LIMIT}"
```

Add `import re` at the top of `db_service.py` if not already present.

**Verify**: `python -m py_compile backend/app/services/db_service.py` — exit 0. `pytest backend/final_test/ -v` — all pass.

### Step 2: Verify protection doesn't break pagination

The pagination endpoint at `routes.py` sends SQL that may already have a LIMIT from the prompt, but the endpoint strips it before adding its own. The `has_limit` check above detects LIMIT clauses — since the endpoint receives the raw SQL (potentially with LIMIT), the enforcement won't add a second LIMIT. The endpoint then strips the LIMIT and adds pagination correctly.

No code change needed for this step — just verification.

**Verify**: Run the integration tests: `pytest backend/final_test/ -v` — all pass.

## Test plan

No new tests in this plan. Existing 19 tests must continue to pass. The change is in `db_service.py` which unit tests cover partially.

## Done criteria

- [ ] `fetchmany(1000)` replaced with `.all()`
- [ ] Programmatic LIMIT enforcement added (limit 5000) when SQL lacks LIMIT/TOP/FETCH
- [ ] `import re` present in `db_service.py`
- [ ] `pytest backend/final_test/ -v` — all pass
- [ ] No files outside in-scope list modified
- [ ] `plans/README.md` status row updated

## STOP conditions

- The `execute_query` function signature or behavior has changed since `0d59108`
- The integration tests use queries that depend on the 1000-row cap (unlikely — test data is small)

## Maintenance notes

The `_DEFAULT_LIMIT = 5000` can be promoted to a config setting in `config.py` if different deployments need different limits. The regex-based LIMIT detection checks for `LIMIT <number>` — it won't detect `LIMIT ?` (parameterized) or `LIMIT @count` (variable-based), but these patterns don't appear in LLM-generated SQL.
