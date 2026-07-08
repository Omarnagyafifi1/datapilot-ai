# Agent Context

## Project: DataPilot AI
## Branch: azure-deployment

## Key Files
- `backend/app/main.py` - FastAPI app entrypoint, health/ready/live endpoints, CORS, rate limiting, env validation
- `backend/app/core/config.py` - Settings with all env vars (Azure OpenAI, PostgreSQL, etc.)
- `backend/app/llm/factory.py` - LLM provider factory (groq, openrouter, gemini, azure, mock, litellm)
- `backend/app/llm/providers/azure_openai_llm.py` - Azure OpenAI provider
- `backend/app/api/routes.py` - All API routes
- `backend/app/api/chat.py` - Chat endpoints
- `backend/app/agents/graph.py` - LangGraph agent graph
- `backend/app/services/database.py` - Async DB engine (SQLite/PostgreSQL)
- `frontend/src/lib/api.js` - Frontend API client (env-based URL)
- `frontend/src/lib/constants.js` - Includes Azure provider
- `infrastructure/main.bicep` - Azure Bicep template
- `.github/workflows/ci-cd.yml` - CI/CD pipeline
- `docker-compose.yml` - Dev compose
- `docker-compose.prod.yml` - Production compose
- `Dockerfile` - Multi-stage production Dockerfile

## Key Environment Variables
- `LLM_PROVIDER` - groq|openrouter|gemini|azure|mock
- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`
- `ENCRYPTION_KEY` - Required (32-byte base64)
- `POSTGRES_HOST/USER/PASSWORD/DB` - For PostgreSQL auto-config
- `ALLOW_ORIGINS` - Comma-separated CORS origins
- `APPLICATIONINSIGHTS_CONNECTION_STRING` - Azure monitor

## Lint/Test Commands
- Backend lint: `flake8 backend/app --max-line-length=120`
- Frontend lint: `cd frontend && npm run lint`
- Backend test: `cd backend && pytest`
- Docker build: `docker build -t datapilot-ai:latest .`
