# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:

# TODO: unit tests are broken and need to be fixed

import asyncio
import logging
import re
import signal
from asyncio import AbstractEventLoop, Future  # pylint: disable=unused-import
from typing import Any, Coroutine, Union  # pylint: disable=unused-import

import websockets
from websockets import WebSocketServerProtocol

from .config import config
from .event import EventHandler, RequestContext
from .interface import FailureReason, Message, MessageType, ProcessingError, RequestFailedContext
from .manager import manager
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


# pylint: disable=too-many-branches
def _dispatch_request(handler: EventHandler, request: RequestContext) -> None:
    """Dispatch a request to the proper handler method based on message type."""
    if request.message.message == MessageType.REREGISTER_PLAYER:
        handler.handle_reregister_player_request(request)
    elif request.message.message == MessageType.UNREGISTER_PLAYER:
        handler.handle_unregister_player_request(request)
    elif request.message.message == MessageType.LIST_PLAYERS:
        handler.handle_list_players_request(request)
    elif request.message.message == MessageType.ADVERTISE_GAME:
        handler.handle_advertise_game_request(request)
    elif request.message.message == MessageType.LIST_AVAILABLE_GAMES:
        handler.handle_list_available_games_request(request)
    elif request.message.message == MessageType.JOIN_GAME:
        handler.handle_join_game_request(request)
    elif request.message.message == MessageType.QUIT_GAME:
        handler.handle_quit_game_request(request)
    elif request.message.message == MessageType.START_GAME:
        handler.handle_start_game_request(request)
    elif request.message.message == MessageType.CANCEL_GAME:
        handler.handle_cancel_game_request(request)
    elif request.message.message == MessageType.EXECUTE_MOVE:
        handler.handle_execute_move_request(request)
    elif request.message.message == MessageType.RETRIEVE_GAME_STATE:
        handler.handle_retrieve_game_state_request(request)
    elif request.message.message == MessageType.SEND_MESSAGE:
        handler.handle_send_message_request(request)
    else:
        raise ProcessingError(FailureReason.INTERNAL_ERROR, "Unable to dispatch request %s" % request.message.message)


def _handle_message(handler: EventHandler, message: Message, websocket: WebSocketServerProtocol) -> None:
    """Handle a valid message received from a websocket client."""
    if message.message == MessageType.REGISTER_PLAYER:
        handler.handle_register_player_request(message, websocket)
    else:
        player_id = _parse_authorization(websocket)
        player = handler.manager.lookup_player(player_id=player_id)
        if not player:
            raise ProcessingError(FailureReason.INVALID_PLAYER)
        log.debug("Request is for player: %s", player)
        player.mark_active()
        game = handler.manager.lookup_game(game_id=player.game_id)
        request = RequestContext(message, websocket, player, game)
        _dispatch_request(handler, request)


async def _handle_data(data: Union[str, bytes], websocket: WebSocketServerProtocol) -> None:
    """Handle data received from a websocket client."""
    log.debug("Received raw data for websocket %s: %s", websocket, data)
    message = Message.for_json(str(data))
    log.debug("Extracted message: %s", message)
    with EventHandler(manager()) as handler:
        with handler.manager.lock:
            _handle_message(handler, message, websocket)
        await handler.execute_tasks()


async def _handle_disconnect(websocket: WebSocketServerProtocol) -> None:
    """Handle a disconnected client."""
    log.debug("Websocket is disconnected: %s", websocket)
    with EventHandler(manager()) as handler:
        with handler.manager.lock:
            handler.handle_player_disconnected_event(websocket)
        await handler.execute_tasks()


# pylint: disable=broad-except
# noinspection PyBroadException
async def _handle_exception(exception: Exception, websocket: WebSocketServerProtocol) -> None:
    """Handle an exception by sending a request failed event."""
    try:
        log.error("Handling exception: %s", str(exception))
        raise exception
    except ProcessingError as e:
        context = RequestFailedContext(e.reason, e.comment if e.comment else e.reason.value)
    except ValueError as e:
        context = RequestFailedContext(FailureReason.INVALID_REQUEST, str(e))
    except Exception as e:
        context = RequestFailedContext(FailureReason.INTERNAL_ERROR, FailureReason.INTERNAL_ERROR.value)
    message = Message(MessageType.REQUEST_FAILED, context)
    try:
        await websocket.send(message.to_json())
    except Exception as e:
        log.error("Failed to handle exception: %s", str(e))


# pylint: disable=broad-except
# noinspection PyBroadException
async def _handle_connection(websocket: WebSocketServerProtocol, _path: str) -> None:
    """Handle a client connection, invoked once for each client that connects to the server."""
    log.debug("Got new websocket connection: %s", websocket)
    async for data in websocket:
        try:
            await _handle_data(data, websocket)
        except Exception as e:
            await _handle_exception(e, websocket)
    await _handle_disconnect(websocket)


async def _handle_shutdown() -> None:
    """Handle server shutdown."""
    with EventHandler(manager()) as handler:
        with handler.manager.lock:
            handler.handle_server_shutdown_event()
        await handler.execute_tasks()


async def _websocket_server(stop: "Future[Any]", host: str = "localhost", port: int = 8765) -> None:
    """Websocket server."""
    async with websockets.serve(_handle_connection, host, port):
        await stop
        await _handle_shutdown()


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
