# Plan 012: Fix frontend suggestions flow (queryService + QueryPage)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat cea37b2..HEAD -- frontend/src/services/queryService.js frontend/src/query/QueryPage.jsx frontend/src/query/components/`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit cea37b2, 2026-07-11

## Why this matters

The `queryService.js` layer silently drops the `suggestions` array from every backend response — it only uses `data.suggestions` as a fallback for `insights`, meaning users never see "Next Steps" in the QueryPage flow. Additionally, the `QueryPage` imports 3 component files that don't exist on disk, making that route completely broken. Fixing both means suggestions actually display and the query page renders.

## Current state

### 1. queryService.js drops suggestions

`frontend/src/services/queryService.js` has 3 methods — `generate()`, `execute()`, `approve()` — each returning an object with an `insights` field that uses `data.suggestions` as a fallback, but no dedicated `suggestions` field:

```js
// Line 16 — generate()
return {
  sql: data.sql || data.generated_sql || resp.data.answer || '',
  results: data.results || data.rows || null,
  insights: data.insights || data.suggestions || data.explanation || [],
  requiresApproval: data.requires_approval || false,
  threadId: data.thread_id || null,
};
```

Same pattern at lines 37 (execute) and 58 (approve).

### 2. QueryPage imports nonexistent components

`frontend/src/query/QueryPage.jsx:2-5`:
```jsx
import QueryInput from './components/QueryInput';
import SQLViewer from './components/SQLViewer';
import ResultsTable from './components/ResultsTable';
import InsightBox from './components/InsightBox';
```

Only `SQLViewer.jsx` exists in `frontend/src/query/components/`. `QueryInput.jsx`, `ResultsTable.jsx`, and `InsightBox.jsx` do not exist anywhere in the project.

### 3. ChatInterface.jsx handles suggestions

`frontend/src/components/ChatInterface.jsx` already works with suggestions correctly — it uses `doc.suggestions` in the `ResultVisualizer`. The fix should align queryService with what ChatInterface expects.

## Commands you will need

| Purpose   | Command                  | Expected on success |
|-----------|--------------------------|---------------------|
| Typecheck | `npx tsc --noEmit`       | exit 0, no errors   |
| Lint      | `npx eslint frontend/src/services/queryService.js` | exit 0 |

## Scope

**In scope** (the only files you should modify):
- `frontend/src/services/queryService.js`
- `frontend/src/query/QueryPage.jsx`

**Out of scope** (do NOT touch):
- `frontend/src/components/ChatInterface.jsx` — already working, must stay unchanged
- Any backend files
- Any CSS or styling files

## Git workflow

- Branch: `advisor/012-fix-frontend-suggestions-flow`
- Commit message style: `fix: add suggestions field to queryService return objects`

## Steps

### Step 1: Add `suggestions` field to all three queryService methods

In `frontend/src/services/queryService.js`, add `suggestions: data.suggestions || []` to the return object of each method (`generate`, `execute`, `approve`). Also clean up the `insights` fallback chain — remove `data.suggestions` and `data.explanation` from the `insights` fallback so insights only come from `data.insights`.

The `generate` method (lines 13-19) should become:
```js
return {
  sql: data.sql || data.generated_sql || resp.data.answer || '',
  results: data.results || data.rows || null,
  insights: data.insights || [],
  suggestions: data.suggestions || [],
  requiresApproval: data.requires_approval || false,
  threadId: data.thread_id || null,
};
```

The `execute` method (lines 35-41):
```js
return {
  results: data.results || data.rows || [],
  insights: data.insights || [],
  suggestions: data.suggestions || [],
  requiresApproval: data.requires_approval || false,
  threadId: data.thread_id || null,
};
```

The `approve` method (lines 56-62):
```js
return {
  results: data.results || data.rows || [],
  insights: data.insights || [],
  suggestions: data.suggestions || [],
  requiresApproval: data.requires_approval || false,
  threadId: data.thread_id || null,
  message: resp.data.message || '',
};
```

**Verify**:
- Read `frontend/src/services/queryService.js` — confirm all 3 return objects have `suggestions: data.suggestions || []`
- Confirm `insights` no longer has `data.suggestions` or `data.exploration` in any fallback chain
- Run `npx eslint frontend/src/services/queryService.js` — exit 0

### Step 2: Remove nonexistent component imports from QueryPage

In `frontend/src/query/QueryPage.jsx`, replace the 4 import lines with only the imports that exist:

Remove:
```jsx
import QueryInput from './components/QueryInput';
import SQLViewer from './components/SQLViewer';
import ResultsTable from './components/ResultsTable';
import InsightBox from './components/InsightBox';
```

Replace with only imports that exist. Check what's actually available:
```jsx
import SQLViewer from './components/SQLViewer';
```

The other 3 components (`QueryInput`, `ResultsTable`, `InsightBox`) were never created. Look at how the file uses these components:

1. `QueryInput` (line 105) — remove this usage; replace the JSX with a simple textarea
2. `ResultsTable` (line 128) — render a basic HTML table instead
3. `InsightBox` (line 133) — render the insights directly or use an inline fallback

For each usage, replace the missing component with inline JSX that reads the same props. Use the existing `base` Tailwind classes already in the codebase (e.g. `glass`, `rounded-2xl`, `border-border`).

**Verify**: Run `npx eslint frontend/src/query/QueryPage.jsx` — exit 0. Run `npx tsc --noEmit` — exit 0.

## Test plan

No existing test infrastructure for frontend. Manual verification:
- Open the app in a browser
- Navigate to the Query page (the route that renders QueryPage)
- Confirm no runtime errors in the console
- Run a query and confirm suggestions appear in the "Next Steps" panel

## Done criteria

- [ ] `frontend/src/services/queryService.js` — all 3 methods return `suggestions: data.suggestions || []`
- [ ] `frontend/src/services/queryService.js` — `insights` no longer falls back to `data.suggestions` or `data.explanation`
- [ ] `frontend/src/query/QueryPage.jsx` — no imports of nonexistent component files
- [ ] `npx tsc --noEmit` exits 0
- [ ] `npx eslint frontend/src/services/queryService.js` exits 0

## STOP conditions

Stop and report back (do not improvise) if:
- The code at the locations in "Current state" doesn't match the excerpts
- A step's verification fails twice after a reasonable fix attempt
- You discover `QueryPage.jsx` uses the missing components in ways that can't be replaced with simple inline JSX

## Maintenance notes

- The ChatInterface.jsx is the canonical query surface; QueryPage is a legacy route that should eventually be removed entirely. This plan makes it functional without requiring full refactoring.
- If additional query flows are added in the future, they should follow the ChatInterface pattern, not the QueryPage pattern.
