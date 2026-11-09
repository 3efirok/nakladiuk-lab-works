"""Production logging: one format for the application and uvicorn, level from LOG_LEVEL."""

import logging
import logging.config

FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


def configure_logging(level: str = "INFO") -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"default": {"format": FORMAT}},
            "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "default"}},
            "root": {"handlers": ["console"], "level": level},
        }
    )
