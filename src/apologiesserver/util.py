# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=unsubscriptable-object

"""
Shared utilities.
"""

import asyncio
import logging
import re
import sys
import time
from asyncio import TimeoutError  # pylint: disable=redefined-builtin
from pathlib import Path
from typing import Optional, Union, cast

from websockets import WebSocketCommonProtocol
from websockets.typing import Data

from .interface import Message, MessageType, ProcessingError, RequestFailedContext

log = logging.getLogger("apologies.util")


def homedir() -> str:
    """Get the current user's home directory."""
    return str(Path.home())


def mask(data: Optional[Union[str, bytes]]) -> str:
    """Mask the player id in JSON data, since it's a secret we don't want logged."""
    decoded = "" if not data else data.decode("utf-8") if isinstance(data, bytes) else data
    return re.sub(r'"player_id" *: *"[^"]+"', r'"player_id": "<masked>"', decoded)


def extract(data: Union[str, Message, Data]) -> Message:
    message = Message.for_json(str(data))
    if message.message == MessageType.REQUEST_FAILED:
        context = cast(RequestFailedContext, message.context)
        raise ProcessingError(reason=context.reason, comment=context.comment, handle=context.handle)
    return message


async def close(websocket: WebSocketCommonProtocol) -> None:
    """Close a websocket."""
    log.debug("Closing websocket: %s", id(websocket))
    await websocket.close()


async def send(websocket: WebSocketCommonProtocol, message: Union[str, Message]) -> None:
    """Send a response to a websocket."""
    if message:
        data = message.to_json() if isinstance(message, Message) else message
        log.debug("Sending message to websocket: %s\n%s", id(websocket), mask(data))
        await websocket.send(data)


async def receive(websocket: WebSocketCommonProtocol, timeout_sec: Optional[int] = None) -> Optional[Message]:
    try:
        data = await websocket.recv() if not timeout_sec else await asyncio.wait_for(websocket.recv(), timeout=timeout_sec)
        log.debug("Received raw data for websocket %s:\n%s", id(websocket), mask(data))
        return extract(data)
    except TimeoutError:
        log.debug("Timed out waiting for raw data for websocket %s", id(websocket))
        return None


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
