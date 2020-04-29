# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import


import asyncio
import re
import signal
from asyncio import Future  # pylint: disable=unused-import
from typing import Any  # pylint: disable=unused-import
from typing import Optional

import websockets
from websockets import WebSocketServerProtocol

from .event import handle_request_failed_event, handle_server_shutdown_event
from .interface import FailureReason, Message, MessageType, ProcessingError
from .request import REQUEST_HANDLERS, handle_register_player_request
from .scheduled import SCHEDULED_TASKS
from .state import mark_player_active

SHUTDOWN_SIGNALS = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
"""Signals that are handled for graceful shutdown."""


def _parse_authorization(websocket: WebSocketServerProtocol) -> Optional[str]:
    """Return the player id from the authorization header, raising _MissingAuthError if missing or invalid."""
    try:
        # For most requests, we expect a header like "Authorization: Player d669c200-74aa-4deb-ad91-2f5c27e51d74"
        authorization = websocket.request_headers["Authorization"]
        return re.fullmatch(r"( *)(Player )([^ ]+)( *)", authorization, flags=re.IGNORECASE).group(3)  # type: ignore
    except:
        raise ProcessingError(FailureReason.MISSING_AUTH)


async def _handle_connection(websocket: WebSocketServerProtocol, _path: str) -> None:
    """Client connection handler coroutine, invoked once for each client that connects."""
    async for data in websocket:
        try:
            message = Message.for_json(str(data))
            if message.message == MessageType.REGISTER_PLAYER:
                await handle_register_player_request(websocket, message)
            else:
                player_id = _parse_authorization(websocket)
                player = await mark_player_active(player_id)  # type: ignore
                await REQUEST_HANDLERS[message.message](player, message)
        except Exception as e:  # pylint: disable=broad-except
            await handle_request_failed_event(websocket, e)


async def _websocket_server(stop: "Future[Any]", host: str = "localhost", port: int = 8765) -> None:
    """Websocket server coroutine."""
    async with websockets.serve(_handle_connection, host, port):
        await stop
        await handle_server_shutdown_event()


def server() -> None:
    """The main processing loop for the websockets server."""
    loop = asyncio.get_event_loop()

    stop = loop.create_future()
    for sig in SHUTDOWN_SIGNALS:
        loop.add_signal_handler(sig, stop.set_result, None)

    for task in SCHEDULED_TASKS:
        loop.create_task(task())

    loop.run_until_complete(_websocket_server(stop))
    loop.stop()
    loop.close()
