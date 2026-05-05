## SRS — AI Text-to-SQL Data Analyst System

### Overview

- User asks a question in natural language.
- System retrieves relevant schema and contextual data.
- LLM generates a candidate SQL query.
- Validator enforces safety and correctness constraints.
- Execution engine runs the SQL against registered data sources.
- Insight and visualization agents produce tabular, chart, and narrative outputs.
- A report containing SQL, results, visualizations and a narrative is returned to the user.

### How to Run (Developer Notes)

1. Create a `.env` with DB connection and LLM/API keys.
2. Start a PostgreSQL instance and ensure the configured DB is reachable.
3. From `backend/` activate the Python venv and run:

```powershell
uvicorn app.main:app --reload --port 8000
```

4. Start the frontend:

```bash
cd frontend
pnpm install
pnpm dev
```

5. Open the UI and try `/query` via the Swagger docs or the app UI.

### API Endpoints (Draft)

- `POST /api/query` — question → SQL → result
- `POST /api/datasources/connect` — register an external DB connection
- `POST /api/data/csv` — upload CSV and ingest to PostgreSQL (planned)
- `GET /api/datasources/{id}/schema` — tables + columns (+ relationships)
- `GET /api/query-history` — query/report history

### Future Improvements

- Cache embeddings (FAISS / vector DB)
- Constrain decoding or fine-tune SQL model for improved correctness
- Row-level security & multi-tenant controls
- Observability dashboard (latency, error rate, LLM cost)

Reference: [Notion SRS link](https://www.notion.so/SRS-AI-Text-to-SQL-Data-Analyst-System-0d8013ec6fdb4e2db9aeb0b6a11d3c5d?pvs=21)
