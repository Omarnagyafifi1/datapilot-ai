# Project Context (Quick Resume)

Last updated: 2026-07-02

## Repository
- Name: datapilot-ai
- Branch: main
- Default branch: main

## Current Implementation Status

### FR-02: Data Source Management
- Data source connect endpoint implemented.
- Data source list endpoint implemented.
- Data source delete endpoint implemented.
- Source credentials are encrypted in storage.
- Data source connection strings are loaded and cached by source_id.

### FR-04: Context-Aware Schema Filtering
- Implemented `filter_schema_context` in `app/agents/tools/context_filtering.py`.
- Integrated into the `fetch_schema` node within the graph.
- Uses an LLM to analyze the user's question and prune the full database schema.
- Filters out irrelevant tables and columns to reduce token consumption.
- Improves SQL generation accuracy by providing a focused, noise-free schema context.
- Safely falls back to the full schema if the filtering step fails.

### FR-09: Generate Insights
- Implemented insight_node in the graph flow.
- Runs after SQL execution.
- If query results are empty, returns fallback insights:
  - ar: "لا توجد بيانات كافية للتحليل"
  - en: "No data to analyze"
- Sends only first 50 rows to the LLM.
- Parses JSON safely; falls back instead of crashing.
- Enforces insight count to be between 3 and 5.

### FR-11: Follow-up Suggestions
- Implemented suggestion_node after insight_node.
- Uses question + generated SQL + insights.
- Parses JSON safely; returns [] on parse/shape failure.
- Enforces exactly 3 suggestions.

### FR-12: Auto Documentation
- Implemented documentation_node as the last graph step.
- No LLM call in this step.
- Builds QueryDocument with:
  - question
  - sql
  - results_count
  - insights
  - suggestions
  - executed_at
- executed_at is set at final documentation time.
- Logs full document as JSON at INFO level.
- Saves document to state.documentation.
- /api/query returns answer + documentation.

### EV-01: LangSmith Evaluation Integration
- **Chosen platform**: LangSmith (over Langfuse) for Text-to-SQL evaluation.
- **Rationale**: Project already uses LangChain/LangGraph extensively; LangSmith provides native tracing without additional SDKs, built-in dataset management for SQL regression testing, and both offline/online evaluation modes.
- Implemented `app/services/evaluation_service.py` with 3 evaluators:
  - **SQL Syntax Check**: Validates SQL structure via `sqlite3.EXPLAIN` (for SQLite) or regex patterns for other dialects; blocks DDL/DML keywords.
  - **SQL Correctness (LLM-as-judge)**: Evaluates correctness, completeness, and efficiency scores (0.0-1.0 each) using an LLM.
  - **Schema Relevance**: LLM judges if the SQL uses correct tables/columns for the user's question.
- Aggregated **overall score** = correctness*0.4 + completeness*0.25 + efficiency*0.15 + schema*0.1 + syntax*0.1.
- **Auto-evaluation** runs after every graph query (in `graph.py:run()`) and posts 8 feedback keys to LangSmith.
- `POST /api/evaluate` endpoint for manual SQL evaluation.
- Requires `LANGCHAIN_API_KEY` env var to enable; silently skips if not configured.

### EV-02: Evaluation Metrics Dashboard
- `GET /api/system/metrics` returns comprehensive evaluation metrics:
  - `total_queries`, `total_sources`, `success_rate`, `avg_latency`
  - `total_visualizations`, `visualization_rate`
  - `trends[]`: daily query counts over 14 days (total, success, with_viz)
  - `visualization_breakdown[]`: chart_type usage counts
- Frontend dashboard (`Dashboard.jsx`) displays:
  - Summary metric cards (5 columns)
  - SVG donut chart for query success distribution
  - SVG bar chart for 14-day query trends
  - Visualization usage stacked bar
  - Active feed + feature cards
- History tracking extended with `has_visualization` and `chart_type` columns.

