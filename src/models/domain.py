"""Domain models for the Rating Methodology Intelligence System.

All request/response models, value objects, and domain entities used across
the application. Pydantic models enforce validation at system boundaries.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


# -- Enumerations -------------------------------------------------------------


class Sector(StrEnum):
    """Industry sector classification aligned with CRISIL's sector taxonomy."""

    MANUFACTURING = "manufacturing"
    FINANCIAL = "financial"
    INFRASTRUCTURE = "infrastructure"
    SERVICES = "services"
    REAL_ESTATE = "real_estate"
    POWER = "power"
    IT = "information_technology"
    PHARMA = "pharmaceuticals"
    OTHER = "other"


class RatingScale(StrEnum):
    """CRISIL rating scale types."""

    LONG_TERM = "long_term"
    SHORT_TERM = "short_term"
    BANK_LOAN = "bank_loan"


class RatingAction(StrEnum):
    """Types of rating actions."""

    NEW = "new"
    UPGRADE = "upgrade"
    DOWNGRADE = "downgrade"
    REAFFIRMATION = "reaffirmation"
    OUTLOOK_CHANGE = "outlook_change"
    WITHDRAWAL = "withdrawal"


class DocumentType(StrEnum):
    """Types of documents that can be ingested."""

    RATING_METHODOLOGY = "rating_methodology"
    PRECEDENT_RATING = "precedent_rating"
    INDUSTRY_REPORT = "industry_report"


# -- Financial Profile Models -------------------------------------------------


class FinancialMetrics(BaseModel):
    """Key financial metrics for credit analysis.

    All monetary values in INR crore unless otherwise specified.
    """

    revenue: float = Field(description="Total revenue (INR crore)")
    ebitda: float = Field(description="EBITDA (INR crore)")
    ebitda_margin: float = Field(description="EBITDA margin (percentage)")
    pat: float = Field(description="Profit after tax (INR crore)")
    total_debt: float = Field(description="Total debt (INR crore)")
    tangible_net_worth: float = Field(description="Tangible net worth (INR crore)")
    debt_to_equity: float = Field(description="Debt-to-equity ratio")
    interest_coverage: float = Field(description="Interest coverage ratio (EBITDA/interest)")
    current_ratio: float = Field(description="Current ratio")
    roce: float = Field(description="Return on capital employed (percentage)")
    debt_to_ebitda: float = Field(description="Debt-to-EBITDA ratio")
    dscr: float = Field(default=0.0, description="Debt service coverage ratio")
    cash_and_equivalents: float = Field(default=0.0, description="Cash and equivalents (INR crore)")
    fiscal_year: str = Field(description="Fiscal year of the financial data (e.g., FY2024)")


class CompanyProfile(BaseModel):
    """Complete company profile for credit assessment."""

    entity_name: str = Field(description="Legal name of the entity")
    sector: Sector = Field(description="Primary sector classification")
    sub_sector: str = Field(default="", description="Sub-sector classification")
    incorporation_year: int = Field(default=0, description="Year of incorporation")
    promoter_group: str = Field(default="", description="Promoter or parent group")
    management_experience_years: int = Field(
        default=0,
        description="Aggregate years of management experience in the industry",
    )
    market_position: str = Field(
        default="",
        description="Description of market position and competitive standing",
    )
    geographic_diversification: str = Field(
        default="",
        description="Geographic revenue diversification description",
    )
    product_diversification: str = Field(
        default="",
        description="Product or service diversification description",
    )
    key_customers: list[str] = Field(
        default_factory=list,
        description="Major customer names or descriptions",
    )
    financials: list[FinancialMetrics] = Field(
        description="Financial data for one or more fiscal years (most recent first)",
    )


# -- Search Models -------------------------------------------------------------


class MethodologySearchRequest(BaseModel):
    """Request model for semantic methodology search."""

    query: str = Field(
        description="Natural language search query",
        min_length=3,
        max_length=2000,
    )
    sector: Sector | None = Field(
        default=None,
        description="Filter results by sector",
    )
    rating_scale_type: RatingScale | None = Field(
        default=None,
        description="Filter results by rating scale type",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of results to return",
    )


