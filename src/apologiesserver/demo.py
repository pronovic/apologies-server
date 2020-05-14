# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import

"""
Implements a quick'n'dirty game-playing client as a demo.
"""

import asyncio
import logging
import signal
from asyncio import AbstractEventLoop, CancelledError
from typing import List, Optional, cast

import websockets
from apologies.game import GameMode
from websockets import WebSocketClientProtocol

from .interface import *
from .util import receive, send

SHUTDOWN_SIGNALS = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)

log = logging.getLogger("apologies.demo")


async def _register_player(websocket: WebSocketClientProtocol) -> str:
    """Register a player."""
    context = RegisterPlayerContext(handle="Demo")
    request = Message(MessageType.REGISTER_PLAYER, context=context)
    await send(websocket, request)
    response = await receive(websocket)
    log.info("Completed registering handle=leela, got player_id=%s", response.player_id)  # type: ignore
    return response.player_id  # type: ignore


async def _advertise_game(websocket: WebSocketClientProtocol, player_id: str) -> None:
    """Advertise a game."""
    name = "Demo Game"
    mode = GameMode.STANDARD
    players = 4
    visibility = Visibility.PUBLIC
    invited_handles: List[str] = []
    context = AdvertiseGameContext(name, mode, players, visibility, invited_handles)
    request = Message(MessageType.ADVERTISE_GAME, player_id=player_id, context=context)
    await send(websocket, request)


async def _start_game(websocket: WebSocketClientProtocol, player_id: str) -> None:
    """Start the player's advertised game."""
    request = Message(MessageType.START_GAME, player_id=player_id)
    await send(websocket, request)


def _handle_game_joined(_player_id: str, message: Message) -> None:
    """Handle the game joined event."""
    context = cast(GameJoinedContext, message.context)
    log.info("Joined game %s", context.game_id)


def _handle_game_advertised(_player_id: str, message: Message) -> None:
    """Handle the game advertised event."""
    context = cast(GameAdvertisedContext, message.context)
    log.info("Advertised game '%s': %s", context.game.name, context.game.game_id)


def _handle_game_started(_player_id: str, message: Message) -> None:
    """Handle the game started event."""
    context = cast(GameStartedContext, message.context)
    log.info("Started game: %s", context.game_id)


def _handle_game_completed(_player_id: str, message: Message) -> None:
    """Handle the game completed event."""
    context = cast(GameCompletedContext, message.context)
    log.info("Game completed: %s", context.comment if context.comment else "")


def _handle_game_state_change(_player_id: str, message: Message) -> None:
    "Handle the game state change event"
    context = cast(GameStateChangeContext, message.context)
    comment: Optional[str] = None
    if context.recent_history:
        history = context.recent_history[-1]
        color = "General" if not history.color else history.color.value
        action = history.action
        comment = "%s - %s" % (color, action)
    log.info("%s", comment if comment else "")


def _handle_game_player_change(_player_id: str, message: Message) -> None:
    """Handle the game player change event."""
    context = cast(GamePlayerChangeContext, message.context)
    players = [player.handle for player in context.players]
    log.info("Game players are: %s", players)


def _handle_game_player_turn(_player_id: str, message: Message) -> Optional[Message]:
    """Handle the game player turn event."""
    context = cast(GamePlayerTurnContext, message.context)
    log.info("Turn for %s, %d moves available", context.handle, len(context.moves))
    return None


def _handle_message(player_id: str, message: Message) -> Optional[Message]:
    """Handle any message received from the connection."""
    response = None
    if message.message == MessageType.GAME_JOINED:
        _handle_game_joined(player_id, message)
    elif message.message == MessageType.GAME_ADVERTISED:
        _handle_game_advertised(player_id, message)
    elif message.message == MessageType.GAME_STARTED:
        _handle_game_started(player_id, message)
    elif message.message == MessageType.GAME_COMPLETED:
        _handle_game_completed(player_id, message)
    elif message.message == MessageType.GAME_STATE_CHANGE:
        _handle_game_state_change(player_id, message)
    elif message.message == MessageType.GAME_PLAYER_CHANGE:
        _handle_game_player_change(player_id, message)
    elif message.message == MessageType.GAME_PLAYER_TURN:
        response = _handle_game_player_turn(player_id, message)
    else:
        log.info("Ignored message with type %s", message.message.name)
    return response


async def _handle_connection(websocket: WebSocketClientProtocol) -> None:
    """Handle a websocket connection, sending and receiving messages."""
    player_id = await _register_player(websocket)
    await _advertise_game(websocket, player_id)
    await _start_game(websocket, player_id)
    while True:
        message = await receive(websocket, timeout_sec=30)
        if message:
            response = _handle_message(player_id, message)
            if response:
                await send(websocket, response)


async def _websocket_client(uri: str) -> None:
    """The asynchronous websocket client."""
    log.info("Completed starting websocket client")  # ok, it's a bit of a lie
    try:
        async with websockets.connect(uri=uri) as websocket:
            await _handle_connection(websocket)
    except Exception as e:  # pylint: disable=broad-except
        log.error("Error with connection: %s", str(e), exc_info=True)


async def _terminate() -> None:
    """Terminate running tasks."""
    pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in pending:
        task.cancel()
    await asyncio.gather(*pending)


def _add_signal_handlers(loop: AbstractEventLoop) -> None:
    """Add signal handlers so shutdown can be handled normally, returning the stop future."""
    log.info("Adding signal handlers...")
    for sig in SHUTDOWN_SIGNALS:
        loop.add_signal_handler(sig, lambda: asyncio.create_task(_terminate()))


def demo(host: str, port: int) -> None:
    """Run the demo."""
    uri = "ws://%s:%d" % (host, port)
    log.info("Demo client started against %s", uri)
    loop = asyncio.get_event_loop()
    _add_signal_handlers(loop)
    try:
        loop.run_until_complete(_websocket_client(uri))
    except CancelledError:
        pass
    finally:
        loop.stop()
        loop.close()
        log.info("Demo client finished")
