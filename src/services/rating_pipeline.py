"""LangChain-based analytical pipeline for credit rating intelligence.

Implements LCEL (LangChain Expression Language) chains for the four core
analytical operations: methodology retrieval, credit analysis, assessment
generation, and surveillance alerting. Chains are composed using
RunnableSequence and the pipe operator for clean, declarative data flow.
"""

from __future__ import annotations

import time
from datetime import date
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough, RunnableSequence

from src.config import AppSettings
from src.exceptions import InsufficientContextError, PipelineExecutionError
from src.logging_config import get_correlation_id, get_logger
from src.models.domain import (
    CompanyProfile,
    CreditAssessment,
    FinancialMetrics,
    MethodologyReference,
    PeerComparisonRequest,
    PeerComparisonResult,
    SearchResult,
    SurveillanceAlertRequest,
    SurveillanceAlertResult,
)
from src.services.llm_service import LLMService
from src.services.weaviate_service import WeaviateService

logger = get_logger(__name__)

_MINIMUM_CONTEXT_RESULTS = 1


class RatingPipeline:
    """Orchestrates LangChain LCEL chains for credit rating analytical tasks.

    Each analytical operation is implemented as a composable chain that:
    1. Retrieves relevant context from Weaviate
    2. Formats the context with the analytical query
    3. Invokes Anthropic Claude via LangChain for generation
    4. Parses and structures the output

    All chains produce draft outputs with explicit disclaimers and evidence
    citations. No chain produces rating recommendations or decisions.
    """

    def __init__(
        self,
        weaviate_service: WeaviateService,
        llm_service: LLMService,
        settings: AppSettings,
    ) -> None:
        """Initialize the rating pipeline with required services.

        Args:
            weaviate_service: Weaviate vector store service for retrieval.
            llm_service: LLM service for generation.
            settings: Application settings for prompt templates and configuration.
        """
        self._weaviate = weaviate_service
        self._llm = llm_service
        self._settings = settings
        self._output_parser = StrOutputParser()

    # -- Public Chain Entry Points -----------------------------------------------

    async def methodology_retrieval_chain(
        self,
        query: str,
        sector: str | None = None,
        rating_scale_type: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Execute the Methodology Retrieval Chain.

        Retrieves relevant methodology sections from Weaviate and generates
        a synthesized answer grounded in the retrieved content.

        Args:
            query: Analyst's natural language query about rating methodology.
            sector: Optional sector filter for targeted retrieval.
            rating_scale_type: Optional rating scale type filter.
            limit: Maximum number of methodology sections to retrieve.

        Returns:
            Dictionary containing the synthesized answer, source references,
            and search metadata.

        Raises:
            InsufficientContextError: If no relevant methodology sections are found.
            PipelineExecutionError: If the chain execution fails.
        """
        try:
            start_time = time.monotonic()

            search_results = self._weaviate.search_methodologies(
                query=query,
                sector=sector,
                rating_scale_type=rating_scale_type,
                limit=limit,
            )

            if len(search_results) < _MINIMUM_CONTEXT_RESULTS:
                raise InsufficientContextError(
                    operation="methodology_retrieval",
                    retrieved_count=len(search_results),
                    minimum_required=_MINIMUM_CONTEXT_RESULTS,
                )

            context = self._format_search_context(search_results)

            answer = await self._llm.generate_with_context(
                template_name="methodology_search",
                context=context,
                query=query,
                operation_name="methodology_retrieval",
            )

            elapsed_ms = (time.monotonic() - start_time) * 1000

            references = [
                MethodologyReference(
                    source_document=r.metadata.get("source_document", "unknown"),
                    section=r.metadata.get("sector", ""),
                    content_excerpt=r.content[:300],
                    relevance_score=r.score,
                )
                for r in search_results
            ]

            logger.info(
                "methodology_retrieval_completed",
                query_length=len(query),
                results_count=len(search_results),
                elapsed_ms=round(elapsed_ms, 2),
            )

            return {
                "answer": answer,
                "references": [ref.model_dump() for ref in references],
                "results_count": len(search_results),
                "search_time_ms": round(elapsed_ms, 2),
            }

        except (InsufficientContextError, PipelineExecutionError):
            raise
        except Exception as exc:
            raise PipelineExecutionError(
                chain_name="methodology_retrieval",
                cause=exc,
            ) from exc

    async def credit_analysis_chain(
        self,
        company_profile: CompanyProfile,
        additional_context: str = "",
    ) -> CreditAssessment:
        """Execute the Credit Analysis Chain.

        Multi-step chain that:
        1. Retrieves relevant methodology criteria for the company's sector
        2. Retrieves precedent ratings for similar companies
        3. Analyzes financial metrics against methodology thresholds
        4. Generates a structured draft credit assessment

        Args:
            company_profile: Complete company profile with financial data.
            additional_context: Optional analyst notes to include in the analysis.

        Returns:
            Structured CreditAssessment with evidence grounding and citations.

        Raises:
            InsufficientContextError: If insufficient methodology context is retrieved.
            PipelineExecutionError: If any stage of the chain fails.
        """
        try:
            start_time = time.monotonic()
            correlation_id = get_correlation_id()

            # Step 1: Retrieve relevant methodology criteria
            methodology_query = (
                f"Rating criteria and financial thresholds for "
                f"{company_profile.sector.value} sector "
                f"{'in ' + company_profile.sub_sector + ' sub-sector' if company_profile.sub_sector else ''}"
            )
            methodology_results = self._weaviate.search_methodologies(
                query=methodology_query,
                sector=company_profile.sector.value,
                limit=8,
            )

            # Step 2: Retrieve precedent ratings for similar companies
            precedent_query = (
                f"Credit rating for {company_profile.sector.value} company "
                f"with revenue {company_profile.financials[0].revenue} crore "
                f"and debt-to-equity {company_profile.financials[0].debt_to_equity}"
            )
            precedent_results = self._weaviate.search_precedent_ratings(
                query=precedent_query,
                sector=company_profile.sector.value,
                limit=5,
            )

            # Step 3: Compose the analytical context
            methodology_context = self._format_search_context(methodology_results)
            precedent_context = self._format_precedent_context(precedent_results)
            financial_summary = self._format_financial_profile(company_profile)

            combined_query = (
                f"Company: {company_profile.entity_name}\n"
                f"Sector: {company_profile.sector.value}\n\n"
                f"--- FINANCIAL PROFILE ---\n{financial_summary}\n\n"
                f"--- PRECEDENT RATINGS ---\n{precedent_context}\n\n"
            )
            if additional_context:
                combined_query += f"--- ANALYST NOTES ---\n{additional_context}\n\n"

            # Step 4: Generate the structured assessment
            raw_assessment = await self._llm.generate_with_context(
                template_name="credit_assessment",
                context=methodology_context,
                query=combined_query,
                operation_name="credit_analysis",
            )

            # Step 5: Parse the generated assessment into structured format
            assessment = self._parse_credit_assessment(
                raw_text=raw_assessment,
                company_profile=company_profile,
                methodology_results=methodology_results,
                correlation_id=correlation_id,
            )

            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.info(
                "credit_analysis_completed",
                entity=company_profile.entity_name,
                sector=company_profile.sector.value,
                methodology_refs=len(methodology_results),
                precedent_refs=len(precedent_results),
                elapsed_ms=round(elapsed_ms, 2),
            )

            return assessment

        except (InsufficientContextError, PipelineExecutionError):
            raise
        except Exception as exc:
            raise PipelineExecutionError(
                chain_name="credit_analysis",
                cause=exc,
            ) from exc

    async def peer_comparison_chain(
        self,
        request: PeerComparisonRequest,
    ) -> PeerComparisonResult:
        """Execute the Peer Comparison Chain.

        Retrieves precedent ratings for comparable entities in the same sector
        and generates a structured comparison analysis.

        Args:
            request: Peer comparison request with company profile and parameters.

        Returns:
            Structured PeerComparisonResult with comparative analysis.

        Raises:
            InsufficientContextError: If insufficient peer data is found.
            PipelineExecutionError: If the chain execution fails.
        """
        try:
            start_time = time.monotonic()
            correlation_id = get_correlation_id()
            sector = request.peer_sector or request.company_profile.sector

            # Retrieve peer ratings
            peer_query = (
                f"Rated entities in {sector.value} sector with financial profile "
                f"comparison for credit assessment"
            )
            peer_results = self._weaviate.search_precedent_ratings(
                query=peer_query,
                sector=sector.value,
                limit=request.max_peers,
            )

            # Retrieve methodology criteria for comparison context
            methodology_results = self._weaviate.search_methodologies(
                query=f"Peer comparison criteria for {sector.value} sector",
                sector=sector.value,
                limit=5,
            )

            methodology_context = self._format_search_context(methodology_results)
            peer_context = self._format_precedent_context(peer_results)
            financial_summary = self._format_financial_profile(request.company_profile)

            query = (
                f"Subject Entity: {request.company_profile.entity_name}\n"
                f"Sector: {sector.value}\n\n"
                f"--- SUBJECT FINANCIAL PROFILE ---\n{financial_summary}\n\n"
                f"--- PEER GROUP ---\n{peer_context}\n\n"
                f"Generate a structured peer comparison analysis."
            )

            analysis = await self._llm.generate_with_context(
                template_name="peer_comparison",
                context=methodology_context,
                query=query,
                operation_name="peer_comparison",
            )

            methodology_refs = [
                MethodologyReference(
                    source_document=r.metadata.get("source_document", "unknown"),
                    section=r.metadata.get("sector", ""),
                    content_excerpt=r.content[:300],
                    relevance_score=r.score,
                )
                for r in methodology_results
            ]

            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.info(
                "peer_comparison_completed",
                entity=request.company_profile.entity_name,
                sector=sector.value,
                peers_found=len(peer_results),
                elapsed_ms=round(elapsed_ms, 2),
            )

            return PeerComparisonResult(
                entity_name=request.company_profile.entity_name,
                sector=sector.value,
                comparison_date=date.today().isoformat(),
                analysis=analysis,
                peer_references=peer_results,
                methodology_references=methodology_refs,
                correlation_id=correlation_id,
            )

        except (InsufficientContextError, PipelineExecutionError):
            raise
        except Exception as exc:
            raise PipelineExecutionError(
                chain_name="peer_comparison",
                cause=exc,
            ) from exc

    async def surveillance_alert_chain(
        self,
        request: SurveillanceAlertRequest,
    ) -> SurveillanceAlertResult:
        """Execute the Surveillance Alert Chain.

        Generates a structured surveillance alert memorandum based on financial
        triggers, applicable methodology thresholds, and precedent rating actions.

        Args:
            request: Surveillance alert request with entity data and triggers.

        Returns:
            Structured SurveillanceAlertResult with alert memorandum.

        Raises:
            PipelineExecutionError: If the chain execution fails.
        """
        try:
            start_time = time.monotonic()
            correlation_id = get_correlation_id()

            # Retrieve applicable methodology thresholds
            trigger_text = "; ".join(request.financial_triggers)
            methodology_query = (
                f"Financial thresholds and rating triggers for "
                f"{request.sector.value} sector: {trigger_text}"
            )
            methodology_results = self._weaviate.search_methodologies(
                query=methodology_query,
                sector=request.sector.value,
                limit=8,
            )

            # Retrieve precedent rating actions for similar triggers
            precedent_query = (
                f"Rating action for {request.sector.value} entity due to "
                f"{trigger_text}"
            )
            precedent_results = self._weaviate.search_precedent_ratings(
                query=precedent_query,
                sector=request.sector.value,
                limit=5,
            )

            methodology_context = self._format_search_context(methodology_results)
            precedent_context = self._format_precedent_context(precedent_results)
            financial_summary = self._format_single_financials(request.latest_financials)

            query = (
                f"Entity: {request.entity_name}\n"
                f"Current Rating: {request.current_rating}\n"
                f"Sector: {request.sector.value}\n\n"
                f"--- FINANCIAL TRIGGERS ---\n{trigger_text}\n\n"
                f"--- LATEST FINANCIALS ---\n{financial_summary}\n\n"
                f"--- PRECEDENT ACTIONS ---\n{precedent_context}\n\n"
            )
            if request.additional_context:
                query += f"--- ANALYST CONTEXT ---\n{request.additional_context}\n\n"

            alert_text = await self._llm.generate_with_context(
                template_name="surveillance_alert",
                context=methodology_context,
                query=query,
                operation_name="surveillance_alert",
            )

            methodology_refs = [
                MethodologyReference(
                    source_document=r.metadata.get("source_document", "unknown"),
                    section=r.metadata.get("sector", ""),
                    content_excerpt=r.content[:300],
                    relevance_score=r.score,
                )
                for r in methodology_results
            ]

            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.info(
                "surveillance_alert_completed",
                entity=request.entity_name,
                current_rating=request.current_rating,
                triggers_count=len(request.financial_triggers),
                elapsed_ms=round(elapsed_ms, 2),
            )

            return SurveillanceAlertResult(
                entity_name=request.entity_name,
                current_rating=request.current_rating,
                alert_date=date.today().isoformat(),
                alert_summary=alert_text,
                triggers_identified=request.financial_triggers,
                methodology_references=methodology_refs,
                precedent_actions=precedent_results,
                correlation_id=correlation_id,
            )

        except PipelineExecutionError:
            raise
        except Exception as exc:
            raise PipelineExecutionError(
                chain_name="surveillance_alert",
                cause=exc,
            ) from exc

    # -- Internal Formatting Methods ---------------------------------------------

    def _format_search_context(self, results: list[SearchResult]) -> str:
        """Format search results into a context string for LLM consumption.

        Args:
            results: List of search results to format.

        Returns:
            Formatted context string with source attribution.
        """
        if not results:
            return "No relevant context retrieved."

        sections: list[str] = []
        for i, result in enumerate(results, 1):
            source = result.metadata.get("source_document", "unknown")
            sector = result.metadata.get("sector", "")
            header = f"[Source {i}: {source}"
            if sector:
                header += f" | Sector: {sector}"
            header += f" | Relevance: {result.score:.3f}]"

            sections.append(f"{header}\n{result.content}")

        return "\n\n---\n\n".join(sections)

    def _format_precedent_context(self, results: list[SearchResult]) -> str:
        """Format precedent rating results into a context string.

        Args:
            results: List of precedent rating search results.

        Returns:
            Formatted precedent context string.
        """
        if not results:
            return "No precedent ratings found for the specified criteria."

        sections: list[str] = []
        for i, result in enumerate(results, 1):
            entity = result.metadata.get("entity_name", "unknown")
            rating = result.metadata.get("rating_assigned", "N/A")
            action = result.metadata.get("rating_action", "N/A")
            rating_date = result.metadata.get("rating_date", "N/A")
            drivers = result.metadata.get("key_drivers", "")

            header = (
                f"[Precedent {i}: {entity} | Rating: {rating} | "
                f"Action: {action} | Date: {rating_date}]"
            )
            body = result.content
            if drivers:
                body += f"\nKey Drivers: {drivers}"

            sections.append(f"{header}\n{body}")

        return "\n\n---\n\n".join(sections)

    def _format_financial_profile(self, profile: CompanyProfile) -> str:
        """Format a company's complete financial profile for LLM context.

        Args:
            profile: Company profile with financial data.

        Returns:
            Formatted financial profile string.
        """
        lines: list[str] = [
            f"Entity: {profile.entity_name}",
            f"Sector: {profile.sector.value}",
        ]
        if profile.sub_sector:
            lines.append(f"Sub-sector: {profile.sub_sector}")
        if profile.promoter_group:
            lines.append(f"Promoter Group: {profile.promoter_group}")
        if profile.market_position:
            lines.append(f"Market Position: {profile.market_position}")
        if profile.geographic_diversification:
            lines.append(f"Geographic Diversification: {profile.geographic_diversification}")
        if profile.product_diversification:
            lines.append(f"Product Diversification: {profile.product_diversification}")
        if profile.management_experience_years:
            lines.append(
                f"Management Experience: {profile.management_experience_years} years"
            )

        for fin in profile.financials:
            lines.append(f"\n--- {fin.fiscal_year} ---")
            lines.append(self._format_single_financials(fin))

        return "\n".join(lines)

    def _format_single_financials(self, metrics: FinancialMetrics) -> str:
        """Format a single fiscal year's financial metrics.

        Args:
            metrics: Financial metrics for one fiscal year.

        Returns:
            Formatted financial metrics string.
        """
        return (
            f"Revenue: INR {metrics.revenue:.1f} crore\n"
            f"EBITDA: INR {metrics.ebitda:.1f} crore (margin: {metrics.ebitda_margin:.1f}%)\n"
            f"PAT: INR {metrics.pat:.1f} crore\n"
            f"Total Debt: INR {metrics.total_debt:.1f} crore\n"
            f"Tangible Net Worth: INR {metrics.tangible_net_worth:.1f} crore\n"
            f"Debt/Equity: {metrics.debt_to_equity:.2f}x\n"
            f"Interest Coverage: {metrics.interest_coverage:.2f}x\n"
            f"Current Ratio: {metrics.current_ratio:.2f}x\n"
            f"ROCE: {metrics.roce:.1f}%\n"
            f"Debt/EBITDA: {metrics.debt_to_ebitda:.2f}x\n"
            f"DSCR: {metrics.dscr:.2f}x\n"
            f"Cash & Equivalents: INR {metrics.cash_and_equivalents:.1f} crore"
        )

    def _parse_credit_assessment(
        self,
        raw_text: str,
        company_profile: CompanyProfile,
        methodology_results: list[SearchResult],
        correlation_id: str,
    ) -> CreditAssessment:
        """Parse raw LLM output into a structured CreditAssessment.

        Extracts the standard assessment sections from the generated text.
        Falls back to the full text if section parsing fails, ensuring the
        analyst always receives the complete generated content.

        Args:
            raw_text: Raw text output from the LLM.
            company_profile: The company profile used for the assessment.
            methodology_results: Methodology search results used as evidence.
            correlation_id: Request correlation ID.

        Returns:
            Structured CreditAssessment instance.
        """
        sections = self._extract_sections(raw_text)

        references = [
            MethodologyReference(
                source_document=r.metadata.get("source_document", "unknown"),
                section=r.metadata.get("sector", ""),
                content_excerpt=r.content[:300],
                relevance_score=r.score,
            )
            for r in methodology_results
        ]

        strengths = self._extract_bullet_points(
            sections.get("key_strengths", sections.get("strengths", ""))
        )
        weaknesses = self._extract_bullet_points(
            sections.get("key_weaknesses", sections.get("weaknesses", ""))
        )

        return CreditAssessment(
            entity_name=company_profile.entity_name,
            sector=company_profile.sector.value,
            assessment_date=date.today().isoformat(),
            business_risk_assessment=sections.get(
                "business_risk_assessment",
                sections.get("business_risk", raw_text[:1000]),
            ),
            financial_risk_assessment=sections.get(
                "financial_risk_assessment",
                sections.get("financial_risk", ""),
            ),
            key_strengths=strengths if strengths else [raw_text[:500]],
            key_weaknesses=weaknesses if weaknesses else ["See full assessment text above."],
            outlook_considerations=sections.get(
                "outlook_considerations",
                sections.get("outlook", ""),
            ),
            methodology_references=references,
            correlation_id=correlation_id,
        )

    def _extract_sections(self, text: str) -> dict[str, str]:
        """Extract named sections from structured LLM output.

        Identifies sections by common heading patterns (numbered headers,
        markdown headers, bold labels) and maps them to normalized keys.

        Args:
            text: Raw LLM output text.

        Returns:
            Dictionary mapping normalized section names to their content.
        """
        import re

        sections: dict[str, str] = {}

        section_patterns = [
            (r"(?:^|\n)#+\s*\d*\.?\s*Business\s+Risk\s+Assessment\s*\n([\s\S]*?)(?=\n#+|\n\d+\.\s|\Z)",
             "business_risk_assessment"),
            (r"(?:^|\n)#+\s*\d*\.?\s*Financial\s+Risk\s+Assessment\s*\n([\s\S]*?)(?=\n#+|\n\d+\.\s|\Z)",
             "financial_risk_assessment"),
            (r"(?:^|\n)#+\s*\d*\.?\s*Key\s+(?:Rating\s+)?Strengths?\s*\n([\s\S]*?)(?=\n#+|\n\d+\.\s|\Z)",
             "key_strengths"),
            (r"(?:^|\n)#+\s*\d*\.?\s*Key\s+(?:Rating\s+)?Weaknesses?\s*\n([\s\S]*?)(?=\n#+|\n\d+\.\s|\Z)",
             "key_weaknesses"),
            (r"(?:^|\n)#+\s*\d*\.?\s*Outlook\s+Considerations?\s*\n([\s\S]*?)(?=\n#+|\n\d+\.\s|\Z)",
             "outlook_considerations"),
        ]

        for pattern, key in section_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                sections[key] = match.group(1).strip()

        return sections

    def _extract_bullet_points(self, text: str) -> list[str]:
        """Extract bullet points from a text section.

        Handles markdown-style bullets (-, *) and numbered lists.

        Args:
            text: Text potentially containing bullet points.

        Returns:
            List of extracted bullet point strings.
        """
        if not text:
            return []

        import re

        bullet_pattern = r"(?:^|\n)\s*(?:[-*]|\d+\.)\s+(.+)"
        matches = re.findall(bullet_pattern, text)

        if matches:
            return [m.strip() for m in matches if m.strip()]

        # Fall back to splitting on newlines for non-bullet-formatted text
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        return lines[:10]  # Cap at 10 points to avoid noise
