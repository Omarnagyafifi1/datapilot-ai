# Plan 030: Fix Arabic Character Stripping in Cache Hash

> **Executor instructions**: One function to fix. Verify with the test command.
>
> **Drift check**: `git diff --stat 0d59108..HEAD -- backend/app/agents/graph.py`

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `0d59108`, 2026-07-12

## Why this matters

The `_question_hash` function in `graph.py:57-61` uses regex `[a-zA-Z0-9_]+` which strips all non-ASCII characters — including Arabic. Every Arabic question (e.g., "كم عدد الموظفين" — "how many employees") produces zero matching tokens, resulting in `md5("")`. All Arabic questions collide to the same semantic cache key, returning wrong results.

## Current state

```python
def _question_hash(question: str) -> str:
    import hashlib
    tokens = re.findall(r"[a-zA-Z0-9_]+", question.lower())
    tokens.sort()
    return hashlib.md5(" ".join(tokens).encode()).hexdigest()[:16]
```

## Scope

**In scope:** `backend/app/agents/graph.py:59` — the regex in `_question_hash`

**Out of scope:** Any other hash or cache logic

## Steps

### Step 1: Include Arabic Unicode range in the regex

Change line 59 from:
```python
tokens = re.findall(r"[a-zA-Z0-9_]+", question.lower())
```
to:
```python
tokens = re.findall(r"[a-zA-Z0-9_\u0600-\u06FF]+", question.lower())
```

**Verify**: `python -m py_compile backend/app/agents/graph.py` — exit 0. `pytest backend/final_test/ -v` — all pass.

## Done criteria

- [ ] Regex includes `\u0600-\u06FF` range
- [ ] `_question_hash("كم عدد الموظفين")` returns a deterministic non-empty hash
- [ ] `pytest backend/final_test/ -v` — all pass
- [ ] No files outside in-scope list modified
- [ ] `plans/README.md` status row updated

## STOP conditions

- The `_question_hash` function was renamed or removed
- The regex pattern is substantially different from what's shown

## Maintenance notes

If additional Unicode scripts (Cyrillic, CJK, etc.) are needed in the future, add their ranges to the character class. The `tokens.sort()` step normalizes word order, so "employees top 10" and "top 10 employees" still collide — this is intentional for the semantic cache but should be documented if changed.
