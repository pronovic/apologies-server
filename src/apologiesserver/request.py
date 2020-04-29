# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=unused-argument,wildcard-import

"""Coroutines to requests received via Websocket connections."""

# TODO: remove disable=unused-argument once these coroutines are implemented

import logging
from typing import Any, Callable, Coroutine, Dict

from websockets import WebSocketServerProtocol

from .event import *
from .interface import Message, MessageType
from .state import TrackedPlayer

logger = logging.getLogger("apologies.request")


async def handle_register_player_request(websocket: WebSocketServerProtocol, message: Message) -> None:
    """Handle the Register Player request."""
    logger.info("REQUEST[Register Player]")
    # context = cast(RegisterPlayerContext, message.context)


async def handle_reregister_player_request(player: TrackedPlayer, message: Message) -> None:
    """Handle the Reregister Player request."""
    logger.info("REQUEST[Reregister Player]")


async def handle_unregister_player_request(player: TrackedPlayer, message: Message) -> None:
    """Handle the Unregister Player request."""
    logger.info("REQUEST[Unregister Player]")


async def handle_list_players_request(player: TrackedPlayer, message: Message) -> None:
    """Handle the List Players request."""
    logger.info("REQUEST[List Players]")


async def handle_advertise_game_request(player: TrackedPlayer, message: Message) -> None:
    """Handle the Advertise Game request."""
    logger.info("REQUEST[Advertise Game]")
    # context = cast(AdvertiseGameContext, message.context)


async def handle_list_available_games_request(player: TrackedPlayer, message: Message) -> None:
    """Handle the List Available Games request."""
    logger.info("REQUEST[List Available Games]")


async def handle_join_game_request(player: TrackedPlayer, message: Message) -> None:
    """Handle the Join Game request."""
    # context = cast(JoinGameContext, message.context)
    logger.info("REQUEST[Join Game]")


async def handle_quit_game_request(player: TrackedPlayer, message: Message) -> None:
    """Handle the Quit Game request."""
    logger.info("REQUEST[Quit Game]")


async def handle_start_game_request(player: TrackedPlayer, message: Message) -> None:
    """Handle the Start Game request."""
    logger.info("REQUEST[Start Game]")


async def handle_cancel_game_request(player: TrackedPlayer, message: Message) -> None:
    """Handle the Cancel Game request."""
    logger.info("REQUEST[Cancel Game]")


async def handle_execute_move_request(player: TrackedPlayer, message: Message) -> None:
    """Handle the Execute Move request."""
    logger.info("REQUEST[Execute Move]")
    # context = cast(ExecuteMoveContext, message.context)


async def handle_retrieve_game_state_request(player: TrackedPlayer, message: Message) -> None:
    """Handle the Retrieve Game State request."""
    logger.info("REQUEST[Retrieve Game]")


async def handle_send_message_request(player: TrackedPlayer, message: Message) -> None:
    """Handle the Send Message request."""
    logger.info("REQUEST[Semd Message]")
    # context = cast(SendMessageContext, message.context)


REQUEST_HANDLERS: Dict[MessageType, Callable[[TrackedPlayer, Message], Coroutine[Any, Any, None]]] = {
    MessageType.REREGISTER_PLAYER: handle_reregister_player_request,
    MessageType.UNREGISTER_PLAYER: handle_unregister_player_request,
    MessageType.LIST_PLAYERS: handle_list_players_request,
    MessageType.ADVERTISE_GAME: handle_advertise_game_request,
    MessageType.LIST_AVAILABLE_GAMES: handle_list_available_games_request,
    MessageType.JOIN_GAME: handle_join_game_request,
    MessageType.QUIT_GAME: handle_quit_game_request,
    MessageType.START_GAME: handle_start_game_request,
    MessageType.CANCEL_GAME: handle_cancel_game_request,
    MessageType.EXECUTE_MOVE: handle_execute_move_request,
    MessageType.RETRIEVE_GAME_STATE: handle_retrieve_game_state_request,
    MessageType.SEND_MESSAGE: handle_send_message_request,
}
