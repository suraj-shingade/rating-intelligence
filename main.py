"""FastAPI application entry point for the Rating Methodology Intelligence System.

Initializes all application components -- configuration, logging, Weaviate
connection, LLM service, and analytical pipelines -- and exposes the REST API
via FastAPI with CORS middleware and structured lifecycle management.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router
from src.config import get_settings
from src.exceptions import RatingIntelligenceError, VectorStoreConnectionError
from src.logging_config import (
    clear_correlation_id,
    configure_logging,
    get_logger,
    set_correlation_id,
)
from src.services.document_processor import DocumentProcessor
from src.services.llm_service import LLMService
from src.services.rating_pipeline import RatingPipeline
from src.services.weaviate_service import WeaviateService


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle: startup and shutdown sequences.

    On startup: initializes configuration, logging, Weaviate connection,
    LLM service, and analytical pipeline. Stores service instances in
    app.state for dependency injection via request handlers.

    On shutdown: gracefully disconnects from Weaviate and logs final
    token usage statistics.

    Args:
        app: The FastAPI application instance.

    Yields:
        Control to the application after startup initialization.
    """
    settings = get_settings()
    configure_logging(
        log_level=settings.log_level,
        json_output=settings.env != "development",
    )

    logger.info(
        "application_starting",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.env,
    )

    # Initialize Weaviate
    weaviate_service = WeaviateService(settings)
    try:
        weaviate_service.connect()
        weaviate_service.ensure_collections()
    except VectorStoreConnectionError as exc:
        logger.warning(
            "weaviate_connection_failed_startup",
            error=str(exc),
            detail="Application will start in degraded mode. Weaviate operations will fail.",
        )

    # Initialize LLM Service
    llm_service: LLMService | None = None
    try:
        llm_service = LLMService(settings)
    except RatingIntelligenceError as exc:
        logger.warning(
            "llm_service_initialization_failed",
            error=str(exc),
            detail="Application will start in degraded mode. LLM operations will fail.",
        )

    # Initialize Document Processor
    document_processor = DocumentProcessor(settings)

    # Initialize Rating Pipeline
    rating_pipeline: RatingPipeline | None = None
    if llm_service:
        rating_pipeline = RatingPipeline(
            weaviate_service=weaviate_service,
            llm_service=llm_service,
            settings=settings,
        )

    # Store services in application state for dependency injection
    app.state.settings = settings
    app.state.weaviate_service = weaviate_service
    app.state.llm_service = llm_service
    app.state.document_processor = document_processor
    app.state.rating_pipeline = rating_pipeline

    logger.info("application_started", app_name=settings.app_name)

    yield

    # Shutdown
    logger.info("application_shutting_down")
    if llm_service:
        final_usage = llm_service.reset_usage()
        logger.info("final_token_usage", **final_usage)
    weaviate_service.disconnect()
    logger.info("application_stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance.

    Returns:
        Fully configured FastAPI application with routes, middleware, and
        lifecycle management.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "RAG-powered credit research assistant for CRISIL rating analysts. "
            "Provides semantic methodology search, draft credit assessment generation, "
            "peer comparison analysis, and surveillance alert drafting."
        ),
        lifespan=lifespan,
    )

    # CORS middleware
    cors_config = settings.yaml_config.get("api", {}).get("cors", {})
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_config.get("allowed_origins", ["*"]),
        allow_credentials=True,
        allow_methods=cors_config.get("allowed_methods", ["*"]),
        allow_headers=cors_config.get("allowed_headers", ["*"]),
    )

    # Correlation ID middleware
    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next) -> Response:
        """Inject a correlation ID into every request's logging context."""
        incoming_id = request.headers.get("X-Correlation-ID")
        cid = set_correlation_id(incoming_id)
        response: Response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        clear_correlation_id()
        return response

    # Register routes
    app.include_router(router)

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
