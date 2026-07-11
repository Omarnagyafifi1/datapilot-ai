# Plan 004: Fix `_is_mock_output` length check

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. Run every verification command and confirm the expected result
> before moving to the next step. If anything in the "STOP conditions" section
> occurs, stop and report — do not improvise. When done, update the status
> row for this plan in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat c5d07ba..HEAD -- backend/app/agents/graph.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `c5d07ba`, 2026-07-11

## Why this matters

`_is_mock_output` at `graph.py:376` rejects any LLM output longer than 500 characters as "mock output". For modification operations (INSERT/UPDATE/DELETE), legitimate multi-line SQL can easily exceed 500 characters. This causes the graph to reset the SQL to empty string and fail the query. The 500-char limit has no justification — it was presumably meant to catch LLMs that ramble, but it also catches legitimate complex queries.

## Current state

`backend/app/agents/graph.py:376-384`:

```python
def _is_mock_output(output: str) -> bool:
    upper = output.strip().upper()
    if upper.startswith("MOCK") or "MOCK RESPONSE" in upper:
        return True
    if len(output) > 500:           # <-- This is the bug
        return True
    if "INSERT statement" in output or "UPDATE statement" in output or "DELETE statement" in output:
        return True
    return False
```

This function is called by `modification_sql_node` at line 405:
```python
if _is_mock_output(sql):
    logger.warning(...)
    sql = ""
```

The intent is to detect LLMs that return placeholder text like "MOCK RESPONSE" or "Here is the INSERT statement" instead of actual SQL. The length check was presumably meant to catch verbose mock responses, but 500 chars is too low for real SQL.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Typecheck | `python -c "import ast; ast.parse(open('backend/app/agents/graph.py').read()); print('OK')"` | exit 0 |
| Tests | `python -m pytest backend/final_test/ -v` | all pass |

## Scope

**In scope**:
- `backend/app/agents/graph.py`

**Out of scope**:
- Any other file

## Git workflow

- Branch: `advisor/004-mock-output-length`
- Commit message: `fix: remove overly aggressive length check in _is_mock_output`
- Do NOT push or open a PR unless instructed

## Steps

### Step 1: Remove the len(output) > 500 check

In `backend/app/agents/graph.py`, locate `_is_mock_output` (line 376-384). Remove the `if len(output) > 500: return True` line.

The function after the change should be:

```python
def _is_mock_output(output: str) -> bool:
    upper = output.strip().upper()
    if upper.startswith("MOCK") or "MOCK RESPONSE" in upper:
        return True
    if "INSERT statement" in output or "UPDATE statement" in output or "DELETE statement" in output:
        return True
    return False
```

**Verify**: `grep -n "len(output) > 500" backend/app/agents/graph.py` returns no matches.

### Step 2: Run tests

```bash
python -m pytest backend/final_test/ -v
```

## Test plan

Add a test to `backend/final_test/test_units.py`:

```python
def test_is_mock_output():
    from app.agents.graph import _is_mock_output
    
    # Legitimate long SQL should NOT be flagged as mock
    long_sql = "INSERT INTO employees (name, salary, department, hire_date, email, phone, address, city, country) VALUES ('John', 50000, 'Engineering', '2024-01-15', 'john@co.com', '555-0100', '123 Main St', 'NYC', 'USA')"
    assert not _is_mock_output(long_sql)
    
    # Actual mock patterns should still be caught
    assert _is_mock_output("MOCK RESPONSE")
    assert _is_mock_output("This is an INSERT statement")
```

## Done criteria

ALL must hold:

- [ ] `python -c "import ast; ast.parse(open('backend/app/agents/graph.py').read()); print('OK')"` exits 0
- [ ] `python -m pytest backend/final_test/ -v` exits 0, all tests pass
- [ ] `grep -n "len(output) > 500" backend/app/agents/graph.py` returns no matches
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated to DONE

## STOP conditions

Stop and report back if:

- The code at the locations in "Current state" doesn't match the excerpts.
- A step's verification fails twice after a reasonable fix attempt.
- `_is_mock_output` has moved to a different file.

## Maintenance notes

- If the `_is_mock_output` function is ever extended, keep the length-based heuristic out of it — the mock phrases are sufficient for detection.
- The "MOCK" and "INSERT statement" checks are still somewhat fragile, but they're well-understood heuristics. If the LLM changes behavior, these may need updating.
