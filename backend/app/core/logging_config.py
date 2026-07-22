"""
Structured logging configuration.

Sentinel is a decision-support system for safety-critical environments, so
every agent decision must be traceable after the fact. We use loguru with a
consistent structured format so logs can later be shipped to any log
aggregator (ELK, CloudWatch, etc.) without code changes.
"""
import sys

from loguru import logger

from app.config import settings

_LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)


def configure_logging() -> None:
    """Configure the global loguru sink. Call once at application startup."""
    logger.remove()  # drop the default handler to avoid duplicate output
    logger.add(
        sys.stdout,
        format=_LOG_FORMAT,
        level=settings.log_level,
        colorize=True,
        backtrace=True,
        diagnose=settings.app_env == "development",
    )
    logger.info(f"Logging configured | env={settings.app_env} | level={settings.log_level}")


__all__ = ["logger", "configure_logging"]
