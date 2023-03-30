""" Custom logging config and useful aliases for logging """

__all__ = ["get_logger"]

import datetime
import logging
import logging.config
import multiprocessing as mp
import os
from functools import partial
from logging.handlers import QueueHandler, QueueListener

LEVELS = {
    "critical": logging.CRITICAL,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "info": logging.INFO,
    "debug": logging.DEBUG,
}

DEFAULT_LEVEL = "info"


def get_logger(logger_name, level=DEFAULT_LEVEL):
    """
    Ensures logging config is loaded and allows us
    to make various customizations.
    """
    logger = logging.getLogger(logger_name)
    if isinstance(level, str):
        level = LEVELS[level.strip().lower()]
    logger.setLevel(level)

    return logger


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

__dt_string = datetime.datetime.now().strftime("%Y%m%d")
LOG_FILEPATH = os.path.join(LOG_DIR, __dt_string + ".log")

LOGGING_FORMAT = "[%(levelname)s][%(asctime)s][%(name)s]: %(message)s"
MULTIPROCESS_LOGGING_FORMAT = (
    "[%(levelname)s][%(asctime)s][%(name)s]-%(process)d: %(message)s"
)

CUSTOM_LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": MULTIPROCESS_LOGGING_FORMAT, "datefmt": "%H:%M:%S"},
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "maxBytes": 10 * 1024 * 1024,
            "mode": "a",
            "backupCount": 10,
            "filename": LOG_FILEPATH,
            "formatter": "standard",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# 3rd party loggers that we want to largely ignore
silenced_loggers = [
    "matplotlib",
    "asyncio",
    "rlp",
]
configured_loggers = CUSTOM_LOGGING_CONFIG["loggers"]
for name in silenced_loggers:
    configured_loggers[name] = {
        "handlers": ["console", "file"],
        "level": "INFO",
        "propagate": False,
    }

logging.config.dictConfig(CUSTOM_LOGGING_CONFIG)
