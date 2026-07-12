# Plan 034: Add bare-dict wrapping to `_normalize_suggestions`

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 80a9d6f..HEAD -- backend/app/agents/graph.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: XS
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `80a9d6f`, 2026-07-12

## Why this matters

`_normalize_insights` wraps a bare dict into a list if it has `ar`/`en` keys (meaning a single insight returned as `{"ar":"...","en":"..."}` is accepted). But `_normalize_suggestions` does not — it only checks `payload.get("suggestions")` on a dict, which returns `None` for a bare suggestion dict, causing the suggestion to be silently dropped. This asymmetry means a perfectly valid single-suggestion LLM response returns an empty suggestions list to the user.

## Current state

`_normalize_suggestions` at `backend/app/agents/graph.py:200-238`:

```python
def _normalize_suggestions(payload: Any) -> list[dict[str, str]] | None:
    if isinstance(payload, dict):
        payload = payload.get("suggestions")

    if not isinstance(payload, list):
        return None
    # ... rest of normalization
```

Compare with `_normalize_insights` at line 144-149:

```python
def _normalize_insights(payload: Any) -> list[dict[str, str]] | None:
    if isinstance(payload, dict):
        if "ar" in payload or "en" in payload:
            payload = [payload]  # <-- wraps bare dict into list
        else:
            payload = payload.get("insights")
    # ...
```

The fix is to add the same bare-dict wrapping to `_normalize_suggestions`.

## Commands you will need

| Purpose   | Command                  | Expected on success |
|-----------|--------------------------|---------------------|
| Test      | `cd backend && pytest final_test/test_graph.py -v --tb=short` | All 10 pass |
| Test all  | `cd backend && pytest final_test/ -v --tb=short` | All 30 pass |
| Lint      | `ruff check backend/app/agents/graph.py --no-fix` | exit 0 |

## Scope

**In scope**:
- `backend/app/agents/graph.py` — only lines 200-205

**Out of scope**:
- Any other normalization or parsing logic
- Changes to prompts or message format

## Steps

### Step 1: Add bare-dict wrapping to `_normalize_suggestions`

Find this code at `backend/app/agents/graph.py:200-205`:

```python
def _normalize_suggestions(payload: Any) -> list[dict[str, str]] | None:
    if isinstance(payload, dict):
        payload = payload.get("suggestions")
```

Replace with:

```python
def _normalize_suggestions(payload: Any) -> list[dict[str, str]] | None:
    if isinstance(payload, dict):
        if "ar" in payload or "en" in payload:
            payload = [payload]
        else:
            payload = payload.get("suggestions")
```

This exactly mirrors the pattern in `_normalize_insights` (line 145-149).

**Verify**: `cd backend && python -c "
from app.agents.graph import _normalize_suggestions

# Case 1: bare dict with ar/en keys
r = _normalize_suggestions({'ar': 'سؤال؟', 'en': 'Question?'})
assert r == [{'ar': 'سؤال؟', 'en': 'Question?'}], f'bare dict failed: {r}'

# Case 2: list of dicts (normal path)
r = _normalize_suggestions([{'ar': 'سؤال؟', 'en': 'Question?'}, {'ar': 'سؤال2', 'en': 'Question2'}])
assert len(r) == 2, f'list path failed: {r}'

# Case 3: wrapped in suggestions key
r = _normalize_suggestions({'suggestions': [{'ar': 'سؤال؟', 'en': 'Question?'}]})
assert len(r) == 1, f'suggestions key failed: {r}'

# Case 4: empty list
r = _normalize_suggestions([])
assert r is None, f'empty list failed: {r}'

# Case 5: None
r = _normalize_suggestions(None)
assert r is None, f'None failed: {r}'

print('All _normalize_suggestions tests passed')
"
` → prints "All _normalize_suggestions tests passed"

### Step 2: Run the full test suite

**Verify**: `cd backend && pytest final_test/ -v --tb=short` → all 30 pass

## Test plan

- No new test file. The step 1 inline tests verify the change.
- Existing `test_graph.py` includes `test_suggestion_node_happy_path` which exercises this path indirectly.

## Done criteria

All must hold:

- [ ] `cd backend && pytest final_test/test_graph.py -v --tb=short` — all 10 pass
- [ ] `cd backend && pytest final_test/ -v --tb=short` — all 30 pass
- [ ] `ruff check backend/app/agents/graph.py --no-fix` — exit 0
- [ ] `_normalize_suggestions` wraps bare `ar`/`en` dicts into a list (same as `_normalize_insights`)
- [ ] No files outside `backend/app/agents/graph.py` are modified

## STOP conditions

Stop and report back if:

- The `_normalize_suggestions` function at `backend/app/agents/graph.py:200` doesn't match the excerpt.

## Maintenance notes

`_normalize_suggestions` and `_normalize_insights` are parallel functions. Keep them in sync — any change to normalization logic in one should be mirrored in the other. Consider extracting the common normalization loop into a shared helper if they diverge further.
