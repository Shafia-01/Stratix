"""
Keylytics FastAPI application entry point.

Start with:
    uvicorn api.main:app --reload

Global exception handlers ensure all tool errors map to appropriate HTTP codes:
  - pydantic.ValidationError          → 422 Unprocessable Entity
  - KeylyticsAPIError / DataError     → 502 Bad Gateway (upstream API failure)
  - Any other Exception               → 500 Internal Server Error

Lifespan:
  - Warms the compiled LangGraph at startup.
  - Starts/stops KeylyticsScheduler for background monitoring jobs.
  - Initialises database connection and verifies schema.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from api.dependencies import verify_api_key

from src.db_client import connect_db
from src.exceptions import KeylyticsAPIError, KeylyticsDataError
from src.security_utils import redact_api_keys
from src.logger_config import get_logger

# Route modules — exclusively from api/routes/ (api/routers/ has been removed)
from api.routes import health, keywords, intelligence
from api.routes import agent as agent_routes
from api.routes import monitor as monitor_routes
from api.routes import evals as evals_routes
from api.routes import observability as observability_routes

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Lifespan — ensure DB schema exists before first request is served
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(application: FastAPI):
    """Initialise DB, warm compiled graph, and start scheduler before first request."""
    logger.info("Keylytics API starting up — initialising database …")
    try:
        connect_db()
        logger.info("Database connection established and schema verified.")
    except Exception as exc:
        logger.error(f"Startup DB init failed: {exc}", exc_info=True)

    # Warm the compiled LangGraph (builds graph + checkpointer once at boot)
    try:
        from src.graph.graph import get_compiled_graph
        get_compiled_graph()
        logger.info("LangGraph research graph warmed successfully.")
    except Exception as exc:
        logger.error(f"Graph warm-up failed: {exc}", exc_info=True)

    # Start keyword monitoring scheduler
    _scheduler = None
    try:
        from src.scheduler import KeylyticsScheduler
        from src.graph.graph import get_compiled_graph as _gcg
        _scheduler = KeylyticsScheduler(graph_fn=_gcg)
        _scheduler.start()
        application.state.scheduler = _scheduler
        logger.info("KeylyticsScheduler started.")
    except Exception as exc:
        logger.error(f"Scheduler startup failed (non-fatal): {exc}", exc_info=True)

    yield  # Application runs

    # Shutdown scheduler gracefully
    if _scheduler is not None:
        try:
            _scheduler.shutdown()
            logger.info("KeylyticsScheduler shut down.")
        except Exception as exc:
            logger.error(f"Scheduler shutdown error: {exc}", exc_info=True)


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
app.include_router(keywords.router, prefix="/keywords", tags=["Keywords"], dependencies=[Depends(verify_api_key)])
app.include_router(intelligence.router, prefix="/intelligence", tags=["Intelligence"], dependencies=[Depends(verify_api_key)])
app.include_router(agent_routes.router, dependencies=[Depends(verify_api_key)])                              # /agent/*
app.include_router(monitor_routes.router, dependencies=[Depends(verify_api_key)])                            # /monitor/*
app.include_router(evals_routes.router, dependencies=[Depends(verify_api_key)])                              # /evals/*
app.include_router(observability_routes.router)                      # /metrics, /health/detailed

logger.info("Keylytics FastAPI app initialised.")

