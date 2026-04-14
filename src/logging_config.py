"""Structured logging configuration with correlation ID support.

Configures structlog for JSON-formatted structured logging with automatic
correlation ID propagation across request processing pipelines. Each
incoming API request receives a unique correlation ID that is bound to all
log entries produced during that request's lifecycle.
"""

from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

import structlog

_correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Retrieve the current correlation ID from context.

    Returns:
        The active correlation ID, or an empty string if none is set.
    """
    return _correlation_id_ctx.get()


def set_correlation_id(correlation_id: str | None = None) -> str:
    """Set a correlation ID in the current context.

    Args:
        correlation_id: Explicit correlation ID to use. If None, generates a
                        new UUID4-based identifier.

    Returns:
        The correlation ID that was set.
    """
    cid = correlation_id or uuid.uuid4().hex[:16]
    _correlation_id_ctx.set(cid)
    return cid


def clear_correlation_id() -> None:
    """Clear the correlation ID from the current context."""
    _correlation_id_ctx.set("")


def _add_correlation_id(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Structlog processor that injects the correlation ID into every log entry.

    Args:
        logger: The wrapped logger object (unused).
        method_name: The name of the log method called (unused).
        event_dict: The event dictionary being processed.

    Returns:
        The event dictionary with correlation_id added.
    """
    cid = get_correlation_id()
    if cid:
        event_dict["correlation_id"] = cid
    return event_dict


def _add_service_context(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Structlog processor that adds service-level context to log entries.

    Args:
        logger: The wrapped logger object (unused).
        method_name: The name of the log method called (unused).
        event_dict: The event dictionary being processed.

    Returns:
        The event dictionary with service context added.
    """
    event_dict.setdefault("service", "rating-intelligence")
    return event_dict


def configure_logging(log_level: str = "INFO", json_output: bool = True) -> None:
    """Configure structlog and standard library logging for the application.

    Sets up structured logging with correlation ID injection, timestamp
    formatting, and either JSON or console-friendly output rendering.

    Args:
        log_level: The minimum log level to capture (DEBUG, INFO, WARN, ERROR).
        json_output: If True, render logs as JSON. If False, use colored console output.
    """
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        _add_correlation_id,
        _add_service_context,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if json_output:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Suppress noisy third-party loggers
    for noisy_logger in ("httpx", "httpcore", "urllib3", "weaviate", "grpc"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name, typically the module's __name__.

    Returns:
        A bound structlog logger with the application's configured processors.
    """
    return structlog.get_logger(name)
