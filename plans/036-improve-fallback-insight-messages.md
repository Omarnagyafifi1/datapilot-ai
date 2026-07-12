# Plan 036: Improve fallback insight message when rows exist

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

- **Priority**: P3
- **Effort**: XS
- **Risk**: LOW
- **Depends on**: none
- **Category**: dx
- **Planned at**: commit `80a9d6f`, 2026-07-12

## Why this matters

When the insight LLM call fails but there ARE query results, the fallback message says "No data to analyze" / "لا توجد بيانات كافية للتحليل" — which is factually wrong (there IS data; the LLM just couldn't generate insights from it). This misleads users into thinking their query returned nothing when it actually returned 36 rows. A more accurate message improves trust and debuggability.

## Current state

`_fallback_insights` at `backend/app/agents/graph.py:80-86`:

```python
def _fallback_insights() -> list[dict[str, str]]:
    return [
        {
            "ar": "لا توجد بيانات كافية للتحليل", 
            "en": "No data to analyze"
        }
    ]
```

This function is called in two places:
1. `insight_node` (line 865) — when query_results is empty OR when LLM parse fails
2. `_post_process_node` (line 1061) — exception handler for insight_node

When called from the empty-results path (line 851-853), the message "No data to analyze" is accurate. When called from the parse-failure path (line 864-865), it's misleading because rows exist.

**Code conventions**: The existing pattern uses a standalone function returning a list of dicts with `ar`/`en` keys. Keep the return type and structure unchanged.

## Commands you will need

| Purpose   | Command                  | Expected on success |
|-----------|--------------------------|---------------------|
| Test      | `cd backend && pytest final_test/test_graph.py -v --tb=short` | All 10 pass |
| Test all  | `cd backend && pytest final_test/ -v --tb=short` | All 30 pass |
| Lint      | `ruff check backend/app/agents/graph.py --no-fix` | exit 0 |

## Scope

**In scope**:
- `backend/app/agents/graph.py` — only `_fallback_insights` at line 80-86

**Out of scope**:
- Changes to `insight_node` logic or flow
- Other fallback messages

## Steps

### Step 1: Split fallback into two variants

Rename the existing `_fallback_insights` to `_fallback_insights_no_data` and create a new `_fallback_insights_llm_failed`. Update the call sites in `insight_node` to use the appropriate one.

Find `_fallback_insights` at line 80:

```python
def _fallback_insights() -> list[dict[str, str]]:
    return [
        {
            "ar": "لا توجد بيانات كافية للتحليل", 
            "en": "No data to analyze"
        }
    ]
```

Replace with:

```python
def _fallback_insights_no_data() -> list[dict[str, str]]:
    return [
        {"ar": "لا توجد بيانات كافية للتحليل", "en": "No data to analyze"}
    ]


def _fallback_insights_llm_failed() -> list[dict[str, str]]:
    return [
        {"ar": "تعذر إنشاء رؤى من البيانات", "en": "Could not generate insights from the data"}
    ]
```

Then update the two call sites in `insight_node` (line 850-865):

Line 853: `return {"insights": _fallback_insights()}` → `return {"insights": _fallback_insights_no_data()}`

Line 865: `return {"insights": _fallback_insights()}` → `return {"insights": _fallback_insights_llm_failed()}`

Also update the exception handler in `_post_process_node` (line 1061):

`results["insights"] = _fallback_insights()` → `results["insights"] = _fallback_insights_llm_failed()`

**Verify**: `cd backend && python -c "
from app.agents.graph import _fallback_insights_no_data, _fallback_insights_llm_failed

r1 = _fallback_insights_no_data()
assert r1[0]['en'] == 'No data to analyze', f'no_data failed: {r1}'

r2 = _fallback_insights_llm_failed()
assert r2[0]['en'] == 'Could not generate insights from the data', f'llm_failed failed: {r2}'

print('Fallback functions verified')
"
` → prints "Fallback functions verified"

### Step 2: Run the full test suite

**Verify**: `cd backend && pytest final_test/ -v --tb=short` → all 30 pass

## Test plan

- Existing tests `test_insight_node_empty_results` and `test_insight_node_parse_failure` verify the fallback paths. After the rename, they should still pass because they import `_fallback_insights` — you must also update the imports in the test file.
- In `backend/final_test/test_graph.py`, remove the old import alias and add both new import names.

## Done criteria

All must hold:

- [ ] `cd backend && pytest final_test/test_graph.py -v --tb=short` — all 10 pass
- [ ] `cd backend && pytest final_test/ -v --tb=short` — all 30 pass
- [ ] `ruff check backend/app/agents/graph.py --no-fix` — exit 0
- [ ] No files outside `backend/app/agents/graph.py` and `backend/final_test/test_graph.py` are modified

## STOP conditions

Stop and report back if:

- The `_fallback_insights` function at `graph.py:80` doesn't match the excerpt.
- Any test references the old `_fallback_insights` name that you miss.

## Maintenance notes

If more fallback variants are needed in the future, consider making a single `_fallback_insights(message_ar, message_en)` factory function instead of proliferating named functions.
