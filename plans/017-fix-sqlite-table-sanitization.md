# Plan 017: Fix SQLite table name sanitization mismatch

> **Executor instructions**: Follow this plan step by step. Run every
> verification command before moving to the next step. If anything in the
> "STOP conditions" section occurs, stop and report.
>
> **Drift check**: `git diff --stat cea37b2..HEAD -- backend/app/services/import_providers/sqlite_provider.py`
> If changed, compare excerpts against live code; mismatch = STOP.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: HIGH
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit cea37b2, 2026-07-11

## Why this matters

When importing a SQLite database, the frontend sends `selected_tables` using `t.name` (sanitized table names), but the backend at line 250 compares using `t.original_name` (unsanitized). If a table has hyphens, spaces, or dots in its name, the sanitized name (`my-table` → `my_table`) never matches the original name, and the table is silently excluded from the import. The user selects it in the UI, the import "succeeds," but the table is missing.

## Current state

`backend/app/services/import_providers/sqlite_provider.py:248-250`:
```python
        table_names = [t.original_name for t in preview.tables]
        if options.selected_tables:
            table_names = [t for t in table_names if t in options.selected_tables]
```

The `options.selected_tables` list comes from the frontend, which sends `t.name` — the sanitized name (see the `_sanitize_table_name` method at line 70 of the same file, which replaces non-alphanumeric characters with underscores).

Meanwhile, `t.original_name` is the raw table name from the database (e.g., `"my-table"`), which never matches the sanitized `"my_table"` sent by the frontend.

The fix: compare both sides using the same normalization (either always use sanitized names, or always use original names but have the frontend match).

## Scope

**In scope**:
- `backend/app/services/import_providers/sqlite_provider.py`

**Out of scope**:
- `backend/app/services/import_providers/csv_provider.py` — separate provider
- Frontend — the frontend already sends `t.name` (sanitized), which is correct

## Git workflow

- Branch: `advisor/017-fix-sqlite-table-sanitization`
- Commit message: `fix: normalize SQLite table name comparison in import filter`

## Commands you will need

| Purpose   | Command                  | Expected on success |
|-----------|--------------------------|---------------------|
| Python syntax | `python -m py_compile backend/app/services/import_providers/sqlite_provider.py` | exit 0 |

## Steps

### Step 1: Read the sanitize_table_name method

Read `sqlite_provider.py` and find the `_sanitize_table_name` method (should be around line 70). Note the exact logic — it likely replaces non-alphanumeric characters (except underscores) with underscores and lowercases. The fix needs to apply this same normalization to the comparison.

### Step 2: Build a set of sanitized selected table names

In the `import_data` method, at line 248-250, change the filter to normalize the comparison:

```python
        table_names = [t.original_name for t in preview.tables]
        if options.selected_tables:
            sanitized_selected = {self._sanitize_table_name(t) for t in options.selected_tables}
            table_names = [t for t in table_names if self._sanitize_table_name(t) in sanitized_selected]
```

This applies `_sanitize_table_name` to both sides of the comparison, ensuring that:
- A table named `"my-table"` in the DB (original_name) sanitizes to `"my_table"`
- The frontend's `selected_tables` entry `"my_table"` (already sanitized by the frontend) stays `"my_table"` after re-sanitization
- They match correctly

**Important**: verify that `self._sanitize_table_name()` is idempotent (applying it twice gives the same result) — read the method to confirm. If it uses regex replace of non-alphanumeric chars, it should be idempotent.

**Verify**:
- Read the modified lines — confirm the comparison uses `self._sanitize_table_name()` on both sides
- `python -m py_compile backend/app/services/import_providers/sqlite_provider.py` — exit 0

## Test plan

- `python -m py_compile` — exit 0
- Manual: upload a SQLite DB with a table named `"sales-data"` or `"2024 data"` → the frontend should show it as `"sales_data"` / `"2024_data"` → select it → the import should include the table

## Done criteria

- [ ] `sqlite_provider.py` — the table name filter at lines 248-250 normalizes both sides with `_sanitize_table_name`
- [ ] `python -m py_compile backend/app/services/import_providers/sqlite_provider.py` exits 0

## STOP conditions

- Code at cited locations doesn't match excerpts
- `_sanitize_table_name` is a static method, not an instance method (if so, call `SQLiteProvider._sanitize_table_name(t)` instead)
- `_sanitize_table_name` exists under a different name (confirm by reading the file)
- Verification fails twice

## Maintenance notes

- The `CSVProvider` in `csv_provider.py` has a similar `_sanitize_column_name` method but uses `_sanitize_column_name` for table name sanitization too (line 122-124). That's a separate bug (finding #7) — not in scope for this plan.
