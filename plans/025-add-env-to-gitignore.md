# Plan 025: Add .env to .gitignore

> **Executor instructions**: One step. Verify and stop on mismatch.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: security
- **Planned at**: commit `0d59108`, 2026-07-12

## Why this matters

`.env` files at both repo root and `backend/.env` contain live API keys (OpenRouter, Gemini, Groq, LangSmith, Azure OpenAI, encryption key). The `.gitignore` has no `.env` entry — one `git add -A` commits all keys to git history, where they are permanently burned. Adding `.env` to `.gitignore` is a one-line safety gate.

## Current state

`D:\me\depi\datapilot-ai\.gitignore` (34 lines) has entries for Python cache, Node modules, IDE files, OS files, backend logs, and test artifacts — but no `.env` entry. Files currently not tracked (confirmed via `git ls-files .env`), but there's no protection against accidental staging.

## Scope

**In scope:** `.gitignore` at repo root only

**Out of scope:** Any other files, `.env.example`, `.env` files themselves

## Steps

### Step 1: Add `.env` entry to `.gitignore`

Append `.env` on a new line at the end of `.gitignore`.

**Verify**: `Select-String -Path ".gitignore" -Pattern "^\.env$"` — matches. `git check-ignore .env backend/.env` — both return the file path (confirmed ignored).

## Done criteria

- [ ] `.env` appears as a line in `.gitignore`
- [ ] `git check-ignore .env` returns `.env`
- [ ] `git check-ignore backend/.env` returns `backend/.env`

## STOP conditions

- `.gitignore` doesn't exist at repo root
- `.env` is already present in `.gitignore`

## Maintenance notes

None — one-line, permanent fix.
