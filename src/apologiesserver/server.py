# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import,unused-variable,unused-argument

# TODO: remove unused-variable and unused-argument once code is done

import asyncio
import re
import signal
from asyncio import Future  # pylint: disable=unused-import
from typing import Any, Callable, Coroutine, Dict, Optional, cast

import attr
import websockets
from periodic import Periodic
from websockets import WebSocketServerProtocol

from .interface import *
from .state import mark_player_active


@attr.s
class ProcessingError(RuntimeError):
    """Exception thrown when authorization is required and is missing."""

    reason = attr.ib(type=FailureReason)
    comment = attr.ib(type=Optional[str], default=None)


async def _idle_game_check() -> None:
    """Execute the Idle Game Check task."""


async def _idle_player_check() -> None:
    """Execute the Idle Player Check task."""


async def _obsolete_game_check() -> None:
    """Execute the Obsolete Game Check task."""


async def _handle_register_player(websocket: WebSocketServerProtocol, message: Message) -> None:
    """Handle the Register Player request."""
    context = cast(RegisterPlayerContext, message.context)


async def _handle_reregister_player(player_id: str, message: Message) -> None:
    """Handle the Reregister Player request."""
    mark_player_active(player_id)


async def _handle_unregister_player(player_id: str, message: Message) -> None:
    """Handle the Unregister Player request."""
    mark_player_active(player_id)


async def _handle_list_players(player_id: str, message: Message) -> None:
    """Handle the List Players request."""
    mark_player_active(player_id)


async def _handle_advertise_game(player_id: str, message: Message) -> None:
    """Handle the Advertise Game request."""
    mark_player_active(player_id)
    context = cast(AdvertiseGameContext, message.context)


async def _handle_list_available_games(player_id: str, message: Message) -> None:
    """Handle the List Available Games request."""
    mark_player_active(player_id)


async def _handle_join_game(player_id: str, message: Message) -> None:
    """Handle the Join Game request."""
    mark_player_active(player_id)
    context = cast(JoinGameContext, message.context)


async def _handle_quit_game(player_id: str, message: Message) -> None:
    """Handle the Quit Game request."""
    mark_player_active(player_id)


async def _handle_start_game(player_id: str, message: Message) -> None:
    """Handle the Start Game request."""
    mark_player_active(player_id)


async def _handle_cancel_game(player_id: str, message: Message) -> None:
    """Handle the Cancel Game request."""
    mark_player_active(player_id)


async def _handle_execute_move(player_id: str, message: Message) -> None:
    """Handle the Execute Move request."""
    mark_player_active(player_id)
    context = cast(ExecuteMoveContext, message.context)


async def _handle_retrieve_game_state(player_id: str, message: Message) -> None:
    """Handle the Retrieve Game State request."""
    mark_player_active(player_id)


async def _handle_send_message(player_id: str, message: Message) -> None:
    """Handle the Send Message request."""
    mark_player_active(player_id)
    context = cast(SendMessageContext, message.context)


async def _handle_server_shutdown() -> None:
    """Handle the Server Shutdown event."""


async def _handle_request_failed(websocket: WebSocketServerProtocol, exception: Exception) -> None:
    """Handle the Request Failed event."""


async def _handle_registered_players(player_id: str) -> None:
    """Handle the Registered Players event."""


async def _handle_available_games(player_id: str) -> None:
    """Handle the AvailableGames event."""


async def _handle_player_registered(player_id: str) -> None:
    """Handle the Player Registered event."""


async def _handle_player_disconnected(player_id: str) -> None:
    """Handle the Player Disconnected event."""


async def _handle_player_idle(player_id: str) -> None:
    """Handle the Player Idle event."""


async def _handle_player_inactive(player_id: str) -> None:
    """Handle the Player Inactive event."""


async def _handle_player_message_received(player_id: str) -> None:
    """Handle the Player Message Received event."""


async def _handle_game_advertised(player_id: str) -> None:
    """Handle the GameAdvertised event."""


async def _handle_game_invitation(player_id: str) -> None:
    """Handle the Game Invitation event."""


