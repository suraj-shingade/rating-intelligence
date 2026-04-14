"""Document processing and chunking service.

Handles reading, parsing, chunking, and metadata extraction for documents
destined for Weaviate ingestion. Supports markdown, text, and JSON formats
with configurable chunking strategies.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import AppSettings
from src.exceptions import DocumentParsingError, UnsupportedDocumentTypeError
from src.logging_config import get_logger
from src.models.domain import (
    DocumentChunk,
    DocumentMetadata,
    DocumentType,
    Sector,
)

logger = get_logger(__name__)


class DocumentProcessor:
    """Processes raw documents into chunked, metadata-enriched objects for ingestion.

    Implements a configurable chunking strategy using LangChain's text splitters,
    with automatic metadata extraction based on document content and file naming
    conventions.
    """

    def __init__(self, settings: AppSettings) -> None:
        """Initialize the document processor.

        Args:
            settings: Application settings containing chunk size and overlap parameters.
        """
        self._settings = settings
        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.document_processing.chunk_size,
            chunk_overlap=settings.document_processing.chunk_overlap,
            length_function=len,
            separators=["\n## ", "\n### ", "\n#### ", "\n\n", "\n", ". ", " ", ""],
        )
        self._supported_extensions = settings.document_processing.supported_extensions

    def process_file(
        self,
        file_path: str,
        document_type: DocumentType,
        metadata_overrides: dict[str, Any] | None = None,
    ) -> list[DocumentChunk]:
        """Process a single file into document chunks with metadata.

        Args:
            file_path: Absolute or relative path to the file.
            document_type: Classification of the document.
            metadata_overrides: Optional metadata fields to override auto-detected values.

        Returns:
            List of DocumentChunk objects ready for Weaviate ingestion.

        Raises:
            UnsupportedDocumentTypeError: If the file extension is not supported.
            DocumentParsingError: If the file cannot be read or parsed.
        """
        path = Path(file_path)
        extension = path.suffix.lower()

        if extension not in self._supported_extensions:
            raise UnsupportedDocumentTypeError(
                file_path=str(path),
                supported_types=self._supported_extensions,
            )

        try:
            content = self._read_file(path, extension)
        except Exception as exc:
            raise DocumentParsingError(file_path=str(path), cause=exc) from exc

        metadata = self._extract_metadata(
            content=content,
            file_path=path,
            document_type=document_type,
            overrides=metadata_overrides or {},
        )

        chunks = self._chunk_content(content, metadata)

        logger.info(
            "file_processed",
            file_path=str(path),
            document_type=document_type,
            chunks_created=len(chunks),
        )

        return chunks

    def process_directory(
        self,
        directory_path: str,
        document_type: DocumentType,
        metadata_overrides: dict[str, Any] | None = None,
    ) -> list[DocumentChunk]:
        """Process all supported files in a directory.

        Args:
            directory_path: Path to the directory containing documents.
            document_type: Classification for all documents in the directory.
            metadata_overrides: Optional metadata fields to apply to all documents.

        Returns:
            Aggregated list of DocumentChunk objects from all processed files.

        Raises:
            DocumentParsingError: If the directory cannot be read.
        """
        dir_path = Path(directory_path)
        if not dir_path.is_dir():
            raise DocumentParsingError(
                file_path=str(dir_path),
                cause=FileNotFoundError(f"Directory not found: {dir_path}"),
            )

        all_chunks: list[DocumentChunk] = []
        errors: list[str] = []

        for file_path in sorted(dir_path.iterdir()):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in self._supported_extensions:
                continue

            try:
                chunks = self.process_file(
                    file_path=str(file_path),
                    document_type=document_type,
                    metadata_overrides=metadata_overrides,
                )
                all_chunks.extend(chunks)
            except Exception as exc:
                error_msg = f"Failed to process {file_path.name}: {exc}"
                errors.append(error_msg)
                logger.warning("file_processing_failed", file=str(file_path), error=str(exc))

        logger.info(
            "directory_processed",
            directory=str(dir_path),
            files_processed=len(all_chunks),
            errors=len(errors),
        )

        return all_chunks

    def _read_file(self, path: Path, extension: str) -> str:
        """Read file content based on extension.

        Args:
            path: Path to the file.
            extension: File extension (lowercase, with dot).

        Returns:
            The file's text content.

        Raises:
            DocumentParsingError: If the file cannot be read.
        """
        try:
            if extension == ".json":
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return self._json_to_text(data)
            else:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
        except Exception as exc:
            raise DocumentParsingError(file_path=str(path), cause=exc) from exc

    def _json_to_text(self, data: Any, prefix: str = "") -> str:
        """Convert a JSON structure to a flat text representation for embedding.

        Recursively flattens nested JSON into key-value text lines suitable
        for semantic embedding.

        Args:
            data: Parsed JSON data (dict, list, or primitive).
            prefix: Key prefix for nested structures.

        Returns:
            Flat text representation of the JSON data.
        """
        lines: list[str] = []

        if isinstance(data, dict):
            for key, value in data.items():
                full_key = f"{prefix}.{key}" if prefix else key
                if isinstance(value, (dict, list)):
                    lines.append(self._json_to_text(value, full_key))
                else:
                    lines.append(f"{full_key}: {value}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                item_prefix = f"{prefix}[{i}]"
                if isinstance(item, (dict, list)):
                    lines.append(self._json_to_text(item, item_prefix))
                else:
                    lines.append(f"{item_prefix}: {item}")
        else:
            lines.append(f"{prefix}: {data}" if prefix else str(data))

        return "\n".join(lines)

    def _extract_metadata(
        self,
        content: str,
        file_path: Path,
        document_type: DocumentType,
        overrides: dict[str, Any],
    ) -> DocumentMetadata:
        """Extract metadata from document content and file path.

        Combines heuristic content analysis with filename conventions and
        explicit overrides to produce a complete DocumentMetadata instance.

        Args:
            content: The document's text content.
            file_path: Path to the source file.
            document_type: Classification of the document.
            overrides: Explicit metadata values to apply.

        Returns:
            Populated DocumentMetadata instance.
        """
        sector = self._detect_sector(content, file_path)
        source_document = file_path.name

        metadata = DocumentMetadata(
            document_type=document_type,
            sector=sector,
            source_document=source_document,
        )

        # Apply filename-based heuristics
        filename_lower = file_path.stem.lower()
        if "manufacturing" in filename_lower or "industrial" in filename_lower:
            metadata.sector = Sector.MANUFACTURING
            metadata.sub_sector = self._detect_sub_sector(content, Sector.MANUFACTURING)
        elif "financial" in filename_lower or "banking" in filename_lower:
            metadata.sector = Sector.FINANCIAL
            metadata.sub_sector = self._detect_sub_sector(content, Sector.FINANCIAL)
        elif "infra" in filename_lower:
            metadata.sector = Sector.INFRASTRUCTURE
        elif "pharma" in filename_lower:
            metadata.sector = Sector.PHARMA

        # Apply explicit overrides
        for key, value in overrides.items():
            if hasattr(metadata, key) and value:
                setattr(metadata, key, value)

        return metadata

    def _detect_sector(self, content: str, file_path: Path) -> Sector:
        """Detect the sector classification from content keywords.

        Args:
            content: Document text content.
            file_path: Path to the source file.

        Returns:
            Detected Sector enumeration value.
        """
        content_lower = content.lower()
        yaml_config = self._settings.yaml_config
        sector_keywords = (
            yaml_config.get("document_processing", {})
            .get("metadata_extraction", {})
            .get("sector_keywords", {})
        )

        for sector_key, keywords in sector_keywords.items():
            match_count = sum(1 for kw in keywords if kw in content_lower)
            if match_count >= 2:
                try:
                    return Sector(sector_key)
                except ValueError:
                    continue

        return Sector.OTHER

    def _detect_sub_sector(self, content: str, sector: Sector) -> str:
        """Detect sub-sector classification from content.

        Args:
            content: Document text content.
            sector: Parent sector classification.

        Returns:
            Detected sub-sector string, or empty string if none detected.
        """
        content_lower = content.lower()

        sub_sector_map: dict[Sector, dict[str, list[str]]] = {
            Sector.MANUFACTURING: {
                "steel": ["steel", "iron ore", "blast furnace", "hot-rolled", "cold-rolled"],
                "cement": ["cement", "clinker", "ready-mix"],
                "automotive": ["automotive", "automobile", "vehicle", "OEM"],
                "chemicals": ["chemicals", "petrochemical", "specialty chemical"],
                "textiles": ["textile", "yarn", "fabric", "apparel"],
            },
            Sector.FINANCIAL: {
                "banking": ["bank", "lending", "deposits", "NPA", "CASA"],
                "nbfc": ["nbfc", "non-banking", "microfinance", "housing finance"],
                "insurance": ["insurance", "premium", "underwriting", "claims ratio"],
            },
        }

        if sector not in sub_sector_map:
            return ""

        for sub_sector, keywords in sub_sector_map[sector].items():
            match_count = sum(1 for kw in keywords if kw.lower() in content_lower)
            if match_count >= 2:
                return sub_sector

        return ""

    def _chunk_content(
        self,
        content: str,
        metadata: DocumentMetadata,
    ) -> list[DocumentChunk]:
        """Split content into chunks and attach metadata to each.

        Args:
            content: Full document text content.
            metadata: Metadata to attach to each chunk.

        Returns:
            List of DocumentChunk objects with sequential chunk indices.
        """
        text_chunks = self._text_splitter.split_text(content)

        return [
            DocumentChunk(
                content=chunk_text,
                chunk_index=idx,
                metadata=metadata,
            )
            for idx, chunk_text in enumerate(text_chunks)
        ]