class SearchResult(BaseModel):
    """A single search result with content and metadata."""

    content: str = Field(description="Retrieved text content")
    score: float = Field(description="Relevance score (0.0 to 1.0)")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Document metadata (sector, version, source, etc.)",
    )


class MethodologySearchResult(BaseModel):
    """Response model for methodology search operations."""

    query: str = Field(description="Original search query")
    results: list[SearchResult] = Field(description="Ranked search results")
    total_results: int = Field(description="Total number of results returned")
    search_time_ms: float = Field(description="Search execution time in milliseconds")


# -- Methodology Reference ----------------------------------------------------


class MethodologyReference(BaseModel):
    """A reference to a specific methodology section used as evidence."""

    source_document: str = Field(description="Source methodology document name")
    section: str = Field(default="", description="Relevant section heading")
    content_excerpt: str = Field(description="Relevant excerpt from the methodology")
    relevance_score: float = Field(
        default=0.0,
        description="Relevance score for this reference",
    )


# -- Credit Assessment Models --------------------------------------------------


class RatingRequest(BaseModel):
    """Request model for generating a draft credit assessment."""

    company_profile: CompanyProfile = Field(description="Complete company profile with financials")
    assessment_type: str = Field(
        default="comprehensive",
        description="Type of assessment: comprehensive, surveillance, initial",
    )
    additional_context: str = Field(
        default="",
        description="Additional context or analyst notes for the assessment",
    )


class CreditAssessment(BaseModel):
    """Generated draft credit assessment with evidence grounding."""

    entity_name: str = Field(description="Assessed entity name")
    sector: str = Field(description="Entity sector")
    assessment_date: str = Field(description="Date the assessment was generated")
    business_risk_assessment: str = Field(
        description="Analysis of business risk factors",
    )
    financial_risk_assessment: str = Field(
        description="Analysis of financial risk metrics against methodology criteria",
    )
    key_strengths: list[str] = Field(description="Key rating strengths with evidence")
    key_weaknesses: list[str] = Field(description="Key rating weaknesses with evidence")
    outlook_considerations: str = Field(
        description="Factors that could affect future trajectory",
    )
    methodology_references: list[MethodologyReference] = Field(
        description="Methodology sections cited in the assessment",
    )
    disclaimer: str = Field(
        default=(
            "DRAFT -- AI-GENERATED CONTENT FOR ANALYST REVIEW ONLY. "
            "This assessment does not represent a rating opinion or recommendation. "
            "All content requires analyst verification and Rating Committee adjudication."
        ),
        description="Mandatory disclaimer on AI-generated content",
    )
    correlation_id: str = Field(default="", description="Request correlation ID for traceability")


# -- Peer Comparison Models ----------------------------------------------------


class PeerComparisonRequest(BaseModel):
    """Request model for peer comparison analysis."""

    company_profile: CompanyProfile = Field(description="Subject company profile")
    peer_sector: Sector | None = Field(
        default=None,
        description="Override sector for peer identification (defaults to company sector)",
    )
    max_peers: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of peers to include in comparison",
    )


class PeerComparisonResult(BaseModel):
    """Generated peer comparison analysis."""

    entity_name: str = Field(description="Subject entity name")
    sector: str = Field(description="Comparison sector")
    comparison_date: str = Field(description="Date the comparison was generated")
    analysis: str = Field(description="Structured peer comparison analysis")
    peer_references: list[SearchResult] = Field(
        description="Precedent ratings used as peer references",
    )
    methodology_references: list[MethodologyReference] = Field(
        description="Methodology sections cited in the comparison",
    )
    disclaimer: str = Field(
        default=(
            "DRAFT -- AI-GENERATED CONTENT FOR ANALYST REVIEW ONLY. "
            "Peer comparison is indicative and does not constitute a rating benchmark."
        ),
        description="Mandatory disclaimer on AI-generated content",
    )
    correlation_id: str = Field(default="", description="Request correlation ID for traceability")


