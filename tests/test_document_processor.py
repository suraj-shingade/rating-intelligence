from __future__ import annotations

import json

import pytest

from src.config import get_settings
from src.exceptions import UnsupportedDocumentTypeError
from src.models.domain import DocumentType, Sector
from src.services.document_processor import DocumentProcessor


@pytest.fixture
def processor() -> DocumentProcessor:
    get_settings.cache_clear()
    return DocumentProcessor(get_settings())


def test_process_file_detects_manufacturing_metadata(
    processor: DocumentProcessor,
    tmp_path,
) -> None:
    document = tmp_path / "manufacturing_criteria.md"
    document.write_text(
        "## Steel methodology\n"
        "Manufacturing companies operating in the steel and iron ore sectors.\n",
        encoding="utf-8",
    )

    chunks = processor.process_file(
        str(document),
        DocumentType.RATING_METHODOLOGY,
    )

    assert len(chunks) == 1
    assert chunks[0].metadata.sector == Sector.MANUFACTURING
    assert chunks[0].metadata.sub_sector == "steel"
    assert chunks[0].metadata.source_document == document.name


def test_process_file_flattens_json_for_embedding(
    processor: DocumentProcessor,
    tmp_path,
) -> None:
    document = tmp_path / "company.json"
    document.write_text(
        json.dumps({"company": {"name": "Acme", "metrics": [1, 2]}}),
        encoding="utf-8",
    )

    chunks = processor.process_file(str(document), DocumentType.INDUSTRY_REPORT)

    assert len(chunks) == 1
    assert "company.name: Acme" in chunks[0].content
    assert "company.metrics[1]: 2" in chunks[0].content


def test_process_file_rejects_unsupported_extension(
    processor: DocumentProcessor,
    tmp_path,
) -> None:
    document = tmp_path / "criteria.pdf"
    document.write_text("not a real PDF", encoding="utf-8")

    with pytest.raises(UnsupportedDocumentTypeError):
        processor.process_file(str(document), DocumentType.RATING_METHODOLOGY)
