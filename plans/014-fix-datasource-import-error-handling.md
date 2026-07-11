# Plan 014: Fix datasource import error handling

> **Executor instructions**: Follow this plan step by step. Run every
> verification command before moving to the next step. If anything in the
> "STOP conditions" section occurs, stop and report.
>
> **Drift check**: `git diff --stat cea37b2..HEAD -- backend/app/services/import_providers/csv_provider.py backend/app/api/routes.py`
> If changed, compare excerpts against live code; mismatch = STOP.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: MEDIUM
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit cea37b2, 2026-07-11

## Why this matters

Two bugs combine to create a confusing user experience: (1) when CSV metadata saving fails, the import "succeeds" but the dataset is invisible — the user sees a success toast but nothing appears in the library; (2) `.xlsx`/`.xls`/`.json` files pass extension validation but no provider handles them, producing a generic "Unsupported file format" error instead of a clear upfront rejection.

## Current state

### Bug A: Metadata save failure silently orphans datasource

`backend/app/services/import_providers/csv_provider.py:263-264`:
```python
        except Exception as e:
            logger.exception("Failed to save dataset metadata during CSV import: %s", e)
```

The exception is logged but NOT re-raised. The `import_data()` method continues to line 275 and returns a success `ImportResult`. The datasource was registered (via `_register_datasource` at line 241), but the `dataset_metadata` row is missing. The Datasets page queries `dataset_metadata`, so the datasource is invisible.

### Bug B: Allowed extensions mismatch

`backend/app/api/routes.py:111`:
```python
_ALLOWED_UPLOAD_EXTENSIONS = {".csv", ".db", ".sqlite", ".sqlite3", ".xlsx", ".xls", ".json"}
```

But `_get_provider()` at lines 103-106 only handles `.csv`, `.db`, `.sqlite`, `.sqlite3`. Files with `.xlsx`, `.xls`, or `.json` pass the validation check but then hit `_get_provider()` which returns `None`, triggering a confusing "Unsupported file format" error at the call site.

## Scope

**In scope**:
- `backend/app/services/import_providers/csv_provider.py`
- `backend/app/api/routes.py`

**Out of scope**:
- `backend/app/services/import_providers/sqlite_provider.py` — similar but separate bug; fix only CSV here
- Any frontend files

## Git workflow

- Branch: `advisor/014-fix-datasource-import-error-handling`
- Commit message: `fix: roll back datasource on metadata failure, restrict allowed extensions`

## Commands you will need

| Purpose   | Command                  | Expected on success |
|-----------|--------------------------|---------------------|
| Python syntax check | `python -m py_compile backend/app/services/import_providers/csv_provider.py` | exit 0 |
| Python syntax check | `python -m py_compile backend/app/api/routes.py` | exit 0 |

## Steps

### Step 1: Roll back datasource on metadata save failure

In `backend/app/services/import_providers/csv_provider.py`, modify the exception handler at lines 263-264. Instead of just logging, call `delete_source(source_uuid)` to roll back the datasource registration, then re-raise the exception.

Add an import for `delete_source` at the top of the file (check if it's already imported from `app.services.data_source_service`). The function is `delete_source` in `app.services.data_source_service`.

Replace the current handler:
```python
        except Exception as e:
            logger.exception("Failed to save dataset metadata during CSV import: %s", e)
```

With:
```python
        except Exception as e:
            logger.exception("Failed to save dataset metadata during CSV import: %s", e)
            # Roll back the datasource registration so we don't orphan it
            try:
                from app.services.data_source_service import delete_source
                delete_source(source_uuid)
            except Exception:
                logger.exception("Failed to roll back datasource after metadata failure")
            raise CSVValidationError(f"Failed to save dataset metadata: {str(e)}")
```

Note: You need `source_uuid` in scope — it's defined at line 241 (`source_uuid = await self._register_datasource(dataset_name, db_path)`). Confirm it's accessible.

Also check whether `CSVValidationError` is imported (line ~12 or similar) — it should be. Verify by reading the imports.

**Verify**:
- Read the modified file and confirm:
  1. The except block calls `delete_source(source_uuid)` before the raise
  2. It re-raises as `CSVValidationError`
  3. The `delete_source` import is present (either imported at top of file or inside the except block)
- `python -m py_compile backend/app/services/import_providers/csv_provider.py` — exit 0

### Step 2: Restrict allowed upload extensions

In `backend/app/api/routes.py`, remove `.xlsx`, `.xls`, and `.json` from `_ALLOWED_UPLOAD_EXTENSIONS` at line 111:

```python
_ALLOWED_UPLOAD_EXTENSIONS = {".csv", ".db", ".sqlite", ".sqlite3"}
```

This way, users uploading unsupported formats get a clear "File type not allowed" message at validation time, listing only the formats that actually work.

**Verify**:
- Read line 111 and confirm only `.csv`, `.db`, `.sqlite`, `.sqlite3` remain
- `python -m py_compile backend/app/api/routes.py` — exit 0

## Test plan

No existing test suite for these modules. After changes:
- `python -m py_compile` on both files — must exit 0
- Manual verification: try uploading a `.xlsx` file → should get "File type 'xlsx' not allowed" before any provider lookup
- Manual verification: if metadata save fails during CSV import, the datasource should be rolled back

## Done criteria

- [ ] `csv_provider.py` — metadata failure rolls back the datasource and re-raises as `CSVValidationError`
- [ ] `routes.py` — `_ALLOWED_UPLOAD_EXTENSIONS` only contains `.csv`, `.db`, `.sqlite`, `.sqlite3`
- [ ] `python -m py_compile` exits 0 on both files

## STOP conditions

- Code at cited locations doesn't match excerpts
- `delete_source` doesn't exist or has a different signature in `data_source_service.py`
- The `source_uuid` variable is renamed or not accessible in the except block
- Validation fails twice

## Maintenance notes

- If `.xlsx` support is added later, add a provider first, then add the extension back to `_ALLOWED_UPLOAD_EXTENSIONS`.
- The same metadata-rollback pattern should be applied to `sqlite_provider.py` in a follow-up plan if needed.
