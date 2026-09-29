from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.models.domain import (
    FinancialMetrics,
    MethodologySearchRequest,
    Sector,
    SurveillanceAlertRequest,
)


def _financial_metrics() -> FinancialMetrics:
    return FinancialMetrics(
        revenue=1000,
        ebitda=150,
        ebitda_margin=15,
        pat=50,
        total_debt=400,
        tangible_net_worth=500,
        debt_to_equity=0.8,
        interest_coverage=3.5,
        current_ratio=1.4,
        roce=12,
        debt_to_ebitda=2.7,
        fiscal_year="FY2025",
    )


def test_methodology_search_enforces_query_and_limit_bounds() -> None:
    with pytest.raises(ValidationError):
        MethodologySearchRequest(query="ab")

    with pytest.raises(ValidationError):
        MethodologySearchRequest(query="methodology", limit=51)


def test_financial_metrics_apply_optional_defaults() -> None:
    metrics = _financial_metrics()

    assert metrics.dscr == 0.0
    assert metrics.cash_and_equivalents == 0.0


def test_surveillance_request_requires_a_trigger() -> None:
    with pytest.raises(ValidationError):
        SurveillanceAlertRequest(
            entity_name="Acme Limited",
            sector=Sector.MANUFACTURING,
            current_rating="CRISIL A",
            financial_triggers=[],
            latest_financials=_financial_metrics(),
        )
