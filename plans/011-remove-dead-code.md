# Plan 011: Remove dead code

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat c5d07ba..HEAD -- backend/app/agents/prompts.py backend/app/services/schema_service.py backend/app/services/approval_store.py backend/app/agents/graph.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: tech-debt
- **Planned at**: commit `c5d07ba`, 2026-07-11

## Why this matters

Three pieces of dead code add maintenance burden:
1. `ANSWER_PROMPT` in `prompts.py:138` — a prompt template for natural-language answers that no graph node ever uses
2. `SchemaService` in `schema_service.py` — an async schema fetcher that is injected into `AgentGraph` but bypassed by `fetch_schema_context` (which does `del schema_service` and calls `db_service.get_source_schema()` directly)
3. `approval_store.py` — a Redis-backed TTL store for approval payloads that is never imported or referenced

Dead code misleads new developers, wastes maintenance attention, and adds unnecessary files to the project.

## Current state

**ANSWER_PROMPT** — `backend/app/agents/prompts.py:138-150`:

```python
ANSWER_PROMPT = """
You are a professional data analyst. Your task is to provide a clear, natural-language answer to the user's question using ONLY the provided database results.

### Inputs
- User Question: {question}
- Raw Database Results: {results}

### Rules
1. DIRECTNESS: Provide a concise, highly readable answer...
...
"""
```

No `grep -rn "ANSWER_PROMPT" backend/` should return any match except the definition itself.

**SchemaService** — `backend/app/services/schema_service.py` (full file, ~89 lines):
An async schema fetcher that uses `DataSourceConfig`, `create_async_engine`, etc. It's never called by the graph — `schema_tools.py:6` does `del schema_service`.

**approval_store.py** — `backend/app/services/approval_store.py` (full file, ~26 lines):
A Redis-backed store for approval payloads. `grep -rn "approval_store" backend/` should return no matches except the file itself.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Typecheck | `python -c "import ast; ast.parse(open('backend/app/agents/prompts.py').read()); print('OK')"` | exit 0 |
| Tests | `python -m pytest backend/final_test/ -v` | all pass |

## Scope

**In scope**:
- `backend/app/agents/prompts.py` — remove `ANSWER_PROMPT`
- `backend/app/services/schema_service.py` — remove the file (and clean up any imports)
- `backend/app/services/approval_store.py` — remove the file (and clean up any imports)

**Out of scope**:
- Changing any behavior or logic
- Removing the `SchemaService` parameter from `AgentGraph.__init__` (that would change the class interface; other code may depend on it via `deps.py`)

## Git workflow

- Branch: `advisor/011-remove-dead-code`
- Commit message: `chore: remove dead code (ANSWER_PROMPT, SchemaService, approval_store)`
- Do NOT push or open a PR unless instructed

## Steps

### Step 1: Remove `ANSWER_PROMPT` from `prompts.py`

In `backend/app/agents/prompts.py`, delete the `ANSWER_PROMPT` block (lines 138-150, from `ANSWER_PROMPT = """` to the closing `"""`).

**Verify**: `grep -rn "ANSWER_PROMPT" backend/` should return no matches.

### Step 2: Remove `approval_store.py`

Delete the file `backend/app/services/approval_store.py`.

**Verify**: `Test-Path "backend/app/services/approval_store.py"` should return False.

### Step 3: Remove `schema_service.py` and clean up imports

Delete the file `backend/app/services/schema_service.py`.

Then find and clean up any remaining imports of `SchemaService`:

1. `backend/app/agents/graph.py` — has `from app.services.schema_service import SchemaService` at line 44. Since the file is removed, remove this import.
2. `backend/app/api/deps.py` — likely imports `SchemaService`. Remove the import there too.
3. `backend/app/agents/graph.py` — the `__init__` method takes `schema_service: SchemaService` as a parameter. Since other code (via `deps.py`) constructs the `AgentGraph` and passes this parameter, we should keep the parameter but remove the type hint import — change the type hint to `Any` or `object`:

In `graph.py:44`, remove `from app.services.schema_service import SchemaService`.

In `graph.py:828`, change `schema_service: SchemaService` to `schema_service: Any` (since `Any` is already imported at line 8).

**Verify**: `grep -rn "schema_service" backend/` should show only the `schema_service` parameter in `graph.py` and references that use it. `grep -rn "SchemaService" backend/` should return no matches.

### Step 4: Run typecheck and tests

```bash
python -c "import ast; ast.parse(open('backend/app/agents/prompts.py').read()); print('OK')"
```

```bash
python -m pytest backend/final_test/ -v
```

## Test plan

No new tests needed. Run existing tests to confirm nothing is broken:

```bash
python -m pytest backend/final_test/ -v
```

## Done criteria

ALL must hold:

- [ ] `python -c "import ast; ast.parse(open('backend/app/agents/prompts.py').read()); print('OK')"` exits 0
- [ ] `python -m pytest backend/final_test/ -v` exits 0, all tests pass
- [ ] `grep -rn "ANSWER_PROMPT" backend/` returns no matches
- [ ] `Test-Path "backend/app/services/schema_service.py"` returns False
- [ ] `Test-Path "backend/app/services/approval_store.py"` returns False
- [ ] `grep -rn "SchemaService" backend/` returns no matches
- [ ] `grep -rn "schema_service" backend/app/agents/graph.py` only shows the parameter and `self.schema_service` references (still needed for the wiring)
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated to DONE

## STOP conditions

Stop and report back if:

- The code at the locations in "Current state" doesn't match the excerpts.
- A step's verification fails twice after a reasonable fix attempt.
- The fix appears to require touching an out-of-scope file.
- You discover that `SchemaService` or `ANSWER_PROMPT` IS used somewhere (different from this analysis). Run `grep -rn "ANSWER_PROMPT\|SchemaService\|approval_store" backend/` to confirm.

## Maintenance notes

- The `schema_service` parameter in `AgentGraph.__init__` is kept because the `deps.py` factory constructs and passes it. Removing it would be a larger refactor of the dependency injection.
- If a future feature needs async schema fetching, a new service should be built — not resurrected from `schema_service.py` — because the async implementation was never tested or used.
