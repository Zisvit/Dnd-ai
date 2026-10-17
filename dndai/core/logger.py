#!/usr/bin/env python3
import logging
import os
import sys
import threading

LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING").upper()

LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

_init_lock = threading.Lock()


def get_logger(name="dnd_bot"):
    logger = logging.getLogger(name)
    if not logger.handlers:
        with _init_lock:
            # Двойная проверка под замком: первый лог мог прийти
            # одновременно из главного потока и фонового.
            if not logger.handlers:
                logger.setLevel(LEVEL_MAP.get(LOG_LEVEL, logging.WARNING))
                handler = logging.StreamHandler(sys.stdout)
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                handler.setFormatter(formatter)
                logger.addHandler(handler)
    return logger


logger = get_logger()


def info(msg, *args, **kwargs):
    logger.info(msg, *args, **kwargs)


def debug(msg, *args, **kwargs):
    logger.debug(msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    logger.warning(msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    logger.error(msg, *args, **kwargs)


def critical(msg, *args, **kwargs):
    logger.critical(msg, *args, **kwargs)
