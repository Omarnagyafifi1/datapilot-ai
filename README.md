# DEPI Project Backend

## Overview
This project is a FastAPI backend organized into clear layers, where each part has a specific responsibility.
The goal of this structure is to make development, testing, and future extension easier without overcomplication.

## Project Structure

- backend/
  - Main backend directory.
  - Contains environment configuration, dependencies, and application code.

### Inside backend

- .env.example
  - Template of required environment variables.
  - Helps new developers understand what needs to be configured.

- requirements.txt
  - Python dependencies required to run the project.

- app/
  - The core application package.
  - Business logic is split by concern.

## app Folder Breakdown

- app/main.py
  - FastAPI application entry point.
  - Creates the app and registers API routes.

- app/api/
  - API endpoint layer.
  - Receives requests and returns responses.

- app/api/routes.py
  - Defines routes like health and query.
  - Represents the external interface of the backend.

- app/api/deps.py
  - Shared route dependencies.
  - Builds and provides the graph orchestrator and its required services.

- app/core/
  - Shared core-level project utilities.

- app/core/config.py
  - Loads and reads environment variables using python-dotenv.
  - Includes settings like GROQ_API_KEY and LANGSMITH_*.

- app/core/logger.py
  - Simple logger setup reusable across the project.

- app/llm/
  - LLM abstraction and provider layer.

- app/llm/base_llm.py
  - Base interface for any LLM provider.
  - Enforces a common method shape (for example generate).

- app/llm/factory.py
  - Factory for selecting the proper provider (mock or openai placeholder).
  - Reduces direct coupling between business flow and provider implementation.

- app/llm/providers/
  - Concrete provider implementations.

- app/llm/providers/mock_llm.py
  - Mock provider for development and quick testing.

- app/llm/providers/openai_llm.py
  - Placeholder for a real provider.
  - Currently a stub with minimal behavior.

- app/services/
  - Service layer for data access and related operations.

- app/services/db_service.py
  - Minimal interface for SQL execution (currently stubbed).

- app/services/schema_service.py
  - Returns schema or database structure context (placeholder).

- app/services/data_source_service.py
  - Lists or manages available data sources (placeholder).

- app/agents/
  - Agent flow and orchestration layer.

- app/agents/base_agent.py
  - Base interface for agent implementations.

- app/agents/graph.py
  - Main orchestrator for the execution flow.
  - Coordinates steps: fetch schema, generate SQL, execute SQL, and build a response.

- app/agents/prompts.py
  - Contains placeholder prompt strings used by the flow.

- app/agents/nodes/
  - Small, focused execution steps used in the graph.

- app/agents/nodes/sql_node.py
  - Node responsible for generating SQL from the user question.

- app/agents/tools/
  - Reusable helper tools for nodes.

- app/agents/tools/sql_tools.py
  - SQL execution helper through db_service.

- app/agents/tools/schema_tools.py
  - Schema retrieval helper through schema_service.

- app/agents/tools/context_filtering.py
  - LLM-based tool to filter and prune the database schema based on the user's question.
  - Optimizes token usage and improves performance by providing a context-aware minimal schema.

- app/agents/state/
  - Agent state definitions during execution.

- app/agents/state/agent_state.py
  - Holds flow fields such as question, sql, and answer.

- app/models/
  - Request/response data models.

- app/models/schemas.py
  - Pydantic schemas for API payloads and responses.

- __init__.py files
  - Mark directories as Python packages.
  - Help keep imports organized across modules.

## Key Features

- **Context-Aware Schema Filtering**
  - Automatically prunes the database schema based on the user's question.
  - Only relevant tables and columns are passed to the SQL generator.
  - **Benefits**: Reduces token consumption, lowers latency, and increases SQL generation accuracy by eliminating noise.

## Why This Structure Matters

- Separation of concerns
  - Each layer has a clear purpose, so changes are easier and safer.

- Extensibility
  - You can swap LLM providers or add new nodes without breaking the whole system.

- Testability
  - Services, tools, and routes are isolated enough for focused tests.

- Readability
  - New developers can understand the codebase faster from the folder layout.

## Quick Start

1. Create a virtual environment:
   - python -m venv backend/.venv

2. Install dependencies:
   - backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt

3. Run the application:
   - backend/.venv/Scripts/uvicorn.exe app.main:app --reload --app-dir backend

