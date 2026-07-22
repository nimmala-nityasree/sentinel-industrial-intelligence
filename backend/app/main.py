"""
Sentinel backend — FastAPI application entrypoint.

Wires together the API routers, CORS policy, and structured logging.
Kept deliberately thin: all real logic lives in services/ and agents/,
consistent with the clean-architecture separation used across the codebase.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_alerts, routes_documents, routes_graph, routes_health, routes_query
from app.config import settings
from app.core.logging_config import configure_logging, logger
from app.services.graph_service import graph_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("Sentinel backend starting up")
    yield
    logger.info("Sentinel backend shutting down")
    graph_service.close()


app = FastAPI(
    title="Sentinel — Industrial Knowledge Intelligence Platform",
    description=(
        "Multi-agent AI system for unified industrial asset & operations intelligence: "
        "RAG copilot, knowledge graph, contradiction/drift detection, maintenance RCA, "
        "and compliance intelligence — built for ET AI Hackathon 2026."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
app.include_router(routes_health.router, prefix=API_PREFIX)
app.include_router(routes_documents.router, prefix=API_PREFIX)
app.include_router(routes_query.router, prefix=API_PREFIX)
app.include_router(routes_alerts.router, prefix=API_PREFIX)
app.include_router(routes_graph.router, prefix=API_PREFIX)


@app.get("/")
def root() -> dict:
    return {
        "service": "Sentinel Industrial Knowledge Intelligence Platform",
        "docs": "/docs",
        "health": f"{API_PREFIX}/health",
    }