## API Contract Snapshot

### POST /api/query
Request body:
{
  "question": "...",
  "source_id": "..."
}

Behavior:
- source_id is required.
- Route validates and warms source connection via data_source_service.get_conn_string(source_id).
- Graph runs with question and source_id.

Response shape:
{
  "answer": "...",
  "documentation": {
    "question": "...",
    "sql": "...",
    "results_count": 0,
    "insights": [],
    "suggestions": [],
    "executed_at": "..."
  }
}

## Graph Flow (Current)
router -> fetch_and_filter_schema -> lookup_scenario -> generate_sql -> execute_sql -> validate_result -> insight_node -> suggestion_node -> documentation_node -> final response

## Key Files To Reopen First
- backend/app/api/routes.py
- backend/app/models/schemas.py
- backend/app/agents/graph.py
- backend/app/agents/state/agent_state.py
- backend/app/agents/tools/sql_tools.py
- backend/app/agents/tools/context_filtering.py
- backend/app/services/db_service.py

## Smoke Checks Already Done
- POST /api/query without source_id -> 422 (expected).
- POST /api/query with invalid source_id -> 400 Invalid data source id (expected).

## Known Environment Note
- If analyzer shows unresolved imports for fastapi/sqlalchemy, verify the selected Python environment and installed dependencies.

## BIRD Evaluation Results

### Latest: 26/30 (86.7%) execution accuracy — 2026-07-02

- **Provider**: OpenRouter (`google/gemma-4-31b-it:free`)
- **Eval**: `scripts/eval_lightweight.py` (1 LLM call per query, no graph overhead)
- **Per difficulty**: Easy 13/15, Medium 10/12, Hard 3/3
- **English accuracy**: 22/24 (91.7%, 2 failures due to rate-limit truncation)
- **Arabic accuracy**: 4/6 (66.7%) — Arabic questions improved from 0/6 with structured 4-step prompt rule
- **Avg latency**: 6.4s per query

### Key improvements that got from 4/24 → 26/30:
1. **Structured 4-step Arabic rule** (rule 21): translate → identify pattern → generate SQL → replace with _ar columns
2. **Arabic→English keyword mappings** covering 15+ phrases
3. **SQL prompt** (`app/agents/prompts.py`): 24 explicit rules covering DISTINCT, HAVING, ORDER BY + LIMIT, aggregate-in-SELECT enforcement, WHERE-column SELECT behavior, 3-JOIN order, alias rules, column parsimony
4. **Lightweight eval script** avoids graph overhead (6-10 LLM calls/query → 1)
5. **Retry logic** for provider errors (429/502/truncation)

### Arabic question results
- **4/6 pass consistently**: avg salary per dept (Q17), managers+depts (Q19), depts+projects+budget (Q18), sales completed revenue (Q21 intermittent)
- **2/6 still fail**: Engineering dept count (Q20 — uses `dept_name` instead of `dept_name_ar`), products needing restock with supplier info (Q22 — AVG instead of filter)

### Remaining failure patterns
- **Rate-limit truncation** (~2 English questions occasionally fail due to OpenRouter 502/429 errors)
- **Arabic column mapping**: Model sometimes uses `dept_name` instead of `dept_name_ar`
- **Complex Arabic queries**: 3-table JOINs with conditions in Arabic still unreliable

## Prompt Engineering Notes
- `SQL_GENERATION_PROMPT` in `app/agents/prompts.py` is the single most impactful file
- System message emphasizes raw SQL only (no markdown, no backticks)
- 24 numbered rules enforce specific SQL patterns

## Next Recommended Steps
1. Test Arabic question support (rule 21 covers Arabic column handling with 4-step approach)
2. Test with the full AgentGraph (not just lightweight) now that SQL gen is reliable
3. Add unit tests for SQL generation prompt edge cases
4. Add integration tests for /api/query request/response contract
