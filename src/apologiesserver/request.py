# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import

"""Coroutines to requests received via Websocket connections."""

# TODO: remove this once manager.py is implemented (it's obsolete)

import logging
from typing import Any, Callable, Coroutine, Dict, Optional, cast

import attr
from websockets import WebSocketServerProtocol

from .event import *
from .interface import *
from .state import *

log = logging.getLogger("apologies.request")


@attr.s(frozen=True)
class RequestContext:
    """Context provided to a request when dispatching it."""

    websocket = attr.ib(type=WebSocketServerProtocol)
    message = attr.ib(type=Message)
    player = attr.ib(type=TrackedPlayer)
    game = attr.ib(type=Optional[TrackedGame])


async def handle_register_player_request(websocket: WebSocketServerProtocol, message: Message) -> None:
    """Handle the Register Player request."""
    log.info("REQUEST[Register Player]")
    context = cast(RegisterPlayerContext, message.context)
    await handle_player_registered_event(websocket, context.handle)


async def handle_reregister_player_request(request: RequestContext) -> None:
    """Handle the Reregister Player request."""
    log.info("REQUEST[Reregister Player]")
    await handle_player_reregistered_event(request.player, request.websocket)


async def handle_unregister_player_request(request: RequestContext) -> None:
    """Handle the Unregister Player request."""
    log.info("REQUEST[Unregister Player]")
    await handle_player_unregistered_event(request.player, request.game)


async def handle_list_players_request(request: RequestContext) -> None:
    """Handle the List Players request."""
    log.info("REQUEST[List Players]")
    await handle_registered_players_event(request.player)


async def handle_advertise_game_request(request: RequestContext) -> None:
    """Handle the Advertise Game request."""
    log.info("REQUEST[Advertise Game]")
    if request.game:
        raise ProcessingError(FailureReason.ALREADY_PLAYING)
    context = cast(AdvertiseGameContext, request.message.context)
    await handle_game_advertised_event(request.player, context)


async def handle_list_available_games_request(request: RequestContext) -> None:
    """Handle the List Available Games request."""
    log.info("REQUEST[List Available Games]")
    await handle_available_games_event(request.player)


async def handle_join_game_request(request: RequestContext) -> None:
    """Handle the Join Game request."""
    log.info("REQUEST[Join Game]")
    if request.game:
        raise ProcessingError(FailureReason.ALREADY_PLAYING)
    context = cast(JoinGameContext, request.message.context)
    await handle_game_joined_event(request.player, context.game_id)


async def handle_quit_game_request(request: RequestContext) -> None:
    """Handle the Quit Game request."""
    log.info("REQUEST[Quit Game]")
    if not request.game:
        raise ProcessingError(FailureReason.NOT_PLAYING)
    if not request.game.is_in_progress():
        raise ProcessingError(FailureReason.INVALID_GAME, "Game is not in progress")
    if request.player.handle == request.game.advertiser_handle:
        raise ProcessingError(FailureReason.ADVERTISER_MAY_NOT_QUIT)
    await handle_game_player_quit_event(request.player, request.game)


async def handle_start_game_request(request: RequestContext) -> None:
    """Handle the Start Game request."""
    log.info("REQUEST[Start Game]")
    if not request.game:
        raise ProcessingError(FailureReason.NOT_PLAYING)
    if request.game.is_playing():
        raise ProcessingError(FailureReason.INVALID_GAME, "Game is already being played")
    if request.game.advertiser_handle != request.player.handle:
        raise ProcessingError(FailureReason.NOT_ADVERTISER)
    await handle_game_started_event(request.game)


async def handle_cancel_game_request(request: RequestContext) -> None:
    """Handle the Cancel Game request."""
    log.info("REQUEST[Cancel Game]")
    if not request.game:
        raise ProcessingError(FailureReason.NOT_PLAYING)
    if not request.game.is_in_progress():
        raise ProcessingError(FailureReason.INVALID_GAME, "Game is not in progress")
    if request.game.advertiser_handle != request.player.handle:
        raise ProcessingError(FailureReason.NOT_ADVERTISER)
    await handle_game_cancelled_event(request.game, CancelledReason.CANCELLED)


async def handle_execute_move_request(request: RequestContext) -> None:
    """Handle the Execute Move request."""
    log.info("REQUEST[Execute Move]")
    if not request.game:
        raise ProcessingError(FailureReason.NOT_PLAYING)
    if not request.game.is_playing():
        raise ProcessingError(FailureReason.INVALID_GAME, "Game is not being played")
    if not request.game.is_move_pending(request.player.handle):
        raise ProcessingError(FailureReason.NO_MOVE_PENDING)
    context = cast(ExecuteMoveContext, request.message.context)
    if not request.game.is_legal_move(request.player.handle, context.move_id):
        raise ProcessingError(FailureReason.ILLEGAL_MOVE)
    await handle_game_execute_move_event(request.player, request.game, context.move_id)


async def handle_retrieve_game_state_request(request: RequestContext) -> None:
    """Handle the Retrieve Game State request."""
    log.info("REQUEST[Retrieve Game]")
    if not request.game:
        raise ProcessingError(FailureReason.NOT_PLAYING)
    if not request.game.is_playing():
        raise ProcessingError(FailureReason.INVALID_GAME, "Game is not being played")
    await handle_game_state_change_event(request.game, request.player)


async def handle_send_message_request(request: RequestContext) -> None:
    """Handle the Send Message request."""
    log.info("REQUEST[Send Message]")
    context = cast(SendMessageContext, request.message.context)
    await handle_player_message_received_event(request.player.handle, context.recipient_handles, context.message)


_REQUEST_HANDLERS: Dict[MessageType, Callable[[RequestContext], Coroutine[Any, Any, None]]] = {
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


def lookup_handler(message_type: MessageType) -> Callable[[RequestContext], Coroutine[Any, Any, None]]:
    """Lookup the handler coroutine for a message type."""
    if message_type not in _REQUEST_HANDLERS:
        raise ProcessingError(FailureReason.INTERNAL_ERROR)
    return _REQUEST_HANDLERS[message_type]
