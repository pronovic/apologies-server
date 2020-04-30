# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=unsubscriptable-object

"""
Shared utilities.
"""

import logging
import sys
import time
from copy import deepcopy
from pathlib import Path
from typing import Optional

from pendulum.datetime import DateTime


def copydate(date: DateTime) -> DateTime:
    """Return a copy of a date."""
    # As of Apr 2020, Pendulum's docs say that there is a DateTime.copy() method, but it doesn't exist.
    # In looking through the code, they verify that deepcopy() works, so that's what we'll use.
    # See: https://github.com/sdispater/pendulum/blob/205a86a22cbebd1fb33c5332a05fa9c2da5a3763/tests/datetime/test_behavior.py#L151
    return deepcopy(date)


def homedir() -> str:
    """Get the current user's home directory."""
    return str(Path.home())


def setup_logging(quiet: bool, verbose: bool, debug: bool, logfile_path: Optional[str]) -> None:
    """Set up Python logging."""
    logger = logging.getLogger("apologies")
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(logfile_path) if logfile_path else logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(fmt="%(asctime)sZ --> [%(levelname)-7s] %(message)s")
    formatter.converter = time.gmtime  # type: ignore
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)
    if quiet:
        handler.setLevel(logging.ERROR)
    if verbose or debug:
        handler.setLevel(logging.DEBUG)
    if debug:
        wslogger = logging.getLogger("websockets")
        wslogger.setLevel(logging.INFO)
        wslogger.addHandler(handler)
    logger.addHandler(handler)
