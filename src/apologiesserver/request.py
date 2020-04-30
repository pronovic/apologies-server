# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import

"""Coroutines to requests received via Websocket connections."""

import logging
from typing import Any, Callable, Coroutine, Dict, cast

from websockets import WebSocketServerProtocol

from .event import *
from .interface import *
from .state import *

log = logging.getLogger("apologies.request")


async def handle_register_player_request(websocket: WebSocketServerProtocol, message: Message) -> None:
    """Handle the Register Player request."""
    log.info("REQUEST[Register Player]")
    context = cast(RegisterPlayerContext, message.context)
    await handle_player_registered_event(websocket, context.handle)


async def handle_reregister_player_request(player_id: str, _: Message) -> None:
    """Handle the Reregister Player request."""
    log.info("REQUEST[Reregister Player]")
    await handle_player_reregistered_event(player_id)


async def handle_unregister_player_request(player_id: str, _: Message) -> None:
    """Handle the Unregister Player request."""
    log.info("REQUEST[Unregister Player]")
    await handle_player_unregistered_event(player_id)


async def handle_list_players_request(player_id: str, _: Message) -> None:
    """Handle the List Players request."""
    log.info("REQUEST[List Players]")
    await handle_registered_players_event(player_id)


async def handle_advertise_game_request(player_id: str, message: Message) -> None:
    """Handle the Advertise Game request."""
    log.info("REQUEST[Advertise Game]")
    context = cast(AdvertiseGameContext, message.context)
    await handle_game_advertised_event(player_id, context)


async def handle_list_available_games_request(player_id: str, _: Message) -> None:
    """Handle the List Available Games request."""
    log.info("REQUEST[List Available Games]")
    await handle_available_games_event(player_id)


async def handle_join_game_request(player_id: str, message: Message) -> None:
    """Handle the Join Game request."""
    log.info("REQUEST[Join Game]")
    context = cast(JoinGameContext, message.context)
    await handle_game_joined_event(player_id, context.game_id)


async def handle_quit_game_request(player_id: str, _: Message) -> None:
    """Handle the Quit Game request."""
    log.info("REQUEST[Quit Game]")
    await handle_game_player_quit_event(player_id)


async def handle_start_game_request(player_id: str, _: Message) -> None:
    """Handle the Start Game request."""
    log.info("REQUEST[Start Game]")
    game_id = await lookup_player_game_id(player_id)
    if not game_id:
        raise ProcessingError(FailureReason.NO_GAME)
    await handle_game_started_event(game_id)


async def handle_cancel_game_request(player_id: str, _: Message) -> None:
    """Handle the Cancel Game request."""
    log.info("REQUEST[Cancel Game]")
    game_id = await lookup_player_game_id(player_id)
    if not game_id:
        raise ProcessingError(FailureReason.NO_GAME)
    await handle_game_cancelled_event(game_id, CancelledReason.CANCELLED)


# TODO: remove the unused-argument thing after this is done
async def handle_execute_move_request(player_id: str, message: Message) -> None:  # pylint: disable=unused-argument
    """Handle the Execute Move request."""
    log.info("REQUEST[Execute Move]")
    # context = cast(ExecuteMoveContext, message.context)


async def handle_retrieve_game_state_request(player_id: str, _: Message) -> None:
    """Handle the Retrieve Game State request."""
    log.info("REQUEST[Retrieve Game]")
    handle = await lookup_player_handle(player_id)
    if not handle:
        raise ProcessingError(FailureReason.UNKNOWN_PLAYER)
    game_id = await lookup_player_game_id(player_id)
    if not game_id:
        raise ProcessingError(FailureReason.NO_GAME)
    await handle_game_state_change_event(game_id, handle)


async def handle_send_message_request(player_id: str, message: Message) -> None:
    """Handle the Send Message request."""
    log.info("REQUEST[Semd Message]")
    context = cast(SendMessageContext, message.context)
    await handle_player_message_received_event(player_id, context.recipient_handles, context.message)


REQUEST_HANDLERS: Dict[MessageType, Callable[[str, Message], Coroutine[Any, Any, None]]] = {
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
