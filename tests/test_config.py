from __future__ import annotations

from src.config import get_settings


def test_settings_loads_configured_search_defaults() -> None:
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.weaviate.default_search_limit == 10
    assert settings.weaviate.max_search_limit == 50
    assert settings.weaviate.hybrid_alpha == 0.75


def test_settings_exposes_credit_assessment_prompt() -> None:
    get_settings.cache_clear()

    prompt = get_settings().get_prompt_template("credit_assessment")

    assert "draft credit assessment" in prompt
    assert "Do NOT recommend a specific rating" in prompt
