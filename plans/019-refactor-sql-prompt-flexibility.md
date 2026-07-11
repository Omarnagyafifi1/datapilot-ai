# Plan 019: Refactor SQL prompt for flexibility — fewer hard rules, more emphasis on understanding the question

> **Executor instructions**: Follow this plan step by step. Run every
> verification command before moving to the next step.
>
> **Drift check**: `git diff --stat cea37b2..HEAD -- backend/app/agents/prompts.py backend/app/agents/nodes/sql_node.py`
> If changed, compare excerpts against live code; mismatch = STOP.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: HIGH
- **Depends on**: none
- **Category**: bug / direction
- **Planned at**: commit cea37b2, 2026-07-11

## Why this matters

The current `SQL_GENERATION_PROMPT` has 28 numbered rules covering specific edge cases (Arabic mappings, 3-JOIN order, `SELECT 1` prohibitions, etc.). This rigidity causes the model to "follow the rules" at the expense of actually understanding the user's question. The model frequently misses requested columns, ignores specific WHERE conditions, or adds/removes columns based on rules that don't apply to the current question. A simpler prompt that emphasizes **reading the question first** and **thinking step by step** produces more accurate SQL than a rulebook.

## Current state

`backend/app/agents/prompts.py` — lines 3-72 contain `SQL_GENERATION_PROMPT` with 28 numbered rules. Key problems:

1. Rules 4 and 27 both prohibit `SELECT 1` in different wording — redundant
2. Rules 5-20 are highly specific edge cases that add noise for 90% of queries
3. Rule 21 (strict schema matching) prevents fuzzy matching for legitimate synonyms
4. Rules 22 (Arabic) is a long imperative block that dominates the prompt
5. The "Thinking Process" section (lines 12-16) is good but buried after the schema context
6. Rules 24/28 contradict rule 21 — one says "map to closest table" and the other says "output ERROR if not found"

The `run_sql_node` function is at `backend/app/agents/nodes/sql_node.py` — check how it calls the prompt.

## Scope

**In scope**:
- `backend/app/agents/prompts.py` — rewrite `SQL_GENERATION_PROMPT`
- `backend/app/agents/nodes/sql_node.py` — verify prompt usage, fix if needed

**Out of scope**:
- `SQL_ADD_PROMPT`, `SQL_UPDATE_PROMPT`, `SQL_DELETE_PROMPT` — modification prompts, different concern
- `SQL_FIX_PROMPT`, `VALIDATION_PROMPT`, `INSIGHT_PROMPT`, etc. — separate prompts
- `app/agents/graph.py` — graph flow, not prompt logic

## Git workflow

- Branch: `advisor/019-refactor-sql-prompt-flexibility`
- Commit message: `refactor: simplify SQL generation prompt — emphasize question understanding over rigid rules`

## Commands you will need

| Purpose   | Command                  | Expected on success |
|-----------|--------------------------|---------------------|
| Python syntax | `python -m py_compile backend/app/agents/prompts.py` | exit 0 |
| Python syntax | `python -m py_compile backend/app/agents/nodes/sql_node.py` | exit 0 |
| Verify no broken refs | `python -c "from app.agents.prompts import SQL_GENERATION_PROMPT; print('OK')"` | exit 0, prints OK |

## Steps

### Step 1: Read the sql_node to understand how the prompt is used

Read `backend/app/agents/nodes/sql_node.py`. Find the function that builds the final prompt for SQL generation. It will do something like:
```python
prompt = SQL_GENERATION_PROMPT.format(schema=..., question=..., max_rows=...)
```

Note which format variables are used (`{schema}`, `{question}`, `{scenario_context}`, `{max_rows}`). These must all still be present in the rewritten prompt.

### Step 2: Rewrite SQL_GENERATION_PROMPT

Replace the current 28-rule prompt (lines 3-72) with a simpler, more flexible one. The new prompt should:

