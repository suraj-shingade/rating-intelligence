"""Weaviate vector database service.

Manages schema creation, document ingestion, and semantic search operations
against the Weaviate instance. Uses the weaviate-client v4 API with typed
collection access and hybrid search capabilities.
"""

from __future__ import annotations

import time
from typing import Any

import weaviate
import weaviate.classes.config as wvc
import weaviate.classes.query as wvq
from weaviate.classes.init import Auth

from src.config import AppSettings
from src.exceptions import (
    CollectionCreationError,
    DocumentIngestionError,
    SearchError,
    VectorStoreConnectionError,
)
from src.logging_config import get_logger
from src.models.domain import DocumentChunk, DocumentType, SearchResult

logger = get_logger(__name__)


class WeaviateService:
    """Service for all Weaviate vector database operations.

    Handles connection lifecycle, collection schema management, document
    ingestion with batch processing, and hybrid semantic search.
    """

    _COLLECTION_MAP: dict[str, str] = {
        DocumentType.RATING_METHODOLOGY: "RatingMethodology",
        DocumentType.PRECEDENT_RATING: "PrecedentRating",
        DocumentType.INDUSTRY_REPORT: "IndustryReport",
    }

    def __init__(self, settings: AppSettings) -> None:
        """Initialize the Weaviate service.

        Args:
            settings: Application settings containing Weaviate connection parameters.
        """
        self._settings = settings
        self._client: weaviate.WeaviateClient | None = None

    def connect(self) -> None:
        """Establish connection to the Weaviate instance.

        Raises:
            VectorStoreConnectionError: If the connection cannot be established.
        """
        host = self._settings.weaviate.host
        http_port = self._settings.weaviate.http_port
        grpc_port = self._settings.weaviate.grpc_port

        try:
            self._client = weaviate.connect_to_local(
                host=host,
                port=http_port,
                grpc_port=grpc_port,
            )
            logger.info(
                "weaviate_connected",
                host=host,
                http_port=http_port,
                grpc_port=grpc_port,
            )
        except Exception as exc:
            raise VectorStoreConnectionError(host, http_port, cause=exc) from exc

    def disconnect(self) -> None:
        """Close the Weaviate client connection."""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("weaviate_disconnected")

    @property
    def client(self) -> weaviate.WeaviateClient:
        """Access the active Weaviate client.

        Returns:
            The connected WeaviateClient instance.

        Raises:
            VectorStoreConnectionError: If the client is not connected.
        """
        if self._client is None:
            raise VectorStoreConnectionError(
                self._settings.weaviate.host,
                self._settings.weaviate.http_port,
            )
        return self._client

    def ensure_collections(self) -> None:
        """Create all required Weaviate collections if they do not already exist.

        Reads collection schemas from YAML configuration and creates collections
        with appropriate property definitions and vectorizer configuration.

        Raises:
            CollectionCreationError: If any collection cannot be created.
        """
        collection_configs = {
            "rating_methodology": self._build_methodology_collection,
            "precedent_rating": self._build_precedent_collection,
            "industry_report": self._build_report_collection,
        }

        for config_key, builder_fn in collection_configs.items():
            try:
                yaml_config = self._settings.get_collection_config(config_key)
                collection_name = yaml_config["name"]

                if self.client.collections.exists(collection_name):
                    logger.info(
                        "collection_exists",
                        collection=collection_name,
                    )
                    continue

                builder_fn(collection_name)
                logger.info(
                    "collection_created",
                    collection=collection_name,
                )
            except Exception as exc:
                raise CollectionCreationError(
                    config_key,
                    cause=exc,
                ) from exc

    def _build_methodology_collection(self, name: str) -> None:
        """Create the RatingMethodology collection schema.

        Args:
            name: Collection name to create.
        """
        self.client.collections.create(
            name=name,
            vectorizer_config=wvc.Configure.Vectorizer.text2vec_transformers(),
            properties=[
                wvc.Property(name="content", data_type=wvc.DataType.TEXT),
                wvc.Property(name="sector", data_type=wvc.DataType.TEXT),
                wvc.Property(name="sub_sector", data_type=wvc.DataType.TEXT),
                wvc.Property(name="version", data_type=wvc.DataType.TEXT),
                wvc.Property(name="effective_date", data_type=wvc.DataType.TEXT),
                wvc.Property(name="rating_scale_type", data_type=wvc.DataType.TEXT),
                wvc.Property(name="source_document", data_type=wvc.DataType.TEXT),
                wvc.Property(name="chunk_index", data_type=wvc.DataType.INT),
            ],
        )

    def _build_precedent_collection(self, name: str) -> None:
        """Create the PrecedentRating collection schema.

        Args:
            name: Collection name to create.
        """
        self.client.collections.create(
            name=name,
            vectorizer_config=wvc.Configure.Vectorizer.text2vec_transformers(),
            properties=[
                wvc.Property(name="content", data_type=wvc.DataType.TEXT),
                wvc.Property(name="entity_name", data_type=wvc.DataType.TEXT),
                wvc.Property(name="sector", data_type=wvc.DataType.TEXT),
                wvc.Property(name="rating_assigned", data_type=wvc.DataType.TEXT),
                wvc.Property(name="rating_date", data_type=wvc.DataType.TEXT),
                wvc.Property(name="rating_action", data_type=wvc.DataType.TEXT),
                wvc.Property(name="key_drivers", data_type=wvc.DataType.TEXT),
                wvc.Property(name="financial_summary", data_type=wvc.DataType.TEXT),
            ],
        )

    def _build_report_collection(self, name: str) -> None:
        """Create the IndustryReport collection schema.

        Args:
            name: Collection name to create.
        """
        self.client.collections.create(
            name=name,
            vectorizer_config=wvc.Configure.Vectorizer.text2vec_transformers(),
            properties=[
                wvc.Property(name="content", data_type=wvc.DataType.TEXT),
                wvc.Property(name="sector", data_type=wvc.DataType.TEXT),
                wvc.Property(name="report_date", data_type=wvc.DataType.TEXT),
                wvc.Property(name="report_type", data_type=wvc.DataType.TEXT),
                wvc.Property(name="key_themes", data_type=wvc.DataType.TEXT),
                wvc.Property(name="source_document", data_type=wvc.DataType.TEXT),
                wvc.Property(name="chunk_index", data_type=wvc.DataType.INT),
            ],
        )

    def ingest_chunks(
        self,
        chunks: list[DocumentChunk],
        document_type: DocumentType,
    ) -> int:
        """Ingest document chunks into the appropriate Weaviate collection.

        Uses batch processing for efficient bulk ingestion. Each chunk's metadata
        is mapped to the collection's property schema.

        Args:
            chunks: List of processed document chunks to ingest.
            document_type: Type classification determining target collection.

        Returns:
            Number of chunks successfully ingested.

        Raises:
            DocumentIngestionError: If the batch ingestion fails.
        """
        collection_name = self._COLLECTION_MAP.get(document_type)
        if not collection_name:
            raise DocumentIngestionError(
                document_source=document_type,
                cause=ValueError(f"Unknown document type: {document_type}"),
            )

        collection = self.client.collections.get(collection_name)
        ingested_count = 0
        source = chunks[0].metadata.source_document if chunks else "unknown"

        try:
            with collection.batch.dynamic() as batch:
                for chunk in chunks:
                    properties = self._chunk_to_properties(chunk, document_type)
                    batch.add_object(properties=properties)
                    ingested_count += 1

            logger.info(
                "chunks_ingested",
                collection=collection_name,
                count=ingested_count,
                source=source,
            )
            return ingested_count

        except Exception as exc:
            raise DocumentIngestionError(
                document_source=source,
                chunk_count=len(chunks),
                cause=exc,
            ) from exc

    def _chunk_to_properties(
        self,
        chunk: DocumentChunk,
        document_type: DocumentType,
    ) -> dict[str, Any]:
        """Convert a DocumentChunk to Weaviate collection properties.

        Args:
            chunk: The document chunk to convert.
            document_type: Type classification for property mapping.

        Returns:
            Dictionary of property name-value pairs for Weaviate insertion.
        """
        meta = chunk.metadata
        base_props: dict[str, Any] = {"content": chunk.content}

        if document_type == DocumentType.RATING_METHODOLOGY:
            base_props.update(
                {
                    "sector": meta.sector,
                    "sub_sector": meta.sub_sector,
                    "version": meta.version,
                    "effective_date": meta.effective_date,
                    "rating_scale_type": meta.rating_scale_type,
                    "source_document": meta.source_document,
                    "chunk_index": chunk.chunk_index,
                }
            )
        elif document_type == DocumentType.PRECEDENT_RATING:
            base_props.update(
                {
                    "entity_name": meta.entity_name,
                    "sector": meta.sector,
                    "rating_assigned": meta.rating_assigned,
                    "rating_date": meta.rating_date,
                    "rating_action": meta.rating_action,
                    "key_drivers": meta.key_drivers,
                    "financial_summary": meta.financial_summary,
                }
            )
        elif document_type == DocumentType.INDUSTRY_REPORT:
            base_props.update(
                {
                    "sector": meta.sector,
                    "report_date": meta.report_date,
                    "report_type": meta.report_type,
                    "key_themes": meta.key_themes,
                    "source_document": meta.source_document,
                    "chunk_index": chunk.chunk_index,
                }
            )

        return base_props

    def search(
        self,
        query: str,
        collection_name: str,
        limit: int | None = None,
        filters: dict[str, str] | None = None,
    ) -> list[SearchResult]:
        """Execute a hybrid semantic search against a Weaviate collection.

        Combines dense vector similarity with BM25 keyword matching, weighted
        by the configured hybrid_alpha parameter.

        Args:
            query: Natural language search query.
            collection_name: Target collection to search.
            limit: Maximum number of results. Defaults to configured default.
            filters: Optional metadata filters as property-value pairs.

        Returns:
            List of SearchResult objects ranked by relevance.

        Raises:
            SearchError: If the search operation fails.
        """
        effective_limit = min(
            limit or self._settings.weaviate.default_search_limit,
            self._settings.weaviate.max_search_limit,
        )

        try:
            collection = self.client.collections.get(collection_name)

            weaviate_filters = self._build_filters(filters) if filters else None

            start_time = time.monotonic()

            response = collection.query.hybrid(
                query=query,
                alpha=self._settings.weaviate.hybrid_alpha,
                limit=effective_limit,
                filters=weaviate_filters,
                return_metadata=wvq.MetadataQuery(score=True, distance=True),
            )

            elapsed_ms = (time.monotonic() - start_time) * 1000

            results: list[SearchResult] = []
            for obj in response.objects:
                properties = obj.properties
                content = properties.pop("content", "")
                score = obj.metadata.score if obj.metadata and obj.metadata.score else 0.0

                results.append(
                    SearchResult(
                        content=content,
                        score=score,
                        metadata=properties,
                    )
                )

            logger.info(
                "search_completed",
                collection=collection_name,
                query_length=len(query),
                results_count=len(results),
                elapsed_ms=round(elapsed_ms, 2),
            )

            return results

        except Exception as exc:
            raise SearchError(query, cause=exc) from exc

    def _build_filters(
        self,
        filters: dict[str, str],
    ) -> wvq.Filter | None:
        """Build a Weaviate filter from a dictionary of property-value pairs.

        Combines multiple filters with AND logic.

        Args:
            filters: Dictionary of property names to expected values.

        Returns:
            A composed Weaviate Filter, or None if the input is empty.
        """
        if not filters:
            return None

        filter_clauses = []
        for prop_name, prop_value in filters.items():
            filter_clauses.append(
                wvq.Filter.by_property(prop_name).equal(prop_value)
            )

        if len(filter_clauses) == 1:
            return filter_clauses[0]

        combined = filter_clauses[0]
        for clause in filter_clauses[1:]:
            combined = combined & clause

        return combined

    def search_methodologies(
        self,
        query: str,
        sector: str | None = None,
        rating_scale_type: str | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Search the RatingMethodology collection with optional sector filtering.

        Convenience method wrapping the generic search with methodology-specific
        filter construction.

        Args:
            query: Natural language search query.
            sector: Optional sector filter.
            rating_scale_type: Optional rating scale type filter.
            limit: Maximum results to return.

        Returns:
            List of SearchResult objects from the methodology collection.
        """
        filters: dict[str, str] = {}
        if sector:
            filters["sector"] = sector
        if rating_scale_type:
            filters["rating_scale_type"] = rating_scale_type

        return self.search(
            query=query,
            collection_name="RatingMethodology",
            limit=limit,
            filters=filters or None,
        )

    def search_precedent_ratings(
        self,
        query: str,
        sector: str | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Search the PrecedentRating collection for relevant historical ratings.

        Args:
            query: Natural language search query describing the rating scenario.
            sector: Optional sector filter.
            limit: Maximum results to return.

        Returns:
            List of SearchResult objects from the precedent rating collection.
        """
        filters: dict[str, str] = {}
        if sector:
            filters["sector"] = sector

        return self.search(
            query=query,
            collection_name="PrecedentRating",
            limit=limit,
            filters=filters or None,
        )

    def search_industry_reports(
        self,
        query: str,
        sector: str | None = None,
        limit: int = 5,
    ) -> list[SearchResult]:
        """Search the IndustryReport collection for sector context.

        Args:
            query: Natural language search query.
            sector: Optional sector filter.
            limit: Maximum results to return.

        Returns:
            List of SearchResult objects from the industry report collection.
        """
        filters: dict[str, str] = {}
        if sector:
            filters["sector"] = sector

        return self.search(
            query=query,
            collection_name="IndustryReport",
            limit=limit,
            filters=filters or None,
        )

    def get_collection_counts(self) -> dict[str, int]:
        """Retrieve object counts for all managed collections.

        Returns:
            Dictionary mapping collection names to their object counts.
        """
        counts: dict[str, int] = {}
        for collection_name in self._COLLECTION_MAP.values():
            try:
                if self.client.collections.exists(collection_name):
                    collection = self.client.collections.get(collection_name)
                    aggregate = collection.aggregate.over_all(total_count=True)
                    counts[collection_name] = aggregate.total_count or 0
                else:
                    counts[collection_name] = 0
            except Exception:
                logger.warning(
                    "collection_count_failed",
                    collection=collection_name,
                )
                counts[collection_name] = -1

        return counts

    def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection and all its data. Use with caution.

        Args:
            collection_name: Name of the collection to delete.

        Returns:
            True if the collection was deleted, False if it did not exist.
        """
        if self.client.collections.exists(collection_name):
            self.client.collections.delete(collection_name)
            logger.warning("collection_deleted", collection=collection_name)
            return True
        return False
