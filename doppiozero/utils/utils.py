"""
utils.py
Shared utility functions for agentic workflows.
"""

import os
import json
import logging

# **********************************
# Constants and parameters
# **********************************

FORMAT = "%(asctime)s - %(name)-10s - %(filename)-18s - %(funcName)-12s - %(levelname)-8s - %(message)s"  # noqa

logging.basicConfig(format=FORMAT, level=logging.INFO)


# **********************************
# Functions definition
# **********************************


def get_logger(name=None, level=logging.INFO, format=FORMAT):
    """Return a logger of the specified name and level.

    Args:
        name   : the name of the logger. If no name is specified, root logger is returned.
        level  : logging levels (e.g. logging.INFO, logging.WARNING, etc.)
        format : format for the logger.

    Multiple calls to getLogger() with the same name return a reference to the same logger object.

    """

    # If no name is specified, return the root logger
    if not name:
        return logging.getLogger()

    # If a logger with the specified name already exists, return it
    logger = logging.getLogger(name)
    if len(logger.handlers) != 0:
        return logger

    # If a logger with the specified name does not exist, create it
    logger.setLevel(level)
    formatter = logging.Formatter(format)

    # Add a StreamHandler to the logger to enable logging to stdout
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # set propagate to False to prevent the logger from propagating to the root logger
    logger.propagate = False
    return logger


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
