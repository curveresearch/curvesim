""" Custom logging config and useful aliases for logging """

__all__ = ["get_logger", "multiprocessing_logging_queue"]

import datetime
import logging
import logging.config
import multiprocessing as mp
import os
from contextlib import contextmanager
from logging.handlers import QueueHandler, QueueListener

# -- convenient parameters to adjust for debugging -- #
DEFAULT_LEVEL = "info"
USE_LOG_FILE = False
# --------------------------------------------------- #

LEVELS = {
    "critical": logging.CRITICAL,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "info": logging.INFO,
    "debug": logging.DEBUG,
}


BASE_DIR = os.getcwd()
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

__dt_string = datetime.datetime.now().strftime("%Y%m%d")
LOG_FILEPATH = os.path.join(LOG_DIR, __dt_string + ".log")

LOGGING_FORMAT = "[%(levelname)s][%(asctime)s][%(name)s]: %(message)s"
MULTIPROCESS_LOGGING_FORMAT = (
    "[%(levelname)s][%(asctime)s][%(name)s]-%(process)d: %(message)s"
)


# FIXME: need a function to update the config after module initialization
HANDLERS = ["console", "file"] if USE_LOG_FILE else ["console"]

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
            "delay": True,
        },
    },
    "loggers": {
        "": {
            "handlers": HANDLERS,
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# 3rd party loggers that we want to largely ignore
silenced_loggers = ["matplotlib", "asyncio", "rlp", "parso"]
configured_loggers = CUSTOM_LOGGING_CONFIG["loggers"]
for name in silenced_loggers:
    configured_loggers[name] = {
        "handlers": HANDLERS,
        "level": "INFO",
        "propagate": False,
    }

logging.config.dictConfig(CUSTOM_LOGGING_CONFIG)


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


@contextmanager
def multiprocessing_logging_queue():
    """
    Context manager for a logging queue that can be shared
    across multiple processes.
    """
    with mp.Manager() as manager:
        try:
            logging_queue = manager.Queue()
            root_logger = get_logger("")
            listener = QueueListener(logging_queue, *root_logger.handlers)
            listener.start()
            yield logging_queue
        finally:
            listener.stop()


def configure_multiprocess_logging(logging_queue):
    """Configure root logger in process to enqueue logs."""
    root_logger = get_logger("")
    root_logger.handlers.clear()
    root_logger.addHandler(QueueHandler(logging_queue))
