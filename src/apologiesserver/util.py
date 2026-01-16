# vim: set ft=python ts=4 sw=4 expandtab:

"""
Shared utilities.
"""

import asyncio
import logging
import re
import sys
import time
import typing
from logging import FileHandler, StreamHandler
from pathlib import Path
from typing import cast

from websockets.asyncio.connection import Connection
from websockets.typing import Data

from apologiesserver.interface import Message, MessageType, ProcessingError

if typing.TYPE_CHECKING:
    # noinspection PyUnresolvedReferences
    from apologiesserver.interface import RequestFailedContext

log = logging.getLogger("apologies.util")


def homedir() -> str:
    """Get the current user's home directory."""
    return str(Path.home())


def mask(data: str | bytes | None) -> str:
    """Mask the player id in JSON data, since it's a secret we don't want logged."""
    decoded = "" if not data else data.decode("utf-8") if isinstance(data, bytes) else data
    return re.sub(r'"player_id" *: *"[^"]+"', r'"player_id": "<masked>"', decoded)


def extract(data: str | Message | Data) -> Message:
    message = Message.for_json(str(data))
    if message.message == MessageType.REQUEST_FAILED:
        context = cast("RequestFailedContext", message.context)
        raise ProcessingError(reason=context.reason, comment=context.comment, handle=context.handle)
    return message


async def close(websocket: Connection) -> None:
    """Close a websocket."""
    log.debug("Closing websocket: %s", id(websocket))
    await websocket.close()


async def send(websocket: Connection, message: str | Message) -> None:
    """Send a response to a websocket."""
    if message:
        data = message.to_json() if isinstance(message, Message) else message
        log.debug("Sending message to websocket: %s\n%s", id(websocket), mask(data))
        await websocket.send(data)


async def receive(websocket: Connection, timeout_sec: int | None = None) -> Message | None:
    try:
        data = await websocket.recv() if not timeout_sec else await asyncio.wait_for(websocket.recv(), timeout=timeout_sec)
        log.debug("Received raw data for websocket %s:\n%s", id(websocket), mask(data))
        return extract(data)
    except TimeoutError:
        log.debug("Timed out waiting for raw data for websocket %s", id(websocket))
        return None


def setup_logging(*, quiet: bool, verbose: bool, debug: bool, logfile_path: str | None = None) -> None:
    """Set up Python logging."""
    logger = logging.getLogger("apologies")
    logger.setLevel(logging.DEBUG)
    handler: StreamHandler = FileHandler(logfile_path) if logfile_path else StreamHandler(sys.stdout)  # type: ignore
    formatter = logging.Formatter(fmt="%(asctime)sZ --> [%(levelname)-7s] %(message)s")
    formatter.converter = time.gmtime
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
