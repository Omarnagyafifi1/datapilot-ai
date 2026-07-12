# Plan 033: Fix `_safe_json_parse` to use bracket-depth matching

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

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `80a9d6f`, 2026-07-12

## Why this matters

`_safe_json_parse` uses a heuristic — find the first `[` or `{` and try that bracket type — but it determines the end bracket with `text.rfind(close_char)`, which finds the *last* closing bracket in the entire text. If the LLM output contains stray brackets in prose (e.g., dates, parenthetical asides, markdown formatting like `[link]`, or `{` in string values), the extracted candidate is garbage JSON that fails to parse. Both `insight_node` and `suggestion_node` then fall back to their failure modes — a misleading "No data to analyze" message or empty suggestions list — even when the LLM returned a perfectly valid JSON array embedded in conversational text.

## Current state

`_safe_json_parse` at `backend/app/agents/graph.py:100-141`:

```python
def _safe_json_parse(text: str) -> Any | None:
    text = text.strip()

    m = re.search(r'```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # Find the first array and object brackets
    first_square = text.find('[')
    first_curly = text.find('{')
    
    # Try array first if it appears before an object, otherwise try object first
    if first_square != -1 and (first_curly == -1 or first_square < first_curly):
        braces = ('[', ']')
    else:
        braces = ('{', '}')
    
    for open_char, close_char in [braces, ('{', '}') if braces != ('{', '}') else ('[', ']')]:
        start = text.find(open_char)
        end = text.rfind(close_char)
        if start != -1 and end > start:
            candidate = text[start:end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                fixed = re.sub(r",\s*}", "}", candidate)
                fixed = re.sub(r",\s*\]", "]", fixed)
                fixed = re.sub(r"(?<!\\)'", '"', fixed)
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    return None
```

**The bug**: `text.rfind(close_char)` finds the last `]` or `}` in the ENTIRE text, not the matching bracket. For input like:
```
Here are some insights [some note]: [{"ar":"text","en":"text"}]
```
`text.rfind(']')` returns the position of the `]` in `[some note]`, not the one at the end of the array. The candidate becomes `[some note]: [{"ar":"text","en":"text"}]` — invalid JSON.

**Code conventions**: The existing pattern uses a helper + fallback chain. Match the style: keep `_safe_json_parse` as a standalone function, use the same try/except/fix strategy, do not modify other functions.

## Commands you will need

| Purpose   | Command                  | Expected on success |
|-----------|--------------------------|---------------------|
| Test      | `cd backend && pytest final_test/test_graph.py -v --tb=short` | All 10 pass |
| Test all  | `cd backend && pytest final_test/ -v --tb=short` | All 30 pass |
| Lint      | `ruff check backend/app/agents/graph.py --no-fix` | exit 0 |

## Scope

**In scope** (the only files you should modify):
- `backend/app/agents/graph.py`

**Out of scope** (do NOT touch, even though they look related):
- `backend/app/agents/prompts.py` — prompts are fine; the LLM ignoring them is a parsing problem
- Any other file in `backend/app/` or `frontend/`

## Steps

### Step 1: Replace the bracket-matching heuristic with a proper depth-based extractor

Replace lines 110–134 inside `_safe_json_parse` (the entire "Find the first array..." block). The new logic should:

1. Scan the text character by character to find the first `[` or `{` that begins a valid JSON structure.
2. Track bracket depth to find the matching closing bracket (`]` or `}`).
3. Extract the substring from the opening to the matching closing bracket.
4. Try `json.loads` on it (with the same fix attempts as the current code for trailing commas and single quotes).
5. If that fails, try the *other* bracket type (array vs object).

Specifically, implement a helper function inside `_safe_json_parse` or inline:

```python
def _extract_bracketed(text: str, open_ch: str, close_ch: str) -> str | None:
    """Extract the first properly bracket-matched substring from text."""
    depth = 0
    start = None
    in_string = False
    escape = False
    for i, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == open_ch:
            if depth == 0:
                start = i
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0 and start is not None:
                return text[start:i + 1]
    return None
