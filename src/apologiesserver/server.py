# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:

import asyncio
import logging
import re
import signal
from asyncio import Future  # pylint: disable=unused-import
from typing import Any  # pylint: disable=unused-import

import websockets
from websockets import WebSocketServerProtocol

from .config import config
from .event import handle_player_disconnected_event, handle_request_failed_event, handle_server_shutdown_event
from .interface import FailureReason, Message, MessageType, ProcessingError
from .request import REQUEST_HANDLERS, RequestContext, handle_register_player_request
from .scheduled import SCHEDULED_TASKS
from .state import lookup_game, lookup_player

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


async def _dispatch_register_player(websocket: WebSocketServerProtocol, message: Message) -> None:
    # This request has a different interface than the others, since there is never a player or a game
    log.debug("Handling request REGISTER_PLAYER vi mapping to handle_register_player_request")
    await handle_register_player_request(websocket, message)


async def _dispatch_request(websocket: WebSocketServerProtocol, message: Message) -> None:
    """Dispatch a websocket request to the right handler function."""
    handler = REQUEST_HANDLERS[message.message]
    log.debug("Handling request %s via mapping to %s", message.message, handler)
    player_id = _parse_authorization(websocket)
    player = await lookup_player(player_id=player_id)
    if not player:
        raise ProcessingError(FailureReason.UNKNOWN_PLAYER)
    async with player.lock:
        log.debug("Request is for player: %s", player)
        game_id = player.game_id
    game = await lookup_game(game_id=game_id)
    request = RequestContext(websocket, message, player, game)
    await player.mark_active()
    await handler(request)


async def _handle_connection(websocket: WebSocketServerProtocol, _path: str) -> None:
    """Client connection handler, invoked once for each client that connects."""
    log.debug("Got new websocket connection: %s", websocket)
    async for data in websocket:
        log.debug("Received raw data for websocket %s: %s", websocket, data)
        try:
            message = Message.for_json(str(data))
            log.debug("Extracted message: %s", message)
            if message.message == MessageType.REGISTER_PLAYER:
                await _dispatch_register_player(websocket, message)
            else:
                await _dispatch_request(websocket, message)
        except Exception as e:  # pylint: disable=broad-except
            log.error("Error handling request: %s", str(e))
            await handle_request_failed_event(websocket, e)
    log.debug("Websocket is disconnected: %s", websocket)
    await handle_player_disconnected_event(websocket)


async def _websocket_server(stop: "Future[Any]", host: str = "localhost", port: int = 8765) -> None:
    """Websocket server."""
    async with websockets.serve(_handle_connection, host, port):
        await stop
        await handle_server_shutdown_event()


def server() -> None:
    """The main processing loop for the websockets server."""
    log.info("Apologies server started")
    log.info("Configuration: %s", config().to_json())

    loop = asyncio.get_event_loop()

    log.info("Adding signal handlers...")
    stop = loop.create_future()
    for sig in SHUTDOWN_SIGNALS:
        loop.add_signal_handler(sig, stop.set_result, None)

    log.info("Scheduling tasks...")
    for task in SCHEDULED_TASKS:
        loop.create_task(task())

    log.info("Starting websocket server...")
    loop.run_until_complete(_websocket_server(stop))
    loop.stop()
    loop.close()

    log.info("Apologies server finished")
