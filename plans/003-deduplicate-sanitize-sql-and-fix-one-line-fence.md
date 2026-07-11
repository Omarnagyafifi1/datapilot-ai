# Plan 003: Deduplicate `_sanitize_sql` and fix one-line code fence edge case

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat c5d07ba..HEAD -- backend/app/agents/`
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

There are three identical copies of `_sanitize_sql` across the codebase (`graph.py:62`, `sql_node.py:27`, `sql_tool.py:19`). Any fix or improvement must be made in three places, and they have already started to diverge. Additionally, all three copies have an edge case: when the LLM returns a one-line code fence like `` ```sql SELECT * FROM foo``` ``, the function returns the SQL with backticks still attached, which breaks SQL execution.

## Current state

The three copies of `_sanitize_sql` are at:
- `backend/app/agents/nodes/sql_node.py:27-37`
- `backend/app/agents/graph.py:62-73`
- `backend/app/agents/tools/sql_tool.py:19-29`

All three are identical:

```python
def _sanitize_sql(sql: str) -> str:
    """Strip markdown code fences that LLMs sometimes add despite instructions."""
    cleaned = sql.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        # Remove opening fence (```sql or ```) and closing fence (```)
        if len(lines) >= 3 and lines[-1].strip().startswith("```"):
            lines = lines[1:-1]
        elif len(lines) >= 2 and lines[0].strip().startswith("```"):
            lines = lines[1:]
        cleaned = "\n".join(lines).strip()
    return cleaned
```

The 1-line edge case: when `cleaned` is something like `` ```sql SELECT * FROM foo``` ``, `splitlines()` returns `["```sql SELECT * FROM foo```"]` (len=1). Neither `if` branch fires (first requires `>=3`, second `>=2`), so the backticks remain.

The `graph.py:62` copy is used by `fix_sql_node` (line 565). The `sql_node.py:27` copy is used by `run_sql_node` (line 52). The `sql_tool.py:19` copy is used by the legacy LangChain tool.

## Repo conventions

- Utility functions that strip LLM output should handle all common wrapping patterns: multi-line code fences (```...```), inline code fences (`` `sql` ``), and backtick-wrapped single lines.
- Error patterns match existing style: use `logger.warning` to log unexpected LLM output, fall back gracefully.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Typecheck | `python -c "import ast; ast.parse(open('backend/app/agents/nodes/sql_node.py').read()); print('OK')"` | exit 0 |
| Tests | `python -m pytest backend/final_test/ -v` | all pass |

## Scope

**In scope**:
- `backend/app/agents/nodes/sql_node.py` — keep `_sanitize_sql` here, make it the canonical version
- `backend/app/agents/graph.py` — replace the duplicated `_sanitize_sql` with an import
- `backend/app/agents/tools/sql_tool.py` — replace the duplicated `_sanitize_sql` with an import

**Out of scope**:
- Any other files
- Changing the behavior of callers (`run_sql_node`, `fix_sql_node`, etc.)

## Git workflow

- Branch: `advisor/003-sanitize-sql-dedup`
- Commit message: `fix: deduplicate _sanitize_sql and fix one-line code fence`
- Do NOT push or open a PR unless instructed

## Steps

### Step 1: Fix the canonical `_sanitize_sql` in `sql_node.py`

In `backend/app/agents/nodes/sql_node.py`, replace the existing `_sanitize_sql` function with a version that handles the one-line edge case. The new version should also use a regex-based approach which is more robust than line-counting:

```python
def _sanitize_sql(sql: str) -> str:
    """Strip markdown code fences that LLMs sometimes add despite instructions."""
    import re
    cleaned = sql.strip()
    # Remove opening ```sql or ``` and closing ```
    cleaned = re.sub(r'^```(?:sql)?\s*', '', cleaned)
    cleaned = re.sub(r'\s*```$', '', cleaned)
    return cleaned.strip()
```

This regex handles all three cases:
- Multi-line: `` ```sql\nSELECT * FROM foo\n``` `` → `SELECT * FROM foo`
- Single-line: `` ```sql SELECT * FROM foo``` `` → `SELECT * FROM foo`
- No fences: `SELECT * FROM foo` → `SELECT * FROM foo`

**Verify**: Read the modified function and confirm the regex-based approach.

### Step 2: Import `_sanitize_sql` in `graph.py`

In `backend/app/agents/graph.py`:

1. Find the existing `_sanitize_sql` function (around line 62) and remove it entirely (lines 62-73).
2. Add an import from `sql_node.py` at the top of the file. Place it near the existing import of `run_sql_node` (line 26):
   ```python
   from app.agents.nodes.sql_node import run_sql_node, _sanitize_sql
   ```
3. Make sure the function reference `fix_sql_node` (line 565) still works — it calls `_sanitize_sql(...)`. Since `_sanitize_sql` is now imported at module level, this will work without any change to the call site.

**Verify**: `grep -n "def _sanitize_sql" backend/app/agents/graph.py` should return no matches.

### Step 3: Import `_sanitize_sql` in `sql_tool.py`

In `backend/app/agents/tools/sql_tool.py`:

1. Remove the existing `_sanitize_sql` function (lines 19-29).
2. Add an import from `sql_node.py` at the top of the file:
   ```python
   from app.agents.nodes.sql_node import _sanitize_sql
   ```
3. The existing call site at line 113 (`sql = _sanitize_sql(...)`) and line 182 will work unchanged.

**Verify**: `grep -n "def _sanitize_sql" backend/app/agents/tools/sql_tool.py` should return no matches.

### Step 4: Run tests

```bash
python -m pytest backend/final_test/ -v
```

## Test plan

The existing test suite doesn't directly test `_sanitize_sql`. Consider adding tests to `backend/final_test/test_units.py`:

```python
def test_sanitize_sql():
    from app.agents.nodes.sql_node import _sanitize_sql
    
    # Multi-line code fence
    assert _sanitize_sql("```sql\nSELECT * FROM t\n```") == "SELECT * FROM t"
    
    # Single-line code fence
    assert _sanitize_sql("```sql SELECT * FROM t```") == "SELECT * FROM t"
    
    # No fences
    assert _sanitize_sql("SELECT * FROM t") == "SELECT * FROM t"
    
    # Empty
    assert _sanitize_sql("") == ""
```

## Done criteria

ALL must hold:

- [ ] `python -c "import ast; ast.parse(open('backend/app/agents/nodes/sql_node.py').read()); print('OK')"` exits 0
- [ ] `python -m pytest backend/final_test/ -v` exits 0, all tests pass
- [ ] `grep -n "def _sanitize_sql" backend/app/agents/graph.py` returns no matches
- [ ] `grep -n "def _sanitize_sql" backend/app/agents/tools/sql_tool.py` returns no matches
- [ ] `grep -rn "from app.agents.nodes.sql_node import.*_sanitize_sql" backend/` shows 2 import lines (graph.py, sql_tool.py)
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated to DONE

## STOP conditions

Stop and report back if:

- The code at the locations in "Current state" doesn't match the excerpts.
- `sql_node.py`'s `_sanitize_sql` is no longer the canonical version.
- A step's verification fails twice after a reasonable fix attempt.
- The fix appears to require touching an out-of-scope file.

## Maintenance notes

- Future code that needs `_sanitize_sql` should import from `app.agents.nodes.sql_node` — that is now the single source of truth.
- The regex-based approach is simpler and handles more edge cases. If the LLM behavior around code fences changes significantly, revisit this function.
