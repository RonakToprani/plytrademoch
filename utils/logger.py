import logging
import sys
import structlog
from config.settings import settings


def _is_dev() -> bool:
    """Detect development mode: dry_run=True or not a TTY."""
    return settings.dry_run or sys.stdout.isatty()


def configure_logging() -> None:
    """Set up structlog with JSON output for prod, colored console for dev."""
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if _is_dev():
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger bound to the given name."""
    return structlog.get_logger(name)


def bind_trade_context(trade_id: str) -> None:
    """Bind a trade ID to the current async context for structured logging."""
    structlog.contextvars.bind_contextvars(trade_id=trade_id)


def bind_wallet_context(wallet_address: str) -> None:
    """Bind a wallet address to the current async context for structured logging."""
    structlog.contextvars.bind_contextvars(wallet=wallet_address[:10] + "…")


def clear_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()
