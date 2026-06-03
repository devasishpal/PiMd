"""Reusable logging utility for PiMD."""

import logging
import sys
from typing import TextIO


def get_logger(
    name: str,
    level: int = logging.INFO,
    stream: TextIO = sys.stderr,
) -> logging.Logger:
    """Return a configured logger instance.

    Args:
        name: Logger name (typically ``__name__``).
        level: Logging level, e.g. ``logging.DEBUG``.
        stream: Output stream (defaults to stderr).

    Returns:
        A ready-to-use :class:`logging.Logger` instance.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(stream)
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(level)
    return logger
