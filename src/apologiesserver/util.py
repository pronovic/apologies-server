# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=unsubscriptable-object

"""
Shared utilities.
"""

import logging
import sys
import time
from pathlib import Path
from typing import Optional


# TODO: unit test needed
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
