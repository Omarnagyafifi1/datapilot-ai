# Plan 024: Add SQL Injection Protection to /query/page Endpoint

> **Executor instructions**: Follow step by step. Verify each command. Stop and report on mismatch.
>
> **Drift check**: `git diff --stat 0d59108..HEAD -- backend/app/api/routes.py backend/app/agents/graph.py backend/app/agents/tools/sql_tool.py`

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: MED
- **Depends on**: none
- **Category**: security
- **Planned at**: commit `0d59108`, 2026-07-12

## Why this matters

The `/query/page` endpoint (POST) accepts raw SQL from the client, strips trailing semicolons and existing LIMIT clauses, appends pagination LIMIT/OFFSET, and executes it directly via `db_service.execute_query()`. There is no keyword validation, no SELECT-structure check, and no parameterization of the user's SQL portion. An attacker can submit arbitrary DML/DDL through this endpoint.

## Current state

In `backend/app/api/routes.py:198-223`, the pagination endpoint:

```python
@router.post("/query/page")
def query_page_endpoint(
    payload: QueryPageRequest,
    data_source_service: DataSourceService = Depends(get_data_source_service),
) -> dict[str, Any]:
    try:
        data_source_service.get_conn_string(payload.source_id)
        clean_sql = payload.sql.rstrip(';').strip()
        clean_sql = re.sub(r'\s*LIMIT\s+\d+(\s+OFFSET\s+\d+)?\s*$', '', clean_sql, flags=re.IGNORECASE)
        dialect = db_service.DBService(source_id=payload.source_id).get_dialect()
        limit_sql = clean_sql
        offset = (payload.page - 1) * payload.page_size
        if dialect in ("sqlite", "postgresql", "mysql"):
            limit_sql = f"{clean_sql} LIMIT {payload.page_size} OFFSET {offset}"
        ...
        results = db_service.execute_query(limit_sql, payload.source_id)
        return _resp(success=True, message="Page fetched", data={"rows": results, "page": payload.page})
```

The `graph.py:655-677` has `_validate_sql_keywords()` that blocks DDL/DML keywords. It is used in `sql_execution_node` (line 700) but the pagination endpoint bypasses it entirely.

The `_validate_sql_keywords` function at graph.py:655:
```python
def _validate_sql_keywords(sql: str, intent: str) -> str | None:
    forbidden = {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE", "REPLACE", "EXEC", "EXECUTE"}
    if intent == "INQUIRE":
        upper = sql.upper()
        for kw in forbidden:
            pattern = re.compile(r'\b' + kw + r'\b')
            if pattern.search(upper):
                return f"SQL contains forbidden keyword: {kw}"
    return None
```

## Scope

**In scope:**
- `backend/app/api/routes.py` — add SELECT validation and keyword check to pagination endpoint

**Out of scope:**
- `backend/app/agents/graph.py` — the `_validate_sql_keywords` function is already correct; do not modify it
- Changing the `QueryPageRequest` model
- Adding authentication (separate product decision)

## Git workflow

- Branch: `advisor/024-sql-injection-pagination`
- Commit message: `fix: validate SQL structure and keywords in /query/page endpoint`

## Steps

### Step 1: Import `_validate_sql_keywords` and add validation to pagination endpoint

Add to `routes.py` imports (near the top):
```python
from app.agents.graph import _validate_sql_keywords
```

After the `clean_sql` cleanup line and before the dialect block, add:
```python
        # Validate SQL structure — must be a SELECT query for read-only pagination
        validation_error = _validate_sql_keywords(clean_sql, "INQUIRE")
        if validation_error:
            return _resp(success=False, message=validation_error, data=None, status_code=400)

        stripped = clean_sql.lstrip().upper()
        if not stripped.startswith("SELECT") or "INTO" in stripped.split()[0:10]:
            return _resp(success=False, message="Only SELECT queries are allowed", data=None, status_code=400)
```

**Verify**: `python -m py_compile backend/app/api/routes.py` — exit 0. `pytest backend/final_test/ -v` — all pass.

### Step 2: Update test to cover pagination validation

In `backend/final_test/test_integrations.py`, add a test that sends a malicious SQL to `/query/page` and asserts 400 response:

```python
def test_query_page_rejects_malicious_sql(client):
    resp = client.post("/api/query/page", json={
        "sql": "SELECT 1; DROP TABLE products; --",
        "source_id": "test",
        "page": 1,
        "page_size": 10
    })
    assert resp.status_code == 400
    data = resp.json()
    assert not data.get("success", True)
```

**Verify**: `pytest backend/final_test/ -v -k test_query_page_rejects_malicious_sql` — passes.

## Test plan

Add the `test_query_page_rejects_malicious_sql` test to `backend/final_test/test_integrations.py`. Also verify the existing pagination still works with valid SQL.

## Done criteria

- [ ] `_validate_sql_keywords` imported from `graph` into `routes.py`
- [ ] Keyword check runs before SQL execution in pagination endpoint
- [ ] Non-SELECT SQL is rejected with 400
- [ ] New integration test passes
- [ ] `pytest backend/final_test/ -v` — all 20 pass
- [ ] No files outside in-scope list modified
- [ ] `plans/README.md` status row updated

## STOP conditions

- `_validate_sql_keywords` is not importable (renamed or moved) → find its current location
- The existing tests for pagination break → the validation is too aggressive; loosen the check

## Maintenance notes

The `_validate_sql_keywords` function in graph.py is shared — if its signature changes, update the import here. The SELECT-only check should not break legitimate pagination of `SELECT` queries with CTEs (WITH clauses) — the `stripped.startswith("SELECT")` check allows `WITH ... SELECT ...` patterns.
