# Project Context (Quick Resume)

Last updated: 2026-04-26

## Repository
- Name: datapilot-ai
- Branch: feature/fr-02-datasource-management
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

## Next Recommended Steps
1. Run /api/query with a real valid source_id from connected data sources.
2. Add unit tests for:
   - _normalize_insights and _parse_insights
   - _normalize_suggestions and _parse_suggestions
   - documentation_node output contract
3. Add integration tests for /api/query request/response contract.
