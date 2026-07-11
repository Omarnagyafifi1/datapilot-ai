# Plan 008: Fix query endpoint to return proper HTTP error status code

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat c5d07ba..HEAD -- backend/app/api/routes.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `c5d07ba`, 2026-07-11

## Why this matters

When the `query_endpoint` catches an exception, it returns `_resp(success=False, message=...)`. The `_resp` helper creates a `JSONResponse` which defaults to HTTP status 200. Clients relying on HTTP status codes (4xx for client errors, 5xx for server errors) will misinterpret these as successful responses. A real server error should return 500; a validation failure should return 400.

## Current state

`backend/app/api/routes.py:133-178`:

```python
@router.post("/query")
def query_endpoint(
    payload: QueryRequest,
    data_source_service: DataSourceService = Depends(get_data_source_service),
    history_service: HistoryService = Depends(get_history_service),
) -> dict:
    start_time = time.time()
    status = "SUCCESS"
    result = {}
    try:
        data_source_service.get_conn_string(payload.source_id)
        thread_id = payload.thread_id or str(uuid4())
        
        result = get_graph_orchestrator().run(...)
        if result.get("requires_approval"):
            result["message"] = "Approval required for write query."
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
        return JSONResponse(content=jsonable_encoder(result), headers=headers)
    except Exception as e:
        status = "ERROR"
        logger.exception("Query failed")
        return _resp(success=False, message=f"Query failed: {str(e)}", data=None)
    finally:
        ...
```

The `_resp` function at `routes.py:79`:

```python
def _resp(success: bool, message: str, data: dict | list | None) -> JSONResponse:
    payload = {
        "success": success,
        "message": message,
        "data": data,
    }
    headers = {
        "Access-Control-Allow-Origin": "*",
        ...
    }
    content_str = _json.dumps(payload, default=_default_serializer)
    return JSONResponse(content=_json.loads(content_str), headers=headers)
```

`JSONResponse` defaults to `status_code=200` unless specified.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Typecheck | `python -c "import ast; ast.parse(open('backend/app/api/routes.py').read()); print('OK')"` | exit 0 |
| Tests | `python -m pytest backend/final_test/ -v` | all pass |

## Scope

**In scope**:
- `backend/app/api/routes.py`

**Out of scope**:
- Any other file
- Changing the JSON response shape (clients may depend on `{"success": false, ...}`)

## Git workflow

- Branch: `advisor/008-query-endpoint-status`
- Commit message: `fix: return HTTP 500 status code on query endpoint errors`
- Do NOT push or open a PR unless instructed

## Steps

### Step 1: Add `status_code` parameter to `_resp`

Change the `_resp` function signature to accept an optional `status_code`:

```python
def _resp(success: bool, message: str, data: dict | list | None, status_code: int = 200) -> JSONResponse:
```

And pass it to `JSONResponse`:

```python
return JSONResponse(content=_json.loads(content_str), headers=headers, status_code=status_code)
```

### Step 2: Update the error call site

Change the exception handler in `query_endpoint` from:

```python
    except Exception as e:
        status = "ERROR"
        logger.exception("Query failed")
        return _resp(success=False, message=f"Query failed: {str(e)}", data=None)
```

to:

```python
    except Exception as e:
        status = "ERROR"
        logger.exception("Query failed")
        return _resp(success=False, message=f"Query failed: {str(e)}", data=None, status_code=500)
```

**Verify**: `grep -n "_resp.*success=False.*Query failed" backend/app/api/routes.py` shows the updated call with `status_code=500`.

### Step 3: Run tests

```bash
python -m pytest backend/final_test/ -v
```

Check that `test_api_explain` and other tests still pass (they test other endpoints, not the query endpoint error path).

## Test plan

The existing integration tests don't cover the error path. Add a test to `backend/final_test/test_integrations.py`:

```python
def test_query_endpoint_returns_500_on_invalid_source():
    response = client.post("/api/query", json={
        "question": "test",
        "source_id": "nonexistent-source-id"
    })
    assert response.status_code == 500
```

## Done criteria

ALL must hold:

- [ ] `python -c "import ast; ast.parse(open('backend/app/api/routes.py').read()); print('OK')"` exits 0
- [ ] `python -m pytest backend/final_test/ -v` exits 0, all tests pass
- [ ] The error path in `query_endpoint` passes `status_code=500` to `_resp`
- [ ] `_resp` accepts a `status_code` parameter and passes it to `JSONResponse`
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated to DONE

## STOP conditions

Stop and report back if:

- The code at the locations in "Current state" doesn't match the excerpts.
- A step's verification fails twice after a reasonable fix attempt.
- The fix appears to require touching an out-of-scope file.
- Any other `_resp` call site needs updating (check with `grep -rn "_resp(" backend/app/api/routes.py`).

## Maintenance notes

- Other callers of `_resp` also default to 200, which is fine for their use cases. Only the query-endpoint error path needed the 500.
- If more error paths need different status codes in the future, extend `_resp` with more `status_code` options as needed.