async def _handle_game_joined(player_id: str) -> None:
    """Handle the Game Joined event."""


async def _handle_game_started(player_id: str) -> None:
    """Handle the Game Started event."""


async def _handle_game_cancelled(player_id: str) -> None:
    """Handle the Game Cancelled event."""


async def _handle_game_completed(player_id: str) -> None:
    """Handle the Game Completed event."""


async def _handle_game_idle(player_id: str) -> None:
    """Handle the Game Idle event."""


async def _handle_game_inactive(player_id: str) -> None:
    """Handle the Game Inactive event."""


async def _handle_game_obsolete(player_id: str) -> None:
    """Handle the Game Obsolete event."""


async def _handle_game_player_change(player_id: str) -> None:
    """Handle the Game PlayerChange event."""


async def _handle_game_state_change(player_id: str) -> None:
    """Handle the Game State Change event."""


async def _handle_game_player_turn(player_id: str) -> None:
    """Handle the Game Player Turn event."""


async def _schedule_idle_game_check(period: int = 60, delay: int = 15) -> None:
    """Schedule the Idle Game Check task to run periodically, with a delay before starting."""
    p = Periodic(period, _idle_game_check)
    await p.start(delay=delay)


async def _schedule_idle_player_check(period: int = 60, delay: int = 30) -> None:
    """Schedule the Idle Player Check task to run periodically, with a delay before starting."""
    p = Periodic(period, _idle_player_check)
    await p.start(delay=delay)


async def _schedule_obsolete_game_check(period: int = 60, delay: int = 45) -> None:
    """Schedule the Obsolete Check task to run periodically, with a delay before starting."""
    p = Periodic(period, _obsolete_game_check)
    await p.start(delay=delay)


# Map from MessageType to request handler couroutine and whether the message requires authorization
_HANDLERS: Dict[MessageType, Callable[[str, Message], Coroutine[Any, Any, None]]] = {
    MessageType.REREGISTER_PLAYER: _handle_reregister_player,
    MessageType.UNREGISTER_PLAYER: _handle_unregister_player,
    MessageType.LIST_PLAYERS: _handle_list_players,
    MessageType.ADVERTISE_GAME: _handle_advertise_game,
    MessageType.LIST_AVAILABLE_GAMES: _handle_list_available_games,
    MessageType.JOIN_GAME: _handle_join_game,
    MessageType.QUIT_GAME: _handle_quit_game,
    MessageType.START_GAME: _handle_start_game,
    MessageType.CANCEL_GAME: _handle_cancel_game,
    MessageType.EXECUTE_MOVE: _handle_execute_move,
    MessageType.RETRIEVE_GAME_STATE: _handle_retrieve_game_state,
    MessageType.SEND_MESSAGE: _handle_send_message,
}


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
                await _handle_register_player(websocket, message)
            else:
                player_id = _parse_authorization(websocket)
                await _HANDLERS[message.message](player_id, message)  # type: ignore
        except Exception as e:  # pylint: disable=broad-except
            await _handle_request_failed(websocket, e)


async def _websocket_server(stop: "Future[Any]", host: str = "localhost", port: int = 8765) -> None:
    """A coroutine to run the websocket server."""
    async with websockets.serve(_handle_connection, host, port):
        await stop
        await _handle_server_shutdown()


# Signals that are handled to cause shutdown
_SHUTDOWN_SIGNALS = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)

# Scheduled tasks
_SCHEDULED_TASKS = [_schedule_idle_game_check, _schedule_idle_player_check, _schedule_obsolete_game_check]


def main() -> None:
    """The server main routine."""
    loop = asyncio.get_event_loop()

    stop = loop.create_future()
    for sig in _SHUTDOWN_SIGNALS:
        loop.add_signal_handler(sig, stop.set_result, None)

    for task in _SCHEDULED_TASKS:
        loop.create_task(task())

    loop.run_until_complete(_websocket_server(stop))
    loop.stop()
    loop.close()


if __name__ == "__main__":
    main()