1. **Lead with the user's question** — the model should look at the question first, not the rules
2. **Simplify the rules** — replace 28 specific rules with ~8 general principles
3. **Keep what works**: the 4-step thinking process, the Arabic question support (but simplified)
4. **Remove contradictions**: rules 21 vs 24 vs 28 — consolidate into one "fuzzy matching" rule
5. **Remove redundant rules**: rules 4 and 27 both say "no SELECT 1"
6. **Remove overly specific edge cases**: rule 18 (3-JOIN order), rule 7 (DISTINCT rules), rule 12 (aggregate-in-SELECT), rule 15 (subquery aliases) — these constrain the model unnecessarily

Here's the suggested structure:

```
### YOUR TASK
Understand the user's question and generate the correct SQL query.

### STEP 1 — Read the Question
[question]

### STEP 2 — Map to Schema
Here is the database schema:
{schema}

Identify which tables and columns are needed.

### STEP 3 — Think Step by Step
- What columns does the user want to see? (SELECT)
- Which table(s) contain this data? (FROM)
- What filters are mentioned? (WHERE)
- Any grouping or sorting? (GROUP BY / ORDER BY)
- Any calculations? (aggregates, arithmetic)

### STEP 4 — Generate the SQL
Write the final SQL query following these principles:

**Principles (not rigid rules — use judgment):**
1. Use ONLY column and table names from the schema. Match semantically: "users" → "employees", "items" → "products".
2. Return ONLY the raw SQL — no markdown, no backticks, no explanations. End with ;
3. Query must be read-only (no INSERT/UPDATE/DELETE/DROP/ALTER).
4. For aggregation queries (COUNT, SUM, AVG, MIN, MAX): include the aggregate column in SELECT, don't add LIMIT.
5. For "top N" / "most/least" queries: use ORDER BY + LIMIT. Include all descriptive columns in SELECT.
6. For JOIN queries: include descriptive names (department name, product name), not just IDs.
7. For Arabic questions: translate the question mentally, then use the exact English column names from schema. Do NOT invent _ar column variants.
8. If the question asks for data that genuinely doesn't exist in the schema, return: SELECT 'ERROR: Data not found in schema' AS error;
9. Always end with a semicolon.
```

**Important**: Ensure all format variables used by the caller (`{schema}`, `{question}`, `{scenario_context}`, `{max_rows}`) are still present in the rewritten prompt. If `{scenario_context}` or `{max_rows}` are used, include them. Check the sql_node to confirm.

### Step 3: Remove the 24-rule `SQL_SYSTEM_MESSAGE` if used

Check if `SQL_SYSTEM_MESSAGE` (line 1) is used anywhere in `sql_node.py` or `graph.py`. If it's concatenated with `SQL_GENERATION_PROMPT`, update accordingly. If it's only the generation prompt, the system message can stay.

**Verify**:
- `python -m py_compile backend/app/agents/prompts.py` — exit 0
- `python -m py_compile backend/app/agents/nodes/sql_node.py` — exit 0
- Verify that the new prompt still contains `{schema}`, `{question}`, and any other format variables the sql_node uses

## Test plan

- `python -m py_compile` — exit 0 on both files
- Manual: run `SELECT 'test'` style queries through the app and confirm the model follows the new prompt
- BIRD eval: `python backend/scripts/eval_lightweight.py` — accuracy should not drop significantly (some regression is expected with a new prompt; this is about improving accuracy on questions the rigid prompt missed)

## Done criteria

- [ ] `SQL_GENERATION_PROMPT` rewritten with ≤10 principles instead of 28 rigid rules
- [ ] All format variables used by `sql_node.py` are still present in the prompt
- [ ] The 4-step thinking process is preserved
- [ ] Arabic question support is simplified but functional
- [ ] Contradictory rules (21 vs 24 vs 28) are consolidated
- [ ] `python -m py_compile` exits 0 on both files

## STOP conditions

- The sql_node uses format variables beyond `{schema}`, `{question}`, `{scenario_context}`, `{max_rows}` that aren't documented here
- The prompt rewrite causes format KeyError at runtime (test with `python -c "..."`)
- BIRD eval drops more than 10% (verify: run before and after)

## Maintenance notes

- The prompt is the single most impactful file for SQL accuracy. Changes should be tested against a known eval set.
- Future prompt changes should follow the same philosophy: emphasize question understanding over edge-case rules.
- Keep the Arabic support minimal — the 4-step approach (translate → map → generate) has been validated as effective.
