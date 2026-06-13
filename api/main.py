from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import keywords, serp, competitors, trends, clusters
from src.logger_config import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Keylytics API",
    description="HTTP API surface for Keylytics research pipeline and agent tools",
    version="1.0.0"
)

# CORS middleware configuration
# WARNING: Allowed all origins for now. Restrict this in production to specific domains!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}

# Register routers
app.include_router(keywords.router, prefix="/api/v1/keywords", tags=["Keywords"])
app.include_router(serp.router, prefix="/api/v1/serp", tags=["SERP"])
app.include_router(competitors.router, prefix="/api/v1/competitors", tags=["Competitors"])
app.include_router(trends.router, prefix="/api/v1/trends", tags=["Trends"])
app.include_router(clusters.router, prefix="/api/v1/clusters", tags=["Clusters"])

logger.info("Keylytics FastAPI app initialized.")
