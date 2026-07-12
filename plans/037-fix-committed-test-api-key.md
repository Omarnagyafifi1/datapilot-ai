# Plan 037: Fix committed test API key in settings.json

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 80a9d6f..HEAD -- backend/settings.json`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P0 (blocker — breaks all LLM features)
- **Effort**: XS
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `4eb5044`, 2026-07-12

## Why this matters

`backend/settings.json` contains `"groq": "test_key"` which was committed accidentally during plan 033-036 execution. This invalid key takes precedence over the real API key in `.env` when the LLM factory resolves credentials. Every LLM call (insight generation, suggestion generation, SQL generation warmup) fails with an authentication error, causing the entire AI insights and next-steps feature to fall back to error messages. Users see empty suggestions and "Could not generate insights" despite having valid data.

## Current state

`backend/settings.json`:

```json
{
  "llm_provider": "groq",
  "model": "gpt-5-mini",
  "temperature": 0.2,
  "max_tokens": 4096,
  "api_keys": {
    "groq": "test_key",
    "openrouter": "",
    "gemini": "",
    "openai": ""
  }
}
```

The LLM factory at `backend/app/llm/factory.py:62` reads API keys from settings.json first:

```python
groq_key = _sanitize_key(api_keys.get("groq") or settings.GROQ_API_KEY)
```

Since `api_keys.get("groq")` returns `"test_key"` (truthy), the real key from `settings.GROQ_API_KEY` (loaded from `.env`) is never used. `GroqLLM` then authenticates with `"test_key"` and gets an HTTP 401 error.

## Commands you will need

| Purpose   | Command                  | Expected on success |
|-----------|--------------------------|---------------------|
| Verify    | `cd backend && python -c "from app.llm.factory import get_llm; llm = get_llm(); r=llm.generate('Say hello', max_tokens=10); print(repr(r))"` | Returns a non-empty string starting with a greeting (e.g. `'Hello!'`) |
| Lint      | `ruff check backend/ --no-fix` | exit 0 |
| Test      | `cd backend && pytest final_test/ -v --tb=short` | All 30 pass |

## Scope

**In scope** (the only files you should modify):
- `backend/settings.json` — only the `"groq"` value inside `"api_keys"`

**Out of scope**:
- Any other file in the repository
- Any change to `factory.py`, `config.py`, or `.env`
- The `.env` file itself (it's gitignored and contains the real secret)

## Step

### Step 1: Restore the empty API key in settings.json

Open `backend/settings.json` and change:

```json
    "groq": "test_key",
```

to:

```json
    "groq": "",
```

This causes `api_keys.get("groq")` to return `""` (falsy), so the factory falls through to `settings.GROQ_API_KEY` from the `.env` file.

**Verify**: `cd backend && python -c "from app.llm.factory import get_llm; llm = get_llm()"` → no exception (LLM initializes without error)

### Step 2: Verify the LLM can actually generate text

**Verify**: `cd backend && python -c "
from app.llm.factory import get_llm
llm = get_llm()
r = llm.generate('Reply with exactly one word: hello', max_tokens=10)
assert len(r) > 0, f'Empty response from LLM: {r!r}'
print(f'LLM works. Response: {r!r}')
"` → prints "LLM works. Response: 'Hello'" (or similar)

## Test plan

- No new tests needed. The existing test suite (`pytest final_test/`) validates all paths.
- The LLM verification commands in steps 1 and 2 are the regression tests for this fix.

## Done criteria

All must hold:

- [ ] `cd backend && python -c "from app.llm.factory import get_llm; llm = get_llm(); print(type(llm).__name__)"` — prints "FallbackLLM" (not "MockLLM")
- [ ] `cd backend && pytest final_test/ -v --tb=short` — all 30 pass
- [ ] `ruff check backend/ --no-fix` — exit 0
- [ ] `backend/settings.json` has `"groq": ""` instead of `"groq": "test_key"`
- [ ] No files outside `backend/settings.json` are modified

## STOP conditions

Stop and report back (do not improvise) if:

- The LLM verification in step 2 fails even after fixing the key — this means the `.env` file is missing or has an invalid key, which is a separate configuration issue.
- You discover any other `"test_key"` pattern in committed credentials (report the locations).

## Maintenance notes

The `.env` file (gitignored) is the canonical location for secrets. `settings.json` is only for runtime-configurable non-secret settings. If a future change adds a new API key to `settings.json`, ensure it defaults to `""` so the `.env` value takes precedence. The `_sanitize_key` function in `factory.py:48-54` correctly handles the precedence chain: settings.json > .env > empty.
