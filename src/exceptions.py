"""Custom exception hierarchy for the Rating Methodology Intelligence System.

All application-specific exceptions derive from RatingIntelligenceError,
enabling granular error handling while preserving exception chaining for
root-cause traceability.
"""

from __future__ import annotations


class RatingIntelligenceError(Exception):
    """Base exception for all Rating Intelligence System errors.

    All custom exceptions in this application inherit from this class,
    enabling catch-all handling at API boundaries while preserving
    specific exception types for targeted recovery logic.
    """

    def __init__(self, message: str, *args: object) -> None:
        self.message = message
        super().__init__(message, *args)


# -- Vector Store Exceptions --------------------------------------------------


class VectorStoreError(RatingIntelligenceError):
    """Base exception for Weaviate vector store operations."""

    pass


class VectorStoreConnectionError(VectorStoreError):
    """Raised when the application cannot establish a connection to Weaviate."""

    def __init__(self, host: str, port: int, cause: Exception | None = None) -> None:
        message = f"Failed to connect to Weaviate at {host}:{port}"
        if cause:
            message += f" -- {cause}"
        super().__init__(message)
        if cause:
            self.__cause__ = cause


class CollectionCreationError(VectorStoreError):
    """Raised when a Weaviate collection cannot be created or configured."""

    def __init__(self, collection_name: str, cause: Exception | None = None) -> None:
        message = f"Failed to create collection '{collection_name}'"
        if cause:
            message += f" -- {cause}"
        super().__init__(message)
        if cause:
            self.__cause__ = cause


class DocumentIngestionError(VectorStoreError):
    """Raised when document ingestion into Weaviate fails."""

    def __init__(
        self,
        document_source: str,
        chunk_count: int = 0,
        cause: Exception | None = None,
    ) -> None:
        message = f"Failed to ingest document '{document_source}'"
        if chunk_count:
            message += f" ({chunk_count} chunks)"
        if cause:
            message += f" -- {cause}"
        super().__init__(message)
        if cause:
            self.__cause__ = cause


class SearchError(VectorStoreError):
    """Raised when a semantic search query fails."""

    def __init__(self, query: str, cause: Exception | None = None) -> None:
        truncated = query[:100] + "..." if len(query) > 100 else query
        message = f"Search failed for query: '{truncated}'"
        if cause:
            message += f" -- {cause}"
        super().__init__(message)
        if cause:
            self.__cause__ = cause


# -- LLM Exceptions -----------------------------------------------------------


class LLMError(RatingIntelligenceError):
    """Base exception for LLM-related operations."""

    pass


class LLMConnectionError(LLMError):
    """Raised when the application cannot connect to the Anthropic API."""

    def __init__(self, model: str, cause: Exception | None = None) -> None:
        message = f"Failed to connect to Anthropic model '{model}'"
        if cause:
            message += f" -- {cause}"
        super().__init__(message)
        if cause:
            self.__cause__ = cause


class LLMGenerationError(LLMError):
    """Raised when LLM content generation fails."""

    def __init__(self, operation: str, cause: Exception | None = None) -> None:
        message = f"LLM generation failed for operation '{operation}'"
        if cause:
            message += f" -- {cause}"
        super().__init__(message)
        if cause:
            self.__cause__ = cause


class LLMTokenLimitError(LLMError):
    """Raised when input exceeds the model's context window."""

    def __init__(
        self,
        token_count: int,
        max_tokens: int,
        cause: Exception | None = None,
    ) -> None:
        message = (
            f"Input token count ({token_count}) exceeds model limit ({max_tokens})"
        )
        super().__init__(message)
        if cause:
            self.__cause__ = cause


# -- Document Processing Exceptions -------------------------------------------


class DocumentProcessingError(RatingIntelligenceError):
    """Base exception for document processing operations."""

    pass


class UnsupportedDocumentTypeError(DocumentProcessingError):
    """Raised when an unsupported document file type is submitted for processing."""

    def __init__(self, file_path: str, supported_types: list[str]) -> None:
        message = (
            f"Unsupported document type for '{file_path}'. "
            f"Supported types: {', '.join(supported_types)}"
        )
        super().__init__(message)


class DocumentParsingError(DocumentProcessingError):
    """Raised when a document cannot be parsed or chunked."""

    def __init__(self, file_path: str, cause: Exception | None = None) -> None:
        message = f"Failed to parse document '{file_path}'"
        if cause:
            message += f" -- {cause}"
        super().__init__(message)
        if cause:
            self.__cause__ = cause


# -- Pipeline Exceptions ------------------------------------------------------


class PipelineError(RatingIntelligenceError):
    """Base exception for analytical pipeline operations."""

    pass


class InsufficientContextError(PipelineError):
    """Raised when retrieved context is insufficient for analysis."""

    def __init__(self, operation: str, retrieved_count: int, minimum_required: int) -> None:
        message = (
            f"Insufficient context for '{operation}': "
            f"retrieved {retrieved_count} results, minimum required {minimum_required}"
        )
        super().__init__(message)


class PipelineExecutionError(PipelineError):
    """Raised when a LangChain pipeline execution fails."""

    def __init__(self, chain_name: str, cause: Exception | None = None) -> None:
        message = f"Pipeline execution failed for chain '{chain_name}'"
        if cause:
            message += f" -- {cause}"
        super().__init__(message)
        if cause:
            self.__cause__ = cause


# -- Configuration Exceptions -------------------------------------------------


class ConfigurationError(RatingIntelligenceError):
    """Raised when application configuration is invalid or missing."""

    def __init__(self, config_key: str, detail: str = "") -> None:
        message = f"Configuration error for '{config_key}'"
        if detail:
            message += f": {detail}"
        super().__init__(message)
