import logging
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
from app.core.config import settings
from app.core.exceptions import CSVValidationError, DataCleaningError, DatabaseIngestionError
from app.models.schemas import UploadResponse, UploadMetadata
from app.services.database import engine
from app.services.data_service import DataSourceService

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
_RATE_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 120

app = FastAPI(
    title="AI Text-to-SQL Data Analyst System API",
    description="API for managing data uploads and text-to-SQL conversions",
    version="1.0.0"
)


@app.on_event("shutdown")
def _shutdown() -> None:
    close_graph_orchestrator()


# CORS configuration - environment-based for Azure compatibility
# Parse ALLOW_ORIGINS as comma-separated list, or use ["*"] as fallback
_raw_origins = settings.ALLOW_ORIGINS.strip()
if _raw_origins == "*":
    _cors_origins = ["*"]
elif _raw_origins:
    _cors_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
else:
    _cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


# Include API router FIRST so it handles /api/* routes before static files
app.include_router(api_router)

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