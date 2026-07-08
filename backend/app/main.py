import logging
import os
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi import Response

from app.api.deps import close_graph_orchestrator
from app.api.routes import router as api_router
from app.api.chat import router as chat_router
from app.core.exceptions import CSVValidationError, DataCleaningError, DatabaseIngestionError
from app.models.schemas import UploadResponse, UploadMetadata
from app.services.database import engine
from app.services.data_service import DataSourceService
from sqlalchemy import text

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
_RATE_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 120


def validate_environment() -> None:
    """Validate required environment variables at startup. Fail fast if missing."""
    from app.core.config import settings

    required_vars = ["ENCRYPTION_KEY"]

    provider = (settings.LLM_PROVIDER or os.getenv("LLM_PROVIDER", "")).strip().lower()
    if not provider:
        provider = settings.DEFAULT_LLM_PROVIDER

    if provider == "azure":
        required_vars.extend(["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT"])
    elif provider == "groq":
        required_vars.append("GROQ_API_KEY")
    elif provider == "openrouter":
        required_vars.append("OPENROUTER_API_KEY")
    elif provider == "gemini":
        required_vars.append("GEMINI_API_KEY")

    missing = [v for v in required_vars if not os.getenv(v) and not getattr(settings, v, None)]
    if missing:
        msg = f"Missing required environment variables for provider '{provider}': {', '.join(missing)}"
        logger.error(msg)
        raise RuntimeError(msg)

    logger.info("Environment validation passed for provider '%s'", provider)


validate_environment()

app = FastAPI(
    title="AI Text-to-SQL Data Analyst System API",
    description="API for managing data uploads and text-to-SQL conversions",
    version="1.0.0"
)


@app.on_event("shutdown")
def _shutdown() -> None:
    close_graph_orchestrator()

# CORS configuration
ALLOW_ORIGINS = os.getenv("ALLOW_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health, Readiness, Liveness endpoints (before any middleware)
@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/ready")
async def ready():
    try:
        from app.services.database import engine
        if engine is None:
            return JSONResponse(status_code=503, content={"status": "not ready", "detail": "Database not configured"})
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "not ready", "detail": str(e)})


@app.get("/live")
async def live():
    return {"status": "alive"}


# Fallback middleware to ensure CORS headers are present on all responses
@app.middleware("http")
async def _ensure_cors_headers(request, call_next):
    allowed_origin = ALLOW_ORIGINS[0] if ALLOW_ORIGINS[0] != "*" else "*"
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": allowed_origin,
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
        return Response(status_code=200, headers=headers)

    response = await call_next(request)
    response.headers.setdefault("Access-Control-Allow-Origin", allowed_origin)
    response.headers.setdefault("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
    response.headers.setdefault("Access-Control-Allow-Headers", "*")
    return response


@app.middleware("http")
async def _rate_limit(request: Request, call_next):
    if request.url.path.startswith("/api"):
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        bucket = _RATE_BUCKETS[client]
        while bucket and now - bucket[0] > RATE_LIMIT_WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please retry shortly."},
                headers={"Retry-After": str(RATE_LIMIT_WINDOW_SECONDS)},
            )
        bucket.append(now)
    return await call_next(request)


# Catch-all OPTIONS handler to ensure preflight requests return CORS headers
@app.options("/{full_path:path}")
async def catch_all_options(full_path: str):
    allowed_origin = ALLOW_ORIGINS[0] if ALLOW_ORIGINS[0] != "*" else "*"
    headers = {
        "Access-Control-Allow-Origin": allowed_origin,
        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        "Access-Control-Allow-Headers": "*",
    }
    return Response(status_code=200, headers=headers)

# Include API routers FIRST so they handle /api/* routes before static files
app.include_router(api_router)
app.include_router(chat_router)

# Mount frontend static files when available (built via `npm run build` into frontend/dist)
dist_dir = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="frontend")


# Exception Handlers
@app.exception_handler(CSVValidationError)
async def csv_validation_exception_handler(request, exc: CSVValidationError):
    logger.warning(f"CSV Validation Error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


@app.exception_handler(DataCleaningError)
async def data_cleaning_exception_handler(request, exc: DataCleaningError):
    logger.error(f"Data Cleaning Error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc)},
    )


@app.exception_handler(DatabaseIngestionError)
async def database_ingestion_exception_handler(request, exc: DatabaseIngestionError):
    logger.error(f"Database Ingestion Error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc)},
    )


# Routes
@app.post("/api/v1/data/upload-csv", response_model=UploadResponse)
async def upload_csv(file: UploadFile = File(...)):
    """
    Uploads a CSV file, cleans it, and ingests it into the PostgreSQL database.
    Returns AI-ready metadata about the newly created table.
    """
    try:
        metadata = await DataSourceService.process_csv(file, engine)
        return UploadResponse(
            message="CSV successfully processed and ingested.",
            metadata=UploadMetadata(**metadata)
        )
    except (CSVValidationError, DataCleaningError, DatabaseIngestionError):
        # Allow custom exceptions to be handled by the specific handlers above
        raise
    except Exception as e:
        logger.exception("Unexpected error during CSV upload")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")