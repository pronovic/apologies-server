# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import


import asyncio
import re
import signal
from asyncio import Future  # pylint: disable=unused-import
from typing import Any, Callable, Coroutine, Dict, Optional

import websockets
from periodic import Periodic
from websockets import WebSocketServerProtocol

from .handler import *
from .interface import *

# Signals that are handled to cause shutdown
_SHUTDOWN_SIGNALS = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)


async def _schedule_idle_game_check(period: int = 60, delay: int = 120) -> None:
    """Schedule the Idle Game Check task to run periodically, with a delay before starting."""
    p = Periodic(period, handle_idle_game_check)
    await p.start(delay=delay)


async def _schedule_idle_player_check(period: int = 60, delay: int = 120) -> None:
    """Schedule the Idle Player Check task to run periodically, with a delay before starting."""
    p = Periodic(period, handle_idle_player_check)
    await p.start(delay=delay)


async def _schedule_obsolete_game_check(period: int = 60, delay: int = 120) -> None:
    """Schedule the Obsolete Check task to run periodically, with a delay before starting."""
    p = Periodic(period, handle_obsolete_game_check)
    await p.start(delay=delay)


# Scheduled tasks
_SCHEDULED_TASKS = [_schedule_idle_game_check, _schedule_idle_player_check, _schedule_obsolete_game_check]


# Map from MessageType to request handler couroutine and whether the message requires authorization
_HANDLERS: Dict[MessageType, Callable[[str, Message], Coroutine[Any, Any, None]]] = {
    MessageType.REREGISTER_PLAYER: handle_reregister_player,
    MessageType.UNREGISTER_PLAYER: handle_unregister_player,
    MessageType.LIST_PLAYERS: handle_list_players,
    MessageType.ADVERTISE_GAME: handle_advertise_game,
    MessageType.LIST_AVAILABLE_GAMES: handle_list_available_games,
    MessageType.JOIN_GAME: handle_join_game,
    MessageType.QUIT_GAME: handle_quit_game,
    MessageType.START_GAME: handle_start_game,
    MessageType.CANCEL_GAME: handle_cancel_game,
    MessageType.EXECUTE_MOVE: handle_execute_move,
    MessageType.RETRIEVE_GAME_STATE: handle_retrieve_game_state,
    MessageType.SEND_MESSAGE: handle_send_message,
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
                await handle_register_player(websocket, message)
            else:
                player_id = _parse_authorization(websocket)
                await _HANDLERS[message.message](player_id, message)  # type: ignore
        except Exception as e:  # pylint: disable=broad-except
            await handle_request_failed(websocket, e)


async def _websocket_server(stop: "Future[Any]", host: str = "localhost", port: int = 8765) -> None:
    """A coroutine to run the websocket server."""
    async with websockets.serve(_handle_connection, host, port):
        await stop
        await handle_server_shutdown()


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
