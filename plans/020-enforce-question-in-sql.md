# Plan 020: Enforce User Question Is Faithfully Reflected in Generated SQL

**Priority**: P0 (critical — directly affects correctness)
**Effort**: M
**Depends on**: None

## Problem

The LLM frequently generates SQL that ignores or partially answers the user's question. Root causes:

1. **No FK metadata in schema** (`db_service.py:575–588`): `get_source_schema` only returns column name/type/nullable/primary_key. Foreign-key relationships are missing, so the LLM guesses JOIN columns — producing wrong results that don't answer the question.

2. **Contradictory Arabic column handling**: The context filter prompt (`prompts.py:200`) says "preserve all `_ar` columns", but the SQL generation prompt (`prompts.py:28`) says "Never invent `_ar` column variants". This contradiction confuses the model and causes Arabic queries to use wrong columns.

3. **Weak prompt verification**: The "Thinking Process" step 4 (`prompts.py:18`) only says "Does the SELECT clause contain ONLY the requested columns?" — there is no structured enumeration of what the user asked, so the model has no explicit checklist to verify against.

4. **Scenario context bleeds wrong columns**: `graph.py:361` and `sql_node.py:47` pass past-query SQL into the prompt — the model may copy columns from past queries that exist in the scenario memory but NOT in the current schema, causing hallucinated column references.

5. **No sample data in schema**: The schema has only column names/types — no sample values. The LLM must guess WHERE-clause values (e.g., guessing `status = 'Completed'` vs `status = 'complete'`), leading to empty results that don't answer the question.

6. **SQL max_tokens=300 is too tight**: `sql_node.py:50` — complex queries with 3+ JOINs get truncated mid-SQL, producing invalid SQL. This causes a retry (another LLM call) and often fails again.

## Solution

### 6a. Add FK metadata to schema (db_service.py)

In `get_source_schema`, after collecting columns for each table, also collect foreign keys:

```python
# After columns loop for each table_name:
fk_list = inspector.get_foreign_keys(table_name)
foreign_keys = [
    {
        "constrained_columns": fk["constrained_columns"],
        "referred_table": fk["referred_table"],
        "referred_columns": fk["referred_columns"],
    }
    for fk in fk_list
]
```

Add `"foreign_keys": foreign_keys` to each table dict in the schema output. This is a non-breaking addition — old clients ignore extra keys.

### 6b. Resolve Arabic column contradiction (prompts.py)

**Delete** rule 8 from `SQL_GENERATION_PROMPT` (the "Never invent _ar" rule).

**Add** a new rule:
```
8. BILINGUAL SUPPORT: If the user's question is in Arabic, use columns with `_ar` suffixes for display/text columns (e.g., `name_ar`, `department_ar`). Use the corresponding English columns for filtering/joins (e.g., `department_id`). The schema may contain both `name` and `name_ar` — prefer `name_ar` for Arabic questions.
```

Update the context filter prompt's bilingual instruction for consistency.

### 6c. Add structured question-to-SQL verification (prompts.py)

Replace the weak Step 4 in SQL_GENERATION_PROMPT with:

```
Step 4. Verify — Write this explicitly:
  The user asked for: [list each requirement from the question]
  My SELECT clause provides: [map each requirement to a column/expression]
  My WHERE clause filters: [list each filter condition and which requirement it satisfies]
  My GROUP BY / HAVING / ORDER BY: [explain how they map to the question]
  Verification: Every user requirement is addressed in the SQL above. If any requirement is missing, add it.
```

This forces the LLM to reason explicitly about question-to-SQL mapping.

### 6d. Sanitize scenario context to not bleed wrong schema (graph.py)

In `scenario_lookup_node`, after building the scenario context string, strip table/column references that don't exist in the current schema. Add a helper function that takes the scenario_context and current schema, and removes any table names or column names from the context that aren't present in `state.documentation.schema`.

Alternatively: store only the *lesson* text (not the raw SQL) in the scenario context for ambiguous columns. The SQL is still available for reference but should be clearly marked as "past query — verify columns against current schema before using."

### 6e. Add sample data to schema (db_service.py)

Add a `"sample_rows"` field to each table in the schema:

```python
try:
    sample = connection.execute(
        text(f"SELECT * FROM {table_name} LIMIT 3")
    ).mappings().all()
    sample_rows = [dict(row) for row in sample]
except Exception:
    sample_rows = []
```

Add `"sample_rows": sample_rows` to each table dict. This gives the LLM concrete values for WHERE clauses.

### 6f. Raise SQL generation max_tokens (sql_node.py)

Change `max_tokens=300` to `max_tokens=1024` in `sql_node.py:50` to prevent truncation of complex queries.

## Files to Modify

| File | Change |
|------|--------|
| `backend/app/services/db_service.py` | Add FK metadata + sample rows to schema output |
| `backend/app/agents/prompts.py` | Remove contradictory Arabic rule, add bilingual rule, strengthen Step 4 verification |
| `backend/app/agents/graph.py` | Sanitize scenario context to remove non-existent columns |
| `backend/app/agents/nodes/sql_node.py` | Raise max_tokens to 1024 |

## Verification

1. **FK in schema**: Call `get_source_schema(source_id)` — each table dict should have a `foreign_keys` array with `constrained_columns`, `referred_table`, `referred_columns`.
2. **Sample rows in schema**: Each table dict should have a `sample_rows` array with up to 3 row dicts.
3. **Arabic query**: Ask "ما هو إجمالي الرواتب لكل قسم" — the SQL should use `department_name_ar` (or equivalent) for display columns.
4. **Question fidelity**: Ask a 3-part question (e.g., "Show total sales for completed orders in the North region, grouped by month, sorted by month descending") — the generated SQL should have all 3 requirements.
5. **Large SQL**: Ask a complex 4-table JOIN — SQL should not be truncated.
6. **Scenario bleed**: Run a query, then a semantically similar query on a different source with different schema — the SQL should not reference columns from the first schema.

## STOP conditions

- FK data is present in schema output
- Arabic query generates correct SQL with `_ar` columns
- Multi-condition query produces SQL matching all conditions
- Scenario context references only current-schema columns
