"""Anthropic Claude LLM integration via LangChain.

Provides a centralized service for all LLM interactions, including prompt
template management, structured generation, and token usage tracking.
Uses LangChain's ChatAnthropic for Claude API access.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from src.config import AppSettings
from src.exceptions import LLMConnectionError, LLMGenerationError
from src.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class TokenUsage:
    """Tracks cumulative token usage across LLM calls within a session."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    call_count: int = 0
    total_latency_ms: float = 0.0

    def record(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
    ) -> None:
        """Record token usage from a single LLM call.

        Args:
            prompt_tokens: Number of input tokens consumed.
            completion_tokens: Number of output tokens generated.
            latency_ms: Latency of the call in milliseconds.
        """
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.total_tokens += prompt_tokens + completion_tokens
        self.call_count += 1
        self.total_latency_ms += latency_ms

    def to_dict(self) -> dict[str, Any]:
        """Serialize usage statistics to a dictionary.

        Returns:
            Dictionary of usage metrics.
        """
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "call_count": self.call_count,
            "total_latency_ms": round(self.total_latency_ms, 2),
            "avg_latency_ms": round(
                self.total_latency_ms / self.call_count if self.call_count else 0, 2,
            ),
        }


class LLMService:
    """Service managing Anthropic Claude LLM interactions via LangChain.

    Centralizes model initialization, prompt template management, and
    generation with automatic token usage tracking and error handling.
    """

    def __init__(self, settings: AppSettings) -> None:
        """Initialize the LLM service.

        Args:
            settings: Application settings containing Anthropic configuration.

        Raises:
            LLMConnectionError: If the Claude model cannot be initialized.
        """
        self._settings = settings
        self._usage = TokenUsage()
        self._model = self._initialize_model()
        self._output_parser = StrOutputParser()

    def _initialize_model(self) -> ChatAnthropic:
        """Initialize the ChatAnthropic model instance.

        Returns:
            Configured ChatAnthropic instance.

        Raises:
            LLMConnectionError: If model initialization fails.
        """
        anthropic_config = self._settings.anthropic

        if not anthropic_config.api_key:
            raise LLMConnectionError(
                model=anthropic_config.model,
                cause=ValueError(
                    "Anthropic API key not configured. Set ANTHROPIC_API_KEY in .env file."
                ),
            )

        try:
            model = ChatAnthropic(
                model=anthropic_config.model,
                anthropic_api_key=anthropic_config.api_key,
                temperature=anthropic_config.temperature,
                max_tokens=anthropic_config.max_output_tokens,
            )
            logger.info(
                "llm_initialized",
                model=anthropic_config.model,
                temperature=anthropic_config.temperature,
                max_output_tokens=anthropic_config.max_output_tokens,
            )
            return model
        except Exception as exc:
            raise LLMConnectionError(
                model=anthropic_config.model,
                cause=exc,
            ) from exc

    @property
    def model(self) -> ChatAnthropic:
        """Access the underlying ChatAnthropic model.

        Returns:
            The initialized LLM model instance.
        """
        return self._model

    @property
    def usage(self) -> TokenUsage:
        """Access cumulative token usage statistics.

        Returns:
            Current TokenUsage tracking object.
        """
        return self._usage

    def get_system_prompt(self) -> str:
        """Retrieve the system context prompt from configuration.

        Returns:
            The system context prompt string.
        """
        return self._settings.get_prompt_template("system_context")

    def get_prompt_template(self, template_name: str) -> str:
        """Retrieve a named prompt template from configuration.

        Args:
            template_name: Key identifying the prompt template.

        Returns:
            The prompt template string.
        """
        return self._settings.get_prompt_template(template_name)

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        operation_name: str = "generic",
    ) -> str:
        """Generate text using the Claude model with system and user prompts.

        Args:
            system_prompt: System-level instructions for the model.
            user_prompt: The user's query or task description.
            operation_name: Label for logging and error context.

        Returns:
            Generated text content.

        Raises:
            LLMGenerationError: If the generation call fails.
        """
        try:
            start_time = time.monotonic()

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            response = await self._model.ainvoke(messages)
            elapsed_ms = (time.monotonic() - start_time) * 1000

            content = response.content if isinstance(response.content, str) else str(response.content)

            usage_meta = getattr(response, "usage_metadata", None)
            prompt_tokens = getattr(usage_meta, "input_tokens", 0) if usage_meta else 0
            completion_tokens = getattr(usage_meta, "output_tokens", 0) if usage_meta else 0

            self._usage.record(prompt_tokens, completion_tokens, elapsed_ms)

            logger.info(
                "llm_generation_completed",
                operation=operation_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                elapsed_ms=round(elapsed_ms, 2),
            )

            return content

        except Exception as exc:
            raise LLMGenerationError(
                operation=operation_name,
                cause=exc,
            ) from exc

    async def generate_with_context(
        self,
        template_name: str,
        context: str,
        query: str,
        operation_name: str = "contextual_generation",
    ) -> str:
        """Generate text using a named prompt template with retrieved context.

        This is the primary method for RAG-based generation, where retrieved
        documents provide the evidence context for the model's response.

        Args:
            template_name: Name of the prompt template from settings.yaml.
            context: Retrieved document content to ground the generation.
            query: The specific analytical query or task.
            operation_name: Label for logging and error context.

        Returns:
            Generated text content grounded in the provided context.

        Raises:
            LLMGenerationError: If the generation call fails.
        """
        system_prompt = self.get_system_prompt()
        task_prompt = self.get_prompt_template(template_name)

        user_prompt = (
            f"{task_prompt}\n\n"
            f"--- RETRIEVED CONTEXT ---\n{context}\n\n"
            f"--- ANALYST QUERY ---\n{query}"
        )

        return await self.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            operation_name=operation_name,
        )

    def build_chat_prompt(
        self,
        system_template: str,
        human_template: str,
    ) -> ChatPromptTemplate:
        """Build a LangChain ChatPromptTemplate for chain composition.

        Args:
            system_template: System message template with format placeholders.
            human_template: Human message template with format placeholders.

        Returns:
            Configured ChatPromptTemplate instance.
        """
        return ChatPromptTemplate.from_messages(
            [
                ("system", system_template),
                ("human", human_template),
            ]
        )

    def reset_usage(self) -> dict[str, Any]:
        """Reset token usage tracking and return the final statistics.

        Returns:
            Dictionary of usage metrics before reset.
        """
        final_stats = self._usage.to_dict()
        self._usage = TokenUsage()
        logger.info("token_usage_reset", final_stats=final_stats)
        return final_stats