## Frontend illustration assets

- Placeholder SVG files live in `frontend/src/assets/illustrations/`.
- Replace the placeholder files with licensed isometric SVGs (examples: ManyPixels, unDraw, Vecteezy, Freepik). Download the SVGs, optimize with `svgo`, then overwrite the files:

```bash
# example
npm install -g svgo
npx svgo -i path/to/downloaded.svg -o frontend/src/assets/illustrations/isometric-neon-purple.svg
```

- If using Freepik/Vecteezy/Flaticon free assets, include attribution in this README or in the app footer. Example attribution:

  "Illustrations by Freepik — https://www.freepik.com"

- The component `IsometricIllustration` (frontend/src/components/IsometricIllustration.jsx) imports these files by default and is used in the dashboard hero.

### Automating download + optimization

If you want me to automatically download and optimize SVGs, use the helper script included at `frontend/scripts/fetch_optimize_svgs.js`.

1. Create a text file with lines of `url,filename.svg` (one per SVG). Example `svg-urls.txt`:

```
https://undraw.co/api/illustrations/Analyze.svg,isometric-neutral-undraw.svg
https://example.com/path/to/teal-isometric.svg,isometric-teal-data.svg
https://example.com/path/to/neon-isometric.svg,isometric-neon-purple.svg
```

2. Install dependencies and run the script:

```bash
cd frontend
npm install node-fetch@2 svgo@2
node scripts/fetch_optimize_svgs.js ../svg-urls.txt
```

3. The script writes optimized SVGs to `frontend/src/assets/illustrations/`.

4. After verifying the images and licenses, update `ATTRIBUTION.md` with exact credits and asset URLs.


## Execution Flow
```mermaid
graph TD
    START([START]) --> Router[router]
    
    Router -->|conditional| RouteIntent{route_intent}
    RouteIntent -->|GENERAL| GeneralChat[general_chat]
    RouteIntent -->|other| FetchAndFilterSchema[fetch_and_filter_schema]
    
    GeneralChat --> END1([END])
    
    FetchAndFilterSchema -->|conditional| RouteSQLGen{route_sql_gen}
    RouteSQLGen -->|ADD/UPDATE/DELETE| GenerateModSQL[generate_mod_sql]
    RouteSQLGen -->|other| LookupScenario[lookup_scenario]
    
    GenerateModSQL --> Approval[approval]
    
    Approval -->|conditional| RouteApproval{route_approval}
    RouteApproval -->|success=true| ExecuteSQL[execute_sql]
    RouteApproval -->|success=false| END2([END])
    
    LookupScenario -->|conditional| RouteScenario{route_scenario}
    RouteScenario -->|scenario_matched AND sql exists| ExecuteSQL
    RouteScenario -->|otherwise| GenerateSQL[generate_sql]
    
    GenerateSQL --> ExecuteSQL
    
    ExecuteSQL -->|conditional| RouteExecution{route_execution}
    RouteExecution -->|success=true| ValidateResult[validate_result]
    RouteExecution -->|success=false AND retry_count >= MAX_RETRIES| ScenarioFailure[scenario_failure]
    RouteExecution -->|success=false AND retry_count < MAX_RETRIES| FixSQL[fix_sql]
    
    FixSQL -->|conditional| RouteFix{route_fix}
    RouteFix -->|success=true| ValidateResult
    RouteFix -->|success=false AND retry_count >= MAX_RETRIES| ScenarioFailure
    RouteFix -->|success=false AND retry_count < MAX_RETRIES| ExecuteSQL
    
    ValidateResult -->|conditional| RouteValidation{route_validation}
    RouteValidation -->|validation_passed=true| ScenarioSuccess[scenario_success]
    RouteValidation -->|validation_passed=false AND retry_count >= MAX_RETRIES| ScenarioFailure
    RouteValidation -->|validation_passed=false AND retry_count < MAX_RETRIES| GenerateSQL
    
    ScenarioSuccess --> GenerateViz[generate_visualization]
    GenerateViz --> GenerateInsights[generate_insights]
    GenerateInsights --> GenerateSuggestions[generate_suggestions]
    GenerateSuggestions --> Document[document]
    
    ScenarioFailure --> Document
    
    Document --> END3([END])
```
