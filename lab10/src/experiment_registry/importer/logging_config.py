"""Logging setup: rotating log file + console."""

import logging
from logging.handlers import RotatingFileHandler

from experiment_registry.importer.config import LoggingConfig

LOGGER_NAME = "experiment_registry.importer"
FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


def setup_logging(config: LoggingConfig, console: bool = True) -> logging.Logger:
    """Configure the importer logger; calling it again replaces old handlers."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(config.level)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    config.file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        config.file, maxBytes=config.max_bytes, backupCount=config.backup_count, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(FORMAT))
    logger.addHandler(file_handler)
    if console:
        stream = logging.StreamHandler()
        stream.setLevel(logging.WARNING)
        stream.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(stream)
    logger.propagate = False
    return logger
