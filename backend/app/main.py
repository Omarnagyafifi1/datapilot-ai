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

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all. In production, restrict this.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Fallback middleware to ensure CORS headers are present on all responses
@app.middleware("http")
async def _ensure_cors_headers(request, call_next):
    # Short-circuit preflight OPTIONS requests to ensure CORS headers are present
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
        return Response(status_code=200, headers=headers)

    response = await call_next(request)
    # these are safe to set in development; in production refine as needed
    response.headers.setdefault("Access-Control-Allow-Origin", "*")
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


@app.middleware("http")
async def _log_requests(request: Request, call_next):
    start_time = time.monotonic()
    client = request.client.host if request.client else "unknown"
    method = request.method
    path = request.url.path
    
    logger.info(f"Incoming request: {method} {path} from client {client}")
    
    try:
        response = await call_next(request)
        process_time = (time.monotonic() - start_time) * 1000
        logger.info(f"Completed request: {method} {path} - Status: {response.status_code} - Duration: {process_time:.2f}ms")
        return response
    except Exception as exc:
        process_time = (time.monotonic() - start_time) * 1000
        logger.error(f"Failed request: {method} {path} - Error: {str(exc)} - Duration: {process_time:.2f}ms")
        raise


# Catch-all OPTIONS handler to ensure preflight requests return CORS headers
@app.options("/{full_path:path}")
async def catch_all_options(full_path: str):
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        "Access-Control-Allow-Headers": "*",
    }
    return Response(status_code=200, headers=headers)

# Include API router FIRST so it handles /api/* routes before static files
app.include_router(api_router)

# Mount frontend static files when available (built via `npm run build` into frontend/dist)
dist_dir = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="frontend")


# Exception Handlers
from fastapi.exceptions import RequestValidationError

@app.exception_handler(CSVValidationError)
async def csv_validation_exception_handler(request, exc: CSVValidationError):
    logger.warning(f"CSV Validation Error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"success": False, "message": str(exc), "data": None},
    )

@app.exception_handler(DataCleaningError)
async def data_cleaning_exception_handler(request, exc: DataCleaningError):
    logger.error(f"Data Cleaning Error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"success": False, "message": str(exc), "data": None},
    )

@app.exception_handler(DatabaseIngestionError)
async def database_ingestion_exception_handler(request, exc: DatabaseIngestionError):
    logger.error(f"Database Ingestion Error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "message": str(exc), "data": None},
    )

from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.detail, "data": None},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    errors = exc.errors()
    msg = errors[0]["msg"] if errors else "Validation error"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"success": False, "message": f"{msg}: {errors}", "data": None},
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc: Exception):
    logger.exception("Unhandled application error occurred")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "message": "An unexpected error occurred. Please contact the administrator.", "data": None},
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