# Plan 006: Fix month-name LIKE rewrite pattern

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

`_rewrite_month_name_like_filters` rewrites SQLite-incompatible date filters like `column LIKE '%May%'` into `SUBSTR(column, 4, 2) = '05'` for DD/MM/YYYY text dates. But the regex pattern only matches `LIKE '%month%'` (percent signs on both sides). LLMs can generate other valid LIKE patterns like `column LIKE 'May%'` (prefix search), `column LIKE '%-May-%'` (with hyphens), or `column LIKE '%may%'` with lowercase. These patterns are silently not rewritten, causing SQLite to return empty results or wrong data.

## Current state

`backend/app/services/db_service.py:81-84`:

```python
pattern = re.compile(
    r'(?P<column>"[^"]+"|`[^`]+`|\[[^\]]+\]|\w+)\s+LIKE\s+\'%(?P<month>[A-Za-z]+)%\'',
    re.IGNORECASE,
)
```

This requires `%` on both sides of the month name. The fix should handle:
- `LIKE '%May%'` (both sides — already handled)
- `LIKE 'May%'` (prefix)
- `LIKE '%-May-%'` (hyphen delimited)
- `LIKE 'May'` (exact — though this is usually wrong for date strings, handle it for correctness)

The `re.IGNORECASE` flag already handles the month name case-insensitivity — `[A-Za-z]` matches `may` and `May`.

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

- Branch: `advisor/006-month-like-pattern`
- Commit message: `fix: broaden month-name LIKE pattern to handle prefix and delimited variants`
- Do NOT push or open a PR unless instructed

## Steps

### Step 1: Expand the regex pattern

Change the pattern at `db_service.py:81-84` from:

```python
pattern = re.compile(
    r'(?P<column>"[^"]+"|`[^`]+`|\[[^\]]+\]|\w+)\s+LIKE\s+\'%(?P<month>[A-Za-z]+)%\'',
    re.IGNORECASE,
)
```

to:

```python
pattern = re.compile(
    r'(?P<column>"[^"]+"|`[^`]+`|\[[^\]]+\]|\w+)\s+LIKE\s+\'(?P<prefix>%?)(?P<delim>.)?(?P<month>[A-Za-z]+)(?P=delim)?(?P<suffix>%?)\'',
    re.IGNORECASE,
)
```

Wait — backreferences in character classes don't work well. Let me use a simpler approach. Change the `replace` function to accept the full match context:

Actually, the simplest correct fix: match the month name with any surrounding characters between `LIKE '...'`, then check for `%` on either side but extract the month name regardless.

Change the pattern to:

```python
pattern = re.compile(
    r'(?P<column>"[^"]+"|`[^`]+`|\[[^\]]+\]|\w+)\s+LIKE\s+\'[%\-\s]*(?P<month>[A-Za-z]+)[%\-\s]*\'',
    re.IGNORECASE,
)
```

And change the `replace` function inside `_rewrite_month_name_like_filters` to update the docstring:

```python
def _rewrite_month_name_like_filters(sql: str) -> str:
    """Rewrite Date LIKE month patterns into month-aware SQLite filtering for DD/MM/YYYY text.
    Handles '%May%', 'May%', '%-May-%', 'May' variants."""
```

This pattern matches `%`, `-`, or whitespace characters before/after the month name, making it flexible for all common LIKE patterns.

**Verify**: `grep -n "LIKE.*%?\(?P<month>" backend/app/services/db_service.py` or just read the pattern.

### Step 2: Update the replacement logic

The `replace` function in `_rewrite_month_name_like_filters` currently reads:

```python
def replace(match: re.Match[str]) -> str:
    column_expr = match.group("column")
    month_name = match.group("month").lower()
    month_number = _MONTH_NAME_TO_NUMBER.get(month_name)
    if month_number is None:
        return match.group(0)
    normalized_column_name = _strip_identifier_quotes(column_expr).lower()
    if "date" not in normalized_column_name:
        return match.group(0)
    return f"SUBSTR({column_expr}, 4, 2) = '{month_number}'"
```

This function already works correctly with the new pattern because it only reads the `column` and `month` groups — it doesn't depend on the surrounding characters. No changes needed to `replace`.

**Verify**: Read the `replace` function and confirm it only uses `column` and `month` groups.

### Step 3: Run tests

```bash
python -m pytest backend/final_test/ -v
```

## Test plan

Add tests to `backend/final_test/test_units.py` covering all LIKE patterns:

```python
def test_rewrite_month_name_like_filters_broader_patterns():
    from app.services.db_service import _rewrite_month_name_like_filters

    # Original pattern still works
    sql = "SELECT * FROM t WHERE date_col LIKE '%May%'"
    assert "SUBSTR(date_col, 4, 2) = '05'" in _rewrite_month_name_like_filters(sql)

    # Prefix search
    sql = "SELECT * FROM t WHERE date_col LIKE 'May%'"
    assert "SUBSTR(date_col, 4, 2) = '05'" in _rewrite_month_name_like_filters(sql)

    # Hyphen delimited
    sql = "SELECT * FROM t WHERE date_col LIKE '%-May-%'"
    assert "SUBSTR(date_col, 4, 2) = '05'" in _rewrite_month_name_like_filters(sql)

    # Lowercase month
    sql = "SELECT * FROM t WHERE date_col LIKE '%may%'"
    assert "SUBSTR(date_col, 4, 2) = '05'" in _rewrite_month_name_like_filters(sql)
```

## Done criteria

ALL must hold:

- [ ] `python -c "import ast; ast.parse(open('backend/app/services/db_service.py').read()); print('OK')"` exits 0
- [ ] `python -m pytest backend/final_test/ -v` exits 0, all tests pass
- [ ] The regex pattern now matches `'%May%'`, `'May%'`, `'%-May-%'`, and `'%may%'` (case-insensitive)
- [ ] `grep -n "test_rewrite_month_name_like_filters" backend/final_test/test_units.py` shows the new broader tests
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated to DONE

## STOP conditions

Stop and report back if:

- The code at the locations in "Current state" doesn't match the excerpts.
- A step's verification fails twice after a reasonable fix attempt.
- The fix appears to require touching an out-of-scope file.
- You discover the existing tests in `test_units.py` no longer pass with the new pattern.

## Maintenance notes

- The regex uses `[%\-\s]*` which matches any sequence of `%`, `-`, and whitespace around the month name. This is flexible enough for all current patterns.
- If new LIKE patterns emerge (e.g., `LIKE '%may%2024%'`), this pattern may need further expansion.
- The `_rewrite_month_extraction_filters` function is separate and handles `EXTRACT(MONTH FROM ...)` and `STRFTIME('%m', ...)` — that function has a different pattern issue covered in plan 007.
