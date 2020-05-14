# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=unsubscriptable-object

"""
Shared utilities.
"""

import logging
import re
import sys
import time
from pathlib import Path
from typing import Optional, Union

from websockets import WebSocketCommonProtocol

log = logging.getLogger("apologies.util")


def homedir() -> str:
    """Get the current user's home directory."""
    return str(Path.home())


def mask(data: Optional[Union[str, bytes]]) -> str:
    """Mask the player id in JSON data, since it's a secret we don't want logged."""
    decoded = "" if not data else data.decode("utf-8") if isinstance(data, bytes) else data
    return re.sub(r'"player_id" *: *"[^"]+"', r'"player_id": "<masked>"', decoded)


async def close(websocket: WebSocketCommonProtocol) -> None:
    """Close a websocket."""
    log.debug("Closing websocket: %s", id(websocket))
    await websocket.close()


async def send(websocket: WebSocketCommonProtocol, message: str) -> None:
    """Send a response to a websocket."""
    log.debug("Sending message to websocket: %s\n%s", id(websocket), mask(message))
    await websocket.send(message)


def setup_logging(quiet: bool, verbose: bool, debug: bool, logfile_path: Optional[str] = None) -> None:
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
