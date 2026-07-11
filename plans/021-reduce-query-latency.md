# Plan 021: Reduce Query Latency by Optimizing LLM Call Patterns

**Priority**: P1 (high — directly improves UX)
**Effort**: M
**Depends on**: 020 (some latency improvements depend on SQL quality first)

## Problem

Average query latency is ~7.7 seconds. The happy path makes 4+ serial LLM calls:

1. **Intent router** — tiny LLM call for `INQUIRE`/`ADD`/`UPDATE`/`DELETE` classification
2. **Context filter** — LLM call to prune schema (only for schemas > 10 tables)
3. **SQL generation** — main LLM call (300 tokens, often truncated → retry)
4. **Insights** — LLM call with query results
5. **Suggestions** — LLM call with query results + SQL

Since `insight_node` and `suggestion_node` are already parallelized in `post_process_node` (ThreadPoolExecutor, max_workers=3), the serial chain is really: router → context filter → SQL gen → [post_process in parallel].

This plan addresses:
- Removing unnecessary LLM calls
- Making remaining calls faster
- Adding caching to avoid repeat work
- Streaming partial results to the frontend

## Solution

### 6a. Merge intent router + context filter into one LLM call

Currently `intent_router_node` calls the LLM with a tiny prompt, then `schema_node` calls `filter_schema_context` which calls the LLM again with the full schema.

**Change**: Combine both into a single `router_and_filter` node that passes both tasks to the LLM in one message. The prompt asks the LLM to:
1. Classify intent
2. Filter schema to relevant tables/columns
3. Output: `{"intent": "INQUIRE", "filtered_schema": {...}}`

**Expected saving**: ~1.5s (one fewer LLM round-trip)

### 6b. Skip context filter completely for small/medium schemas

The current threshold is 10 tables (`context_filtering.py:14`). For the test dataset (15 tables), this triggers every time.

**Change**: Raise threshold to 20 tables. With FK metadata (from plan 020), the LLM can handle moderate-sized schemas without pruning.

Alternatively: use a fast heuristic (keyword match between question and column names) instead of an LLM call for schemas with 10–30 tables. Only call the LLM for schemas > 30 tables.

**Expected saving**: ~2s (entire context filter LLM call skipped for most sources)

### 6c. Reduce insight generation overhead

`insight_node` sends `state.query_results[:20]` to the LLM with `max_tokens=1024`.

**Changes**:
- Reduce to `state.query_results[:10]` (fewer rows → less prompt size → faster generation)
- Reduce `max_tokens` from 1024 to 512 (insights should be concise)
- Truncate long string values in cells to 100 chars

**Expected saving**: ~1s

### 6d. Reduce suggestion generation overhead

`suggestion_node` sends the full schema summary + results preview + SQL. This is a large prompt.

**Changes**:
- Remove the schema summary from the suggestion prompt (suggestions don't need the full schema — they're follow-up questions based on results)
- Reduce results preview from `state.query_results[:3]` to just `[:1]`
- Reduce `max_tokens` from 256 to 192

**Expected saving**: ~0.5s

### 6e. Add semantic result caching

Current cache (`_STALE_CACHE` in graph.py) caches by exact SQL match. Two syntactically different queries that produce the same results won't reuse cache.

**Change**: Add a secondary cache keyed by a hash of:
- `source_id`
- question intent embedding (bag-of-words hash of the question)
- first 100 chars of generated SQL

On graph completion, if results are returned and `success=True`, store `{source_id + question_hash + sql_prefix_hash} -> results`.

On the next query, compute the hash and check before making any LLM calls.

**Expected saving**: For repeated/similar questions: 7s → ~0.1s (cache hit)

### 6f. Stream partial results

**Change**: Add Server-Sent Events (SSE) endpoint `POST /api/query/stream` that sends progress updates:
- `{"event": "schema_loaded"}`
- `{"event": "sql_generated", "sql": "..."}`
- `{"event": "results", "data": [...]}`
- `{"event": "insights", "data": [...]}`
- `{"event": "complete", "data": {...}}`

The frontend can show SQL immediately when generated, then results as they arrive, then insights/suggestions.

This doesn't reduce server latency but makes the perceived latency much lower — users see progress within 1-2 seconds instead of waiting 7s for a blank screen.

### 6g. Sample background evaluation (reduces server load)

`graph.py:1023-1055` runs evaluation on every query. This doesn't affect user-facing latency (it's in a background thread) but adds CPU load.

**Change**: Sample evaluation to 20% of queries (or skip entirely when server is under load). Add a config flag `EVALUATION_SAMPLE_RATE` (default 1.0) in settings.

## Files to Modify

| File | Change |
|------|--------|
| `backend/app/agents/graph.py` | Merge router + context filter into one node; add semantic cache; add streaming endpoint; sample eval rate |
| `backend/app/agents/tools/context_filtering.py` | Raise threshold to 20 tables, or add heuristic-based filtering |
| `backend/app/api/routes.py` | Add `POST /api/query/stream` SSE endpoint |
| `backend/app/agents/prompts.py` | Combined router+filter prompt |
| `backend/app/core/config.py` | Add `EVALUATION_SAMPLE_RATE` setting |

## Verification

1. **Latency before/after**: Run same 5 queries before and after — average latency should drop by at least 40% (from ~7.7s to ~4.5s or less).
2. **Cache hit**: Run a query, then run a semantically identical query — should return results in <1s.
3. **SSE**: Hit `/api/query/stream` — should receive multiple events before the final response.
4. **Accuracy**: Merged router+filter node should still correctly classify intent and produce filtered schema comparable to the two-call version.

## STOP conditions

- Average latency < 5s for the test dataset
- No quality regression on BIRD eval suite (must stay at 26/30 or better)
- SSE endpoint returns at least 3 events before completion