```

Then in `_safe_json_parse`, replace the `first_square`/`first_curly` + `text.find`/`text.rfind` block with:

```python
    # Use bracket-depth matching for robustness
    for open_char, close_char in [('[', ']'), ('{', '}')]:
        candidate = _extract_bracketed(text, open_char, close_char)
        if candidate is None:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            fixed = re.sub(r",\s*}", "}", candidate)
            fixed = re.sub(r",\s*\]", "]", fixed)
            fixed = re.sub(r"(?<!\\)'", '"', fixed)
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass
```

This handles:
- Conversational text before the JSON: the depth scanner finds the first opening bracket and its matching close.
- Stray brackets in prose: they don't have matching depth-0 counterparts, so they're ignored.
- Nested objects/arrays inside strings: the `in_string` flag prevents treating brackets inside string values as structure.
- Escaped characters: the `escape` flag handles `\"` correctly.

**Verify**: `cd backend && python -c "
from app.agents.graph import _safe_json_parse

# Test 1: bare array
r = _safe_json_parse('[{\"ar\":\"a\",\"en\":\"b\"}]')
assert isinstance(r, list) and r[0]['ar'] == 'a', f'bare array failed: {r}'

# Test 2: conversational text before
r = _safe_json_parse('Here are insights: [{\"ar\":\"a\",\"en\":\"b\"}]')
assert isinstance(r, list), f'conversational prefix failed: {r}'

# Test 3: stray bracket in prose
r = _safe_json_parse('Results [showing 36 rows]: [{\"ar\":\"a\",\"en\":\"b\"}]')
assert isinstance(r, list), f'stray bracket failed: {r}'

# Test 4: nested braces in string value
r = _safe_json_parse('[{\"ar\":\"about {stuff}\",\"en\":\"about {stuff}\"}]')
assert isinstance(r, list), f'nested in string failed: {r}'

# Test 5: markdown-wrapped (stage 1)
r = _safe_json_parse('\`\`\`json\\n[{\"ar\":\"a\",\"en\":\"b\"}]\\n\`\`\`')
assert isinstance(r, list), f'markdown failed: {r}'

# Test 6: bare dict
r = _safe_json_parse('{\"insights\": [{\"ar\":\"a\",\"en\":\"b\"}]}')
assert isinstance(r, dict), f'bare dict failed: {r}'

# Test 7: single-quote fix
r = _safe_json_parse(\"[{'ar':'a','en':'b'}]\")
assert isinstance(r, list), f'single quote failed: {r}'

# Test 8: completely unparseable
r = _safe_json_parse('this is not json at all')
assert r is None, f'noise should return None: {r}'

print('All _safe_json_parse tests passed')
"
` → prints "All _safe_json_parse tests passed"

### Step 2: Run the full test suite

**Verify**: `cd backend && pytest final_test/ -v --tb=short` → all 30 pass

## Test plan

- No new test file needed. The step 1 verification command includes inline characterization tests for the specific edge cases.
- The existing test suite (`test_graph.py`) includes `test_parse_insights_markdown_wrapped` and `test_parse_insights_raw_text` which exercise `_safe_json_parse` through `_parse_insights`. Verify these still pass.

## Done criteria

All must hold:

- [ ] `cd backend && pytest final_test/test_graph.py -v --tb=short` — all 10 pass
- [ ] `cd backend && pytest final_test/ -v --tb=short` — all 30 pass
- [ ] `ruff check backend/app/agents/graph.py --no-fix` — exit 0
- [ ] `_safe_json_parse` correctly handles: bare arrays, conversational prefix, stray brackets in prose, brackets inside string values, single-quoted JSON, markdown-wrapped JSON, bare dicts, and completely unparseable text (returns None).
- [ ] No files outside `backend/app/agents/graph.py` are modified (`git status`)

## STOP conditions

Stop and report back (do not improvise) if:

- The code at `backend/app/agents/graph.py:100-141` doesn't match the excerpts above (another session already modified `_safe_json_parse`).
- The `_extract_bracketed` helper produces wrong results for any of the inline tests in step 1.
- A test outside `test_graph.py` fails that you didn't cause (pre-existing CI environment issue).

## Maintenance notes

The `_extract_bracketed` function is a general-purpose bracket-matcher that respects string escaping and string boundaries. If future LLM providers return JSON with different quoting styles or escape patterns, this function may need updating. The fallback chain (stage 1: markdown extraction; stage 2: bracket matching; stage 3: whole-text parse) should be preserved.
