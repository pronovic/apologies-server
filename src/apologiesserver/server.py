# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:

import asyncio
import logging
import re
import signal
from asyncio import AbstractEventLoop, Future  # pylint: disable=unused-import
from typing import Any, Coroutine, Union  # pylint: disable=unused-import

import websockets
from websockets import WebSocketServerProtocol

from .config import config
from .interface import FailureReason, Message, MessageType, ProcessingError
from .manager import handle_disconnect, handle_exception, handle_message, handle_register, handle_shutdown
from .scheduled import scheduled_tasks

log = logging.getLogger("apologies.server")

SHUTDOWN_SIGNALS = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)


def _parse_authorization(websocket: WebSocketServerProtocol) -> str:
    """Return the player id from the authorization header, raising ProcessingError if missing or invalid."""
    try:
        # For most requests, we expect a header like "Authorization: Player d669c200-74aa-4deb-ad91-2f5c27e51d74"
        authorization = websocket.request_headers["Authorization"]
        return re.fullmatch(r"( *)(Player  *)([^ ]+)( *)", authorization, flags=re.IGNORECASE).group(3)  # type: ignore
    except:
        raise ProcessingError(FailureReason.INVALID_AUTH)


async def _handle_message(data: Union[str, bytes], websocket: WebSocketServerProtocol) -> None:
    """Handle a message received from a websocket."""
    try:
        log.debug("Received raw data for websocket %s: %s", websocket, data)
        message = Message.for_json(str(data))
        log.debug("Extracted message: %s", message)
        if message.message == MessageType.REGISTER_PLAYER:
            queue = await handle_register(message, websocket)
        else:
            player_id = _parse_authorization(websocket)
            queue = await handle_message(player_id, message, websocket)
        await queue.send()
    except Exception as e:  # pylint: disable=broad-except
        await handle_exception(e, websocket)


async def _handle_connection(websocket: WebSocketServerProtocol, _path: str) -> None:
    """Client connection handler, invoked once for each client that connects."""
    log.debug("Got new websocket connection: %s", websocket)
    async for data in websocket:
        await _handle_message(data, websocket)
    log.debug("Websocket is disconnected: %s", websocket)
    queue = await handle_disconnect(websocket)
    await queue.send()


async def _websocket_server(stop: "Future[Any]", host: str = "localhost", port: int = 8765) -> None:
    """Websocket server."""
    async with websockets.serve(_handle_connection, host, port):
        await stop
        queue = await handle_shutdown()
        await queue.send()


def _add_signal_handlers(loop: AbstractEventLoop) -> "Future[Any]":
    """Add signal handlers so shutdown can be handled normally, returning the stop future."""
    log.info("Adding signal handlers...")
    stop = loop.create_future()
    for sig in SHUTDOWN_SIGNALS:
        loop.add_signal_handler(sig, stop.set_result, None)
    return stop


def _schedule_tasks(loop: AbstractEventLoop) -> None:
    """Schedule all of the scheduled tasks."""
    log.info("Scheduling tasks...")
    for task in scheduled_tasks():
        loop.create_task(task())


def _run_server(loop: AbstractEventLoop, stop: "Future[Any]") -> None:
    """Run the websocket server, stopping and closing the event loop when the server completes."""
    log.info("Starting websocket server...")
    loop.run_until_complete(_websocket_server(stop))
    loop.stop()
    loop.close()


def server() -> None:
    """The main processing loop for the websockets server."""
    log.info("Apologies server started")
    log.info("Configuration: %s", config().to_json())
    loop = asyncio.get_event_loop()
    stop = _add_signal_handlers(loop)
    _schedule_tasks(loop)
    _run_server(loop, stop)
    log.info("Apologies server finished")
