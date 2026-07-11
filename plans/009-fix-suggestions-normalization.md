# Plan 009: Fix suggestions normalization to handle missing language gracefully

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat c5d07ba..HEAD -- backend/app/agents/graph.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `c5d07ba`, 2026-07-11

## Why this matters

`_normalize_suggestions` and `_normalize_insights` are sibling functions that parse LLM JSON output into bilingual `{ar, en}` entries. But they handle partial output differently: `_normalize_insights` fills missing languages from the other (e.g. if `ar` is missing, it copies `en` to `ar`), while `_normalize_suggestions` silently drops entire entries when either language is missing. This inconsistency means the same LLM output that produces valid insights can produce empty suggestions. Users see follow-up questions disappear without explanation.

## Current state

`_normalize_insights` at `graph.py:148-164` (lenient — fills missing):

```python
        if isinstance(ar_value, str) and ar_value.strip():
            ar_value = ar_value.strip()
        else:
            ar_value = ""

        if isinstance(en_value, str) and en_value.strip():
            en_value = en_value.strip()
        else:
            en_value = ""

        if not ar_value and not en_value:
            continue

        if not ar_value:
            ar_value = en_value
        if not en_value:
            en_value = ar_value

        normalized.append({"ar": ar_value, "en": en_value})
```

`_normalize_suggestions` at `graph.py:193-206` (strict — drops on missing):

```python
        ar_value = item.get("ar")
        en_value = item.get("en")
        if not isinstance(ar_value, str) or not isinstance(en_value, str):
            continue

        ar_value = ar_value.strip()
        en_value = en_value.strip()
        if ar_value and en_value:
            normalized.append({"ar": ar_value, "en": en_value})
```

The fix: make `_normalize_suggestions` use the same fill-logic as `_normalize_insights`.

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

- Branch: `advisor/009-suggestions-normalization`
- Commit message: `fix: use lenient language-fill logic in _normalize_suggestions to match _normalize_insights`
- Do NOT push or open a PR unless instructed

## Steps

### Step 1: Align `_normalize_suggestions` with `_normalize_insights` fill-logic

In `backend/app/agents/graph.py`, find `_normalize_suggestions` (line 186). Replace the entry-processing loop (lines 193-206) with the same filling pattern used in `_normalize_insights`:

```python
def _normalize_suggestions(payload: Any) -> list[dict[str, str]] | None:
    if isinstance(payload, dict):
        payload = payload.get("suggestions")

    if not isinstance(payload, list):
        return None

    normalized: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue

        ar_value = item.get("ar")
        en_value = item.get("en")

        if isinstance(ar_value, str) and ar_value.strip():
            ar_value = ar_value.strip()
        else:
            ar_value = ""

        if isinstance(en_value, str) and en_value.strip():
            en_value = en_value.strip()
        else:
            en_value = ""

        if not ar_value and not en_value:
            continue

        if not ar_value:
            ar_value = en_value
        if not en_value:
            en_value = ar_value

        normalized.append({"ar": ar_value, "en": en_value})

    if not normalized:
        return None

    return normalized[:5]
```

**Verify**: Read the modified function and confirm it now mirrors the fill-logic from `_normalize_insights`.

### Step 2: Run tests

```bash
python -m pytest backend/final_test/ -v
```

## Test plan

Add tests to `backend/final_test/test_units.py`:

```python
def test_normalize_suggestions_handles_missing_language():
    from app.agents.graph import _normalize_suggestions

    # Single language only — should fill the other
    result = _normalize_suggestions([{"en": "Show top products?"}])
    assert result is not None
    assert len(result) == 1
    assert result[0]["en"] == "Show top products?"
    assert result[0]["ar"] == "Show top products?"  # filled from en

    # Missing both — should drop
    result = _normalize_suggestions([{"ar": "", "en": ""}])
    assert result is None or len(result) == 0
```

## Done criteria

ALL must hold:

- [ ] `python -c "import ast; ast.parse(open('backend/app/agents/graph.py').read()); print('OK')"` exits 0
- [ ] `python -m pytest backend/final_test/ -v` exits 0, all tests pass
- [ ] `_normalize_suggestions` now fills missing languages from the other (same pattern as `_normalize_insights`)
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated to DONE

## STOP conditions

Stop and report back if:

- The code at the locations in "Current state" doesn't match the excerpts.
- A step's verification fails twice after a reasonable fix attempt.
- The fix appears to require touching an out-of-scope file.

## Maintenance notes

- `_normalize_insights` and `_normalize_suggestions` now share the same filling logic. If the logic needs to change, update both.
- The `[:5]` cap on both functions is a safety net — the prompts ask for 3-5 insights and exactly 3 suggestions.
