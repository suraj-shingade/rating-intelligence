"""Application configuration management.

Loads configuration from environment variables (.env) and YAML settings file,
providing a unified, validated configuration object via Pydantic Settings.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_DIR = _PROJECT_ROOT / "config"
_DEFAULT_SETTINGS_PATH = _CONFIG_DIR / "settings.yaml"


def _load_yaml_settings(path: Path | None = None) -> dict[str, Any]:
    """Load settings from the YAML configuration file.

    Args:
        path: Path to the YAML settings file. Defaults to config/settings.yaml.

    Returns:
        Dictionary of configuration values parsed from YAML.

    Raises:
        FileNotFoundError: If the settings file does not exist.
    """
    settings_path = path or _DEFAULT_SETTINGS_PATH
    if not settings_path.exists():
        raise FileNotFoundError(
            f"Settings file not found at {settings_path}. "
            f"Ensure config/settings.yaml exists in the project root."
        )
    with open(settings_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class WeaviateSettings(BaseSettings):
    """Weaviate vector database connection settings."""

    host: str = Field(default="localhost", description="Weaviate server hostname")
    http_port: int = Field(default=8080, description="Weaviate HTTP API port")
    grpc_port: int = Field(default=50051, description="Weaviate gRPC port")
    default_search_limit: int = Field(default=10, description="Default search result limit")
    max_search_limit: int = Field(default=50, description="Maximum search result limit")
    hybrid_alpha: float = Field(
        default=0.75,
        description="Hybrid search alpha (0=keyword, 1=vector)",
    )
    certainty_threshold: float = Field(
        default=0.7,
        description="Minimum certainty score for search results",
    )

    model_config = SettingsConfigDict(env_prefix="WEAVIATE_")


class AnthropicSettings(BaseSettings):
    """Anthropic Claude LLM configuration."""

    api_key: str = Field(default="", description="Anthropic API key for Claude")
    model: str = Field(
        default="claude-opus-4-6",
        description="Anthropic Claude model identifier",
    )
    temperature: float = Field(
        default=0.1,
        description="Generation temperature (lower = more deterministic)",
    )
    max_output_tokens: int = Field(
        default=4096,
        description="Maximum tokens in generated output",
    )

    model_config = SettingsConfigDict(env_prefix="ANTHROPIC_")

    @field_validator("api_key", mode="before")
    @classmethod
    def resolve_api_key(cls, v: str) -> str:
        """Resolve API key from ANTHROPIC_API_KEY environment variable."""
        if v:
            return v
        return os.getenv("ANTHROPIC_API_KEY", "")


class DocumentProcessingSettings(BaseSettings):
    """Document chunking and processing configuration."""

    chunk_size: int = Field(default=512, description="Token count per document chunk")
    chunk_overlap: int = Field(default=50, description="Token overlap between chunks")
    supported_extensions: list[str] = Field(
        default=[".md", ".txt", ".json"],
        description="File extensions supported for ingestion",
    )

    model_config = SettingsConfigDict(env_prefix="DOC_")


class AppSettings(BaseSettings):
    """Top-level application settings aggregating all subsystem configurations."""

    app_name: str = Field(
        default="Rating Methodology Intelligence System",
        description="Application display name",
    )
    app_version: str = Field(default="1.0.0", description="Application version")
    env: str = Field(default="development", description="Runtime environment")
    debug: bool = Field(default=False, description="Debug mode flag")
    log_level: str = Field(default="INFO", description="Logging level")

    weaviate: WeaviateSettings = Field(default_factory=WeaviateSettings)
    anthropic: AnthropicSettings = Field(default_factory=AnthropicSettings)
    document_processing: DocumentProcessingSettings = Field(
        default_factory=DocumentProcessingSettings,
    )

    yaml_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Raw YAML configuration for prompt templates and collection schemas",
    )

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, v: str) -> str:
        """Normalize log level to uppercase."""
        return v.upper() if isinstance(v, str) else v

    def get_prompt_template(self, template_name: str) -> str:
        """Retrieve a named prompt template from YAML configuration.

        Args:
            template_name: Key identifying the prompt template in settings.yaml.

        Returns:
            The prompt template string.

        Raises:
            KeyError: If the template name is not found in configuration.
        """
        templates = self.yaml_config.get("llm", {}).get("prompt_templates", {})
        if template_name not in templates:
            raise KeyError(
                f"Prompt template '{template_name}' not found in settings.yaml. "
                f"Available templates: {list(templates.keys())}"
            )
        return templates[template_name]

    def get_collection_config(self, collection_key: str) -> dict[str, Any]:
        """Retrieve Weaviate collection schema configuration from YAML.

        Args:
            collection_key: Key identifying the collection in settings.yaml
                            (e.g., 'rating_methodology').

        Returns:
            Dictionary containing collection schema configuration.

        Raises:
            KeyError: If the collection key is not found in configuration.
        """
        collections = self.yaml_config.get("weaviate", {}).get("collections", {})
        if collection_key not in collections:
            raise KeyError(
                f"Collection '{collection_key}' not found in settings.yaml. "
                f"Available collections: {list(collections.keys())}"
            )
        return collections[collection_key]


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Create and cache the application settings singleton.

    Loads .env file for environment variables and settings.yaml for structural
    configuration, merging them into a single validated settings object.

    Returns:
        Fully initialized AppSettings instance.
    """
    from dotenv import load_dotenv

    load_dotenv(_PROJECT_ROOT / ".env", override=True)

    yaml_config = _load_yaml_settings()

    weaviate_search = yaml_config.get("weaviate", {}).get("search", {})

    return AppSettings(
        yaml_config=yaml_config,
        weaviate=WeaviateSettings(
            default_search_limit=weaviate_search.get("default_limit", 10),
            max_search_limit=weaviate_search.get("max_limit", 50),
            hybrid_alpha=weaviate_search.get("hybrid_alpha", 0.75),
            certainty_threshold=weaviate_search.get("certainty_threshold", 0.7),
        ),
    )
