# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:

import asyncio
import logging
import signal
from asyncio import AbstractEventLoop, Future  # pylint: disable=unused-import
from typing import Any, Callable, Coroutine, Union  # pylint: disable=unused-import

import websockets
from websockets import WebSocketServerProtocol

from .config import config
from .event import EventHandler, RequestContext
from .interface import FailureReason, Message, MessageType, ProcessingError, RequestFailedContext
from .manager import manager
from .scheduled import scheduled_tasks
from .util import close, mask, send

log = logging.getLogger("apologies.server")

SHUTDOWN_SIGNALS = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)

# pylint: disable=too-many-return-statements,too-many-branches
def _lookup_method(handler: EventHandler, message: MessageType) -> Callable[[RequestContext], None]:
    """Lookup the handler method to invoke for a message type."""
    if message == MessageType.REREGISTER_PLAYER:
        return handler.handle_reregister_player_request
    elif message == MessageType.UNREGISTER_PLAYER:
        return handler.handle_unregister_player_request
    elif message == MessageType.LIST_PLAYERS:
        return handler.handle_list_players_request
    elif message == MessageType.ADVERTISE_GAME:
        return handler.handle_advertise_game_request
    elif message == MessageType.LIST_AVAILABLE_GAMES:
        return handler.handle_list_available_games_request
    elif message == MessageType.JOIN_GAME:
        return handler.handle_join_game_request
    elif message == MessageType.QUIT_GAME:
        return handler.handle_quit_game_request
    elif message == MessageType.START_GAME:
        return handler.handle_start_game_request
    elif message == MessageType.CANCEL_GAME:
        return handler.handle_cancel_game_request
    elif message == MessageType.EXECUTE_MOVE:
        return handler.handle_execute_move_request
    elif message == MessageType.OPTIMAL_MOVE:
        return handler.handle_optimal_move_request
    elif message == MessageType.RETRIEVE_GAME_STATE:
        return handler.handle_retrieve_game_state_request
    elif message == MessageType.SEND_MESSAGE:
        return handler.handle_send_message_request
    else:
        raise ProcessingError(FailureReason.INTERNAL_ERROR, comment="Invalid request %s" % message.name)


def _handle_message(handler: EventHandler, message: Message, websocket: WebSocketServerProtocol) -> None:
    """Handle a valid message received from a websocket client, assumed to be within the handler's lock."""
    if message.message == MessageType.REGISTER_PLAYER:
        handler.handle_register_player_request(message, websocket)
    else:
        player = handler.manager.lookup_player(player_id=message.player_id)
        if not player:
            if message.message != MessageType.REREGISTER_PLAYER:
                raise ProcessingError(FailureReason.INVALID_PLAYER)
            handler.handle_register_player_request(message, websocket)  # fall back and treat this as a register request
        else:
            handler.manager.mark_active(player)  # marks both the player and its websocket as active
            log.debug("Request is for player: %s", player)
            game = handler.manager.lookup_game(game_id=player.game_id)
            request = RequestContext(message, websocket, player, game)
            method = _lookup_method(handler, request.message.message)
            method(request)


async def _handle_data(data: Union[str, bytes], websocket: WebSocketServerProtocol) -> None:
    """Handle data received from a websocket client."""
    log.debug("Received raw data for websocket %s:\n%s", id(websocket), mask(data))
    message = Message.for_json(str(data))
    with EventHandler(manager()) as handler:
        async with handler.manager.lock:
            _handle_message(handler, message, websocket)
        await handler.execute_tasks()


async def _handle_connect(websocket: WebSocketServerProtocol) -> None:
    """Handle a newly-connected client."""
    with EventHandler(manager()) as handler:
        async with handler.manager.lock:
            handler.handle_websocket_connected_event(websocket)
        await handler.execute_tasks()


async def _handle_disconnect(websocket: WebSocketServerProtocol) -> None:
    """Handle a disconnected client."""
    with EventHandler(manager()) as handler:
        async with handler.manager.lock:
            handler.handle_websocket_disconnected_event(websocket)
        await handler.execute_tasks()


# pylint: disable=broad-except
# noinspection PyBroadException
async def _handle_exception(exception: Exception, websocket: WebSocketServerProtocol) -> None:
    """Handle an exception by sending a request failed event."""
    try:
        disconnect = False
        try:
            log.error("Handling exception: %s", str(exception), exc_info=True)
            raise exception
        except ProcessingError as e:
            disconnect = e.reason == FailureReason.WEBSOCKET_LIMIT  # this is a special case that can't easily be handled elsewhere
            reason = e.reason
            comment = e.comment if e.comment else e.reason.value
            handle = e.handle
            context = RequestFailedContext(reason=reason, comment=comment, handle=handle)
        except ValueError as e:
            context = RequestFailedContext(FailureReason.INVALID_REQUEST, str(e))
        except Exception as e:
            # Note: we don't want to expose internal implementation details in the case of an internal error
            context = RequestFailedContext(FailureReason.INTERNAL_ERROR, FailureReason.INTERNAL_ERROR.value)
        message = Message(MessageType.REQUEST_FAILED, context=context)
        await send(websocket, message.to_json())
        if disconnect:
            await close(websocket)
    except Exception as e:
        # We don't propogate errors like this to the caller.  We just ignore them and
        # hope that we can recover for future requests.  If the websocket is dead,
        # we presume (hope?) that it will eventually get disconnected by the library.
        # It's not entirely clear what would be a better approach.  The only other
        # obvious option is to drop the client because we failed to send them an error,
        # which doesn't seem quite right, either.
        log.error("Failed to handle exception: %s", str(e))


# pylint: disable=broad-except
# noinspection PyBroadException
async def _handle_connection(websocket: WebSocketServerProtocol, _path: str) -> None:
    """Handle a client connection, invoked once for each client that connects to the server."""
    await _handle_connect(websocket)
    try:
        async for data in websocket:
            try:
                await _handle_data(data, websocket)
            except Exception as e:
                await _handle_exception(e, websocket)
    except websockets.exceptions.ConnectionClosed:  # we get this if the connection closes for any reason
        pass
    await _handle_disconnect(websocket)


async def _handle_shutdown() -> None:
    """Handle server shutdown."""
    with EventHandler(manager()) as handler:
        async with handler.manager.lock:
            handler.handle_server_shutdown_event()
        await handler.execute_tasks()


async def _websocket_server(stop: "Future[Any]", host: str, port: int, close_timeout_sec: float) -> None:
    """Websocket server."""
    log.info("Completed starting websocket server")  # ok, it's a bit of a lie
    async with websockets.serve(_handle_connection, host=host, port=port, close_timeout=close_timeout_sec):
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

    # Websockets has this to say about closing connections:
    #
    #    The close_timeout parameter defines a maximum wait time in seconds for
    #    completing the closing handshake and terminating the TCP connection.
    #    close() completes in at most 4 * close_timeout on the server side and
    #    5 * close_timeout on the client side.
    #
    # Since our configuration specifies a maximum time to wait (in total), we
    # need to divide by 4 to make sure that time isn't exceeded.
    #
    # See also: https://websockets.readthedocs.io/en/stable/api.html#module-websockets.protocol
    #           https://websockets.readthedocs.io/en/stable/api.html#module-websockets.server

    host = config().server_host
    port = config().server_port
    close_timeout_sec = config().close_timeout_sec / 4
    loop.run_until_complete(_websocket_server(stop=stop, host=host, port=port, close_timeout_sec=close_timeout_sec))
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
