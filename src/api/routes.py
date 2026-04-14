"""FastAPI route definitions for the Rating Methodology Intelligence System.

Defines all REST API endpoints for semantic search, credit assessment generation,
peer comparison, surveillance alerting, document ingestion, and health monitoring.
Each endpoint enforces Pydantic validation, manages correlation IDs, and maps
domain exceptions to appropriate HTTP responses.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.exceptions import (
    DocumentProcessingError,
    InsufficientContextError,
    LLMError,
    PipelineExecutionError,
    RatingIntelligenceError,
    VectorStoreError,
)
from src.logging_config import get_correlation_id, get_logger, set_correlation_id
from src.models.domain import (
    CreditAssessment,
    IngestionRequest,
    IngestionResult,
    MethodologySearchRequest,
    MethodologySearchResult,
    PeerComparisonRequest,
    PeerComparisonResult,
    RatingRequest,
    SearchResult,
    SurveillanceAlertRequest,
    SurveillanceAlertResult,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Rating Intelligence"])


def _get_services(request: Request) -> dict[str, Any]:
    """Retrieve service instances from the application state.

    Args:
        request: The incoming FastAPI request (provides access to app.state).

    Returns:
        Dictionary containing weaviate_service, llm_service, rating_pipeline,
        document_processor, and settings.
    """
    return {
        "weaviate_service": request.app.state.weaviate_service,
        "llm_service": request.app.state.llm_service,
        "rating_pipeline": request.app.state.rating_pipeline,
        "document_processor": request.app.state.document_processor,
        "settings": request.app.state.settings,
    }


def _handle_domain_exception(exc: RatingIntelligenceError) -> HTTPException:
    """Map domain exceptions to appropriate HTTP error responses.

    Args:
        exc: The domain exception to map.

    Returns:
        An HTTPException with the appropriate status code and detail message.
    """
    if isinstance(exc, InsufficientContextError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        )
    if isinstance(exc, VectorStoreError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Vector store error: {exc.message}",
        )
    if isinstance(exc, LLMError):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM service error: {exc.message}",
        )
    if isinstance(exc, DocumentProcessingError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Document processing error: {exc.message}",
        )
    if isinstance(exc, PipelineExecutionError):
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline error: {exc.message}",
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=exc.message,
    )


# -- Health Check Endpoint -------------------------------------------------------


@router.get(
    "/health",
    summary="System health check",
    response_model=dict[str, Any],
)
async def health_check(request: Request) -> dict[str, Any]:
    """Return system health status including Weaviate connectivity and collection counts.

    Returns:
        Health status dictionary with component statuses and collection counts.
    """
    services = _get_services(request)
    weaviate_service = services["weaviate_service"]
    llm_service = services["llm_service"]

    weaviate_healthy = False
    collection_counts: dict[str, int] = {}

    try:
        collection_counts = weaviate_service.get_collection_counts()
        weaviate_healthy = all(count >= 0 for count in collection_counts.values())
    except Exception as exc:
        logger.warning("health_check_weaviate_failed", error=str(exc))

    llm_status = {"status": "unavailable", "model": services["settings"].anthropic.model}
    if llm_service:
        llm_status = {
            "status": "connected",
            "model": services["settings"].anthropic.model,
            "usage": llm_service.usage.to_dict(),
        }

    return {
        "status": "healthy" if weaviate_healthy else "degraded",
        "components": {
            "weaviate": {
                "status": "connected" if weaviate_healthy else "disconnected",
                "collections": collection_counts,
            },
            "llm": llm_status,
        },
        "version": services["settings"].app_version,
    }


# -- Methodology Search Endpoint -------------------------------------------------


@router.post(
    "/search/methodology",
    summary="Semantic search across rating methodologies",
    response_model=MethodologySearchResult,
)
async def search_methodology(
    request: Request,
    body: MethodologySearchRequest,
) -> MethodologySearchResult:
    """Search rating methodology documents using semantic similarity.

    Performs hybrid search (vector + keyword) against the RatingMethodology
    collection in Weaviate, returning ranked results with relevance scores
    and source attribution.

    Args:
        request: The incoming FastAPI request.
        body: Search parameters including query text and optional filters.

    Returns:
        Ranked methodology search results with metadata.
    """
    set_correlation_id()
    services = _get_services(request)
    weaviate_service = services["weaviate_service"]

    try:
        start_time = time.monotonic()

        sector_filter = body.sector.value if body.sector else None
        scale_filter = body.rating_scale_type.value if body.rating_scale_type else None

        results = weaviate_service.search_methodologies(
            query=body.query,
            sector=sector_filter,
            rating_scale_type=scale_filter,
            limit=body.limit,
        )

        elapsed_ms = (time.monotonic() - start_time) * 1000

        logger.info(
            "methodology_search_request",
            query_length=len(body.query),
            sector=sector_filter,
            results_count=len(results),
            elapsed_ms=round(elapsed_ms, 2),
        )

        return MethodologySearchResult(
            query=body.query,
            results=results,
            total_results=len(results),
            search_time_ms=round(elapsed_ms, 2),
        )

    except RatingIntelligenceError as exc:
        raise _handle_domain_exception(exc) from exc
    except Exception as exc:
        logger.error("methodology_search_failed", error=str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(exc)}",
        ) from exc


# -- Credit Assessment Endpoint --------------------------------------------------


@router.post(
    "/analysis/credit-assessment",
    summary="Generate a draft credit assessment",
    response_model=CreditAssessment,
)
async def generate_credit_assessment(
    request: Request,
    body: RatingRequest,
) -> CreditAssessment:
    """Generate a structured draft credit assessment for an entity.

    Retrieves relevant methodology criteria, analyzes financial data against
    rating thresholds, and generates a comprehensive draft assessment with
    evidence citations. The output is explicitly labeled as AI-generated draft
    content requiring analyst review.

    Args:
        request: The incoming FastAPI request.
        body: Rating request with company profile and financial data.

    Returns:
        Structured CreditAssessment with business/financial risk analysis,
        strengths, weaknesses, and methodology citations.
    """
    set_correlation_id()
    services = _get_services(request)
    pipeline = services["rating_pipeline"]

    try:
        logger.info(
            "credit_assessment_request",
            entity=body.company_profile.entity_name,
            sector=body.company_profile.sector.value,
        )

        assessment = await pipeline.credit_analysis_chain(
            company_profile=body.company_profile,
            additional_context=body.additional_context,
        )

        return assessment

    except RatingIntelligenceError as exc:
        raise _handle_domain_exception(exc) from exc
    except Exception as exc:
        logger.error(
            "credit_assessment_failed",
            entity=body.company_profile.entity_name,
            error=str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Assessment generation failed: {str(exc)}",
        ) from exc


# -- Peer Comparison Endpoint ----------------------------------------------------


@router.post(
    "/analysis/peer-comparison",
    summary="Generate peer comparison analysis",
    response_model=PeerComparisonResult,
)
async def generate_peer_comparison(
    request: Request,
    body: PeerComparisonRequest,
) -> PeerComparisonResult:
    """Compare an entity's financial profile against rated peers.

    Retrieves precedent ratings for comparable entities and generates a
    structured comparison covering relative financial positioning, qualitative
    differentiators, and methodology-relevant metrics.

    Args:
        request: The incoming FastAPI request.
        body: Peer comparison request with subject company profile.

    Returns:
        Structured PeerComparisonResult with comparative analysis.
    """
    set_correlation_id()
    services = _get_services(request)
    pipeline = services["rating_pipeline"]

    try:
        logger.info(
            "peer_comparison_request",
            entity=body.company_profile.entity_name,
            sector=(body.peer_sector or body.company_profile.sector).value,
        )

        result = await pipeline.peer_comparison_chain(request=body)
        return result

    except RatingIntelligenceError as exc:
        raise _handle_domain_exception(exc) from exc
    except Exception as exc:
        logger.error(
            "peer_comparison_failed",
            entity=body.company_profile.entity_name,
            error=str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Peer comparison failed: {str(exc)}",
        ) from exc


# -- Surveillance Alerts Endpoint ------------------------------------------------


@router.post(
    "/surveillance/alerts",
    summary="Generate surveillance alert memorandum",
    response_model=SurveillanceAlertResult,
)
async def generate_surveillance_alert(
    request: Request,
    body: SurveillanceAlertRequest,
) -> SurveillanceAlertResult:
    """Generate a surveillance alert memorandum based on financial triggers.

    Analyzes financial triggers against methodology thresholds and precedent
    rating actions to produce a structured alert memorandum with recommended
    surveillance actions.

    Args:
        request: The incoming FastAPI request.
        body: Surveillance alert request with entity data and triggers.

    Returns:
        Structured SurveillanceAlertResult with alert memorandum.
    """
    set_correlation_id()
    services = _get_services(request)
    pipeline = services["rating_pipeline"]

    try:
        logger.info(
            "surveillance_alert_request",
            entity=body.entity_name,
            current_rating=body.current_rating,
            triggers_count=len(body.financial_triggers),
        )

        result = await pipeline.surveillance_alert_chain(request=body)
        return result

    except RatingIntelligenceError as exc:
        raise _handle_domain_exception(exc) from exc
    except Exception as exc:
        logger.error(
            "surveillance_alert_failed",
            entity=body.entity_name,
            error=str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Surveillance alert generation failed: {str(exc)}",
        ) from exc


# -- Document Ingestion Endpoint -------------------------------------------------


@router.post(
    "/ingest/documents",
    summary="Ingest documents into the knowledge base",
    response_model=IngestionResult,
)
async def ingest_documents(
    request: Request,
    body: IngestionRequest,
) -> IngestionResult:
    """Ingest documents into the Weaviate vector store.

    Processes files or directories of documents, chunks them according to
    the configured strategy, enriches with extracted metadata, and inserts
    into the appropriate Weaviate collection.

    Args:
        request: The incoming FastAPI request.
        body: Ingestion request specifying file/directory path and document type.

    Returns:
        IngestionResult with processing statistics and any errors.
    """
    set_correlation_id()
    correlation_id = get_correlation_id()
    services = _get_services(request)
    doc_processor = services["document_processor"]
    weaviate_service = services["weaviate_service"]

    try:
        start_time = time.monotonic()

        if not body.file_path and not body.directory_path:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Either file_path or directory_path must be provided.",
            )

        if body.file_path:
            chunks = doc_processor.process_file(
                file_path=body.file_path,
                document_type=body.document_type,
                metadata_overrides=body.metadata_overrides or None,
            )
            documents_processed = 1
        else:
            chunks = doc_processor.process_directory(
                directory_path=body.directory_path,
                document_type=body.document_type,
                metadata_overrides=body.metadata_overrides or None,
            )
            documents_processed = len(
                set(c.metadata.source_document for c in chunks)
            )

        ingested_count = 0
        errors: list[str] = []

        if chunks:
            try:
                ingested_count = weaviate_service.ingest_chunks(
                    chunks=chunks,
                    document_type=body.document_type,
                )
            except Exception as exc:
                errors.append(f"Weaviate ingestion error: {str(exc)}")
                logger.error("ingestion_weaviate_failed", error=str(exc), exc_info=True)

        elapsed_ms = (time.monotonic() - start_time) * 1000

        logger.info(
            "document_ingestion_completed",
            documents_processed=documents_processed,
            chunks_created=len(chunks),
            chunks_ingested=ingested_count,
            errors_count=len(errors),
            elapsed_ms=round(elapsed_ms, 2),
        )

        return IngestionResult(
            documents_processed=documents_processed,
            chunks_created=len(chunks),
            chunks_ingested=ingested_count,
            errors=errors,
            processing_time_ms=round(elapsed_ms, 2),
            correlation_id=correlation_id,
        )

    except RatingIntelligenceError as exc:
        raise _handle_domain_exception(exc) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("document_ingestion_failed", error=str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(exc)}",
        ) from exc
