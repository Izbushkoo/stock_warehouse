"""Logging configuration helpers."""

from __future__ import annotations

import logging
import sys

from loguru import logger

_LOGGING_CONFIGURED = False


def configure_logging(level: str = "INFO") -> None:
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    class InterceptHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            frame, depth = logging.currentframe(), 2
            while frame and frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1
            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

    logging.basicConfig(handlers=[InterceptHandler()], level=logging.getLevelName(level))
    logger.remove()
    logger.add(sys.stderr, level=level, enqueue=True, backtrace=True, diagnose=False)

    _LOGGING_CONFIGURED = True


__all__ = ["configure_logging", "logger"]