# -- Surveillance Models -------------------------------------------------------


class SurveillanceAlertRequest(BaseModel):
    """Request model for surveillance alert generation."""

    entity_name: str = Field(description="Entity under surveillance")
    sector: Sector = Field(description="Entity sector classification")
    current_rating: str = Field(description="Current assigned rating (e.g., CRISIL AA)")
    financial_triggers: list[str] = Field(
        description="List of financial trigger descriptions",
        min_length=1,
    )
    latest_financials: FinancialMetrics = Field(
        description="Most recent financial data for the entity",
    )
    additional_context: str = Field(
        default="",
        description="Additional surveillance context or analyst notes",
    )


class SurveillanceAlertResult(BaseModel):
    """Generated surveillance alert memorandum."""

    entity_name: str = Field(description="Entity under surveillance")
    current_rating: str = Field(description="Current assigned rating")
    alert_date: str = Field(description="Date the alert was generated")
    alert_summary: str = Field(description="Structured surveillance alert memorandum")
    triggers_identified: list[str] = Field(
        description="Specific triggers identified from financial data",
    )
    methodology_references: list[MethodologyReference] = Field(
        description="Methodology thresholds referenced in the alert",
    )
    precedent_actions: list[SearchResult] = Field(
        description="Precedent rating actions under similar circumstances",
    )
    disclaimer: str = Field(
        default=(
            "DRAFT -- AI-GENERATED CONTENT FOR ANALYST REVIEW ONLY. "
            "Surveillance recommendations require analyst assessment and committee review."
        ),
        description="Mandatory disclaimer on AI-generated content",
    )
    correlation_id: str = Field(default="", description="Request correlation ID for traceability")


# -- Document Ingestion Models -------------------------------------------------


class DocumentMetadata(BaseModel):
    """Metadata for a document being ingested."""

    document_type: DocumentType = Field(description="Classification of the document")
    sector: Sector = Field(default=Sector.OTHER, description="Sector classification")
    sub_sector: str = Field(default="", description="Sub-sector classification")
    version: str = Field(default="1.0", description="Document version")
    effective_date: str = Field(default="", description="Effective date of the document")
    rating_scale_type: str = Field(default="", description="Applicable rating scale type")
    source_document: str = Field(default="", description="Original source filename")
    # Precedent rating specific fields
    entity_name: str = Field(default="", description="Rated entity name")
    rating_assigned: str = Field(default="", description="Rating assigned")
    rating_date: str = Field(default="", description="Date of rating action")
    rating_action: str = Field(default="", description="Type of rating action")
    key_drivers: str = Field(default="", description="Comma-separated key rating drivers")
    financial_summary: str = Field(default="", description="Financial summary at time of rating")
    # Industry report specific fields
    report_date: str = Field(default="", description="Publication date")
    report_type: str = Field(default="", description="Report type classification")
    key_themes: str = Field(default="", description="Comma-separated key themes")


class DocumentChunk(BaseModel):
    """A processed document chunk ready for vector store ingestion."""

    content: str = Field(description="Chunk text content")
    chunk_index: int = Field(description="Position within the source document")
    metadata: DocumentMetadata = Field(description="Associated metadata")


class IngestionRequest(BaseModel):
    """Request model for document ingestion."""

    file_path: str = Field(
        default="",
        description="Path to a single file to ingest",
    )
    directory_path: str = Field(
        default="",
        description="Path to a directory of files to ingest",
    )
    document_type: DocumentType = Field(description="Classification for the documents")
    metadata_overrides: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata fields to override for all ingested documents",
    )


class IngestionResult(BaseModel):
    """Response model for document ingestion operations."""

    documents_processed: int = Field(description="Number of documents processed")
    chunks_created: int = Field(description="Total number of chunks created")
    chunks_ingested: int = Field(description="Number of chunks successfully ingested")
    errors: list[str] = Field(
        default_factory=list,
        description="Error messages for any failed documents",
    )
    processing_time_ms: float = Field(description="Total processing time in milliseconds")
    correlation_id: str = Field(default="", description="Request correlation ID for traceability")
