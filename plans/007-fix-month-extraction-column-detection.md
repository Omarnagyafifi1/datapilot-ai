# Plan 007: Fix month extraction column detection to include date-like names

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat c5d07ba..HEAD -- backend/app/services/db_service.py`
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

The `_rewrite_month_extraction_filters` function (and the helper `month_replacement` used by both rewrite functions) only rewrites month filters when the column name contains the literal substring "date". Columns named `created_at`, `purchase_ts`, `transaction_dt`, `updated_time`, `order_timestamp`, etc. are not matched, so month extractions on these columns are silently not rewritten for SQLite. This produces incorrect SQL that SQLite cannot evaluate correctly.

## Current state

In `backend/app/services/db_service.py`, the `month_replacement` function at line 91:

```python
def month_replacement(column_expr: str, month_value: str, original: str) -> str:
    normalized_column_name = _strip_identifier_quotes(column_expr).lower()
    if "date" not in normalized_column_name:
        return original
    month_number = month_value.zfill(2)
    return f"SUBSTR({column_expr}, 4, 2) = '{month_number}'"
```

The check `"date" not in normalized_column_name` is too narrow. It should also match:
- `_at` suffix (created_at, updated_at, deleted_at)
- `_dt` suffix (transaction_dt, eff_dt)
- `_ts` suffix (purchase_ts, event_ts)
- `_time` suffix (updated_time, start_time)
- `timestamp` in name (order_timestamp, TIMESTAMP)
- `date` in name (date_of_hire — already matched)

The same check appears in `_rewrite_month_name_like_filters` at line 76.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Typecheck | `python -c "import ast; ast.parse(open('backend/app/services/db_service.py').read()); print('OK')"` | exit 0 |
| Tests | `python -m pytest backend/final_test/ -v` | all pass |

## Scope

**In scope**:
- `backend/app/services/db_service.py`

**Out of scope**:
- Any other file

## Git workflow

- Branch: `advisor/007-month-extraction-columns`
- Commit message: `fix: broaden date column detection to include time-stamped column names`
- Do NOT push or open a PR unless instructed

## Steps

### Step 1: Add a helper function for date-column detection

In `backend/app/services/db_service.py`, add a helper function near the top of the module or near the other utility functions:

```python
def _is_date_column(column_expr: str) -> bool:
    """Check if a column name suggests it holds date/time data."""
    name = _strip_identifier_quotes(column_expr).lower()
    date_indicators = ["date", "_at", "_dt", "_ts", "_time", "timestamp"]
    return any(indicator in name for indicator in date_indicators)
```

### Step 2: Replace the inline "date" checks

Find the `month_replacement` function at line 91-97 and change:

```python
    normalized_column_name = _strip_identifier_quotes(column_expr).lower()
    if "date" not in normalized_column_name:
        return original
```

to:

```python
    if not _is_date_column(column_expr):
        return original
```

Find the same pattern in `_rewrite_month_name_like_filters` at line 75-77:

```python
        normalized_column_name = _strip_identifier_quotes(column_expr).lower()
        if "date" not in normalized_column_name:
            return match.group(0)
```

Change to:

```python
        if not _is_date_column(column_expr):
            return match.group(0)
```

**Verify**: `grep -n '"date" not in normalized_column_name' backend/app/services/db_service.py` returns no matches (both instances replaced).

### Step 3: Run tests

```bash
python -m pytest backend/final_test/ -v
```

## Test plan

Add tests to `backend/final_test/test_units.py`:

```python
def test_is_date_column():
    from app.services.db_service import _is_date_column
    assert _is_date_column("date_of_hire")
    assert _is_date_column("created_at")
    assert _is_date_column("updated_at")
    assert _is_date_column("purchase_dt")
    assert _is_date_column("event_ts")
    assert _is_date_column("start_time")
    assert _is_date_column("order_timestamp")
    assert not _is_date_column("employee_name")
    assert not _is_date_column("salary")
    assert not _is_date_column("department_id")

def test_rewrite_month_extraction_non_date_column():
    from app.services.db_service import _rewrite_month_extraction_filters
    # created_at should now be matched
    sql = "SELECT * FROM orders WHERE STRFTIME('%m', created_at) = '5'"
    rewritten = _rewrite_month_extraction_filters(sql)
    assert "SUBSTR(created_at, 4, 2) = '05'" in rewritten
```

## Done criteria

ALL must hold:

- [ ] `python -c "import ast; ast.parse(open('backend/app/services/db_service.py').read()); print('OK')"` exits 0
- [ ] `python -m pytest backend/final_test/ -v` exits 0, all tests pass
- [ ] `grep -rn '"date" not in normalized_column_name' backend/app/services/db_service.py` returns no matches
- [ ] `grep -rn "_is_date_column" backend/app/services/db_service.py` shows the new helper and two call sites
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated to DONE

## STOP conditions

Stop and report back if:

- The code at the locations in "Current state" doesn't match the excerpts.
- A step's verification fails twice after a reasonable fix attempt.
- The fix appears to require touching an out-of-scope file.
- The `_strip_identifier_quotes` function has been renamed or moved.

## Maintenance notes

- If new date/time column naming patterns emerge (e.g., `_dttm`, `_datetime`), add them to the `date_indicators` list in `_is_date_column`.
- The function uses a simple `any(indicator in name for indicator in ...)` check. This is intentionally broad to avoid missing columns. False positives (non-date columns matching the indicators) are harmless since the SUBSTR rewrite is only applied when a LIKE or EXTRACT on the column contains a month reference — if the column doesn't contain DD/MM/YYYY text, the query might still work or fail on its own merits without this rewrite.
