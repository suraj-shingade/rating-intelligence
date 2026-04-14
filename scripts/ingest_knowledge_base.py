"""Knowledge base ingestion script.

Processes and ingests all documents from the data/knowledge_base directory
into Weaviate, creating the initial knowledge base for the Rating Methodology
Intelligence System.

Usage:
    python -m scripts.ingest_knowledge_base
    python -m scripts.ingest_knowledge_base --directory data/knowledge_base/rating_methodologies
    python -m scripts.ingest_knowledge_base --reset
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Ensure project root is on the path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.config import get_settings
from src.exceptions import RatingIntelligenceError
from src.logging_config import configure_logging, get_logger, set_correlation_id
from src.models.domain import DocumentType
from src.services.document_processor import DocumentProcessor
from src.services.weaviate_service import WeaviateService

logger = get_logger(__name__)

_DATA_ROOT = project_root / "data" / "knowledge_base"

_INGESTION_MAP: list[dict] = [
    {
        "directory": "rating_methodologies",
        "document_type": DocumentType.RATING_METHODOLOGY,
        "description": "Rating methodology criteria documents",
    },
    {
        "directory": "sample_financials",
        "document_type": DocumentType.PRECEDENT_RATING,
        "description": "Sample financial and precedent rating data",
    },
]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed argument namespace.
    """
    parser = argparse.ArgumentParser(
        description="Ingest knowledge base documents into Weaviate vector store.",
    )
    parser.add_argument(
        "--directory",
        type=str,
        default="",
        help="Specific directory to ingest (relative to data/knowledge_base). "
             "If not specified, all configured directories are ingested.",
    )
    parser.add_argument(
        "--document-type",
        type=str,
        choices=[dt.value for dt in DocumentType],
        default="",
        help="Document type classification for the specified directory.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete all existing collections before ingestion. Data loss warning.",
    )
    return parser.parse_args()


def run_ingestion(
    weaviate_service: WeaviateService,
    document_processor: DocumentProcessor,
    directory: Path,
    document_type: DocumentType,
    description: str,
) -> dict[str, int]:
    """Run ingestion for a single directory.

    Args:
        weaviate_service: Weaviate service for chunk insertion.
        document_processor: Document processor for chunking.
        directory: Path to the directory containing documents.
        document_type: Classification for the documents.
        description: Human-readable description for logging.

    Returns:
        Dictionary with processing statistics.
    """
    logger.info(
        "ingestion_directory_start",
        directory=str(directory),
        document_type=document_type.value,
        description=description,
    )

    if not directory.is_dir():
        logger.warning(
            "ingestion_directory_not_found",
            directory=str(directory),
        )
        return {"documents": 0, "chunks_created": 0, "chunks_ingested": 0}

    chunks = document_processor.process_directory(
        directory_path=str(directory),
        document_type=document_type,
    )

    if not chunks:
        logger.info("ingestion_no_chunks", directory=str(directory))
        return {"documents": 0, "chunks_created": 0, "chunks_ingested": 0}

    unique_sources = set(c.metadata.source_document for c in chunks)
    ingested_count = weaviate_service.ingest_chunks(
        chunks=chunks,
        document_type=document_type,
    )

    logger.info(
        "ingestion_directory_complete",
        directory=str(directory),
        documents=len(unique_sources),
        chunks_created=len(chunks),
        chunks_ingested=ingested_count,
    )

    return {
        "documents": len(unique_sources),
        "chunks_created": len(chunks),
        "chunks_ingested": ingested_count,
    }


def main() -> None:
    """Execute the knowledge base ingestion pipeline."""
    args = parse_args()

    settings = get_settings()
    configure_logging(log_level=settings.log_level, json_output=False)
    set_correlation_id("ingest-kb")

    logger.info("knowledge_base_ingestion_starting")
    overall_start = time.monotonic()

    # Initialize services
    weaviate_service = WeaviateService(settings)
    document_processor = DocumentProcessor(settings)

    try:
        weaviate_service.connect()
    except RatingIntelligenceError as exc:
        logger.error("weaviate_connection_failed", error=str(exc))
        sys.exit(1)

    # Reset collections if requested
    if args.reset:
        logger.warning("resetting_all_collections")
        for collection_name in WeaviateService._COLLECTION_MAP.values():
            weaviate_service.delete_collection(collection_name)
        logger.info("collections_deleted")

    # Ensure collections exist
    try:
        weaviate_service.ensure_collections()
    except RatingIntelligenceError as exc:
        logger.error("collection_creation_failed", error=str(exc))
        sys.exit(1)

    # Determine ingestion targets
    targets = _INGESTION_MAP
    if args.directory:
        doc_type = (
            DocumentType(args.document_type) if args.document_type
            else DocumentType.RATING_METHODOLOGY
        )
        targets = [
            {
                "directory": args.directory,
                "document_type": doc_type,
                "description": f"User-specified: {args.directory}",
            }
        ]

    # Execute ingestion
    totals = {"documents": 0, "chunks_created": 0, "chunks_ingested": 0}

    for target in targets:
        directory = _DATA_ROOT / target["directory"]
        try:
            stats = run_ingestion(
                weaviate_service=weaviate_service,
                document_processor=document_processor,
                directory=directory,
                document_type=target["document_type"],
                description=target["description"],
            )
            for key in totals:
                totals[key] += stats[key]
        except RatingIntelligenceError as exc:
            logger.error(
                "ingestion_failed",
                directory=str(directory),
                error=str(exc),
            )

    # Report final statistics
    elapsed_s = time.monotonic() - overall_start

    collection_counts = weaviate_service.get_collection_counts()

    logger.info(
        "knowledge_base_ingestion_complete",
        total_documents=totals["documents"],
        total_chunks_created=totals["chunks_created"],
        total_chunks_ingested=totals["chunks_ingested"],
        elapsed_seconds=round(elapsed_s, 2),
        collection_counts=collection_counts,
    )

    weaviate_service.disconnect()

    print(f"\nIngestion Summary:")
    print(f"  Documents processed: {totals['documents']}")
    print(f"  Chunks created:      {totals['chunks_created']}")
    print(f"  Chunks ingested:     {totals['chunks_ingested']}")
    print(f"  Elapsed time:        {elapsed_s:.2f}s")
    print(f"\nCollection Counts:")
    for name, count in collection_counts.items():
        print(f"  {name}: {count}")


if __name__ == "__main__":
    main()
