"""
Keylytics FastAPI application entry point.

Start with:
    uvicorn api.main:app --reload

Global exception handlers ensure all tool errors map to appropriate HTTP codes:
  - pydantic.ValidationError          → 422 Unprocessable Entity
  - KeylyticsAPIError / DataError     → 502 Bad Gateway (upstream API failure)
  - Any other Exception               → 500 Internal Server Error
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src.db_client import connect_db
from src.exceptions import KeylyticsAPIError, KeylyticsDataError
from src.security_utils import redact_api_keys
from src.logger_config import get_logger

# Route modules — exclusively from api/routes/ (api/routers/ has been removed)
from api.routes import health, keywords, intelligence

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Lifespan — ensure DB schema exists before first request is served
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(application: FastAPI):
    """Initialise the database connection before the first request is served."""
    logger.info("Keylytics API starting up — initialising database …")
    try:
        connect_db()
        logger.info("Database connection established and schema verified.")
    except Exception as exc:
        # Log but don't crash startup — health check will report db=False
        logger.error(f"Startup DB init failed: {exc}", exc_info=True)
    yield  # Application runs
    # (teardown hooks can go here if needed in future)


app = FastAPI(
    title="Keylytics API",
    description="HTTP API surface for the Keylytics SEO research pipeline and agent tools.",
    version="2.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — localhost dev origins only.
# In production, replace with the actual deployed frontend domain.
# ---------------------------------------------------------------------------
_DEV_ORIGINS = [
    "http://localhost:3000",   # React / Next.js dev server
    "http://localhost:8501",   # Streamlit dev server
    "http://localhost:8000",   # Uvicorn self-referential (e.g. Swagger UI)
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8501",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_DEV_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------
@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    logger.warning(f"ValidationError on {request.url}: {exc}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(KeylyticsAPIError)
async def keylytics_api_error_handler(request: Request, exc: KeylyticsAPIError) -> JSONResponse:
    msg = redact_api_keys(str(exc))
    logger.error(f"KeylyticsAPIError on {request.url}: {msg}")
    return JSONResponse(status_code=502, content={"detail": msg})


@app.exception_handler(KeylyticsDataError)
async def keylytics_data_error_handler(request: Request, exc: KeylyticsDataError) -> JSONResponse:
    msg = redact_api_keys(str(exc))
    logger.error(f"KeylyticsDataError on {request.url}: {msg}")
    return JSONResponse(status_code=502, content={"detail": msg})


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    msg = redact_api_keys(str(exc))
    logger.error(f"Unhandled exception on {request.url}: {msg}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred."})


# ---------------------------------------------------------------------------
# Router registration — single source of truth, all from api/routes/
# ---------------------------------------------------------------------------
app.include_router(health.router)                                    # GET /health
app.include_router(keywords.router, prefix="/keywords", tags=["Keywords"])
app.include_router(intelligence.router, prefix="/intelligence", tags=["Intelligence"])

logger.info("Keylytics FastAPI app initialised.")
