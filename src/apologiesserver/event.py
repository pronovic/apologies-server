# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import

"""Coroutines to events, most of which publish data to Websocket connections."""

import asyncio
import logging
from typing import List, Optional

from apologies.rules import Move
from websockets import WebSocketServerProtocol

from .interface import *
from .state import *

__all__ = [
    "send_message",
    "handle_request_failed_event",
    "handle_server_shutdown_event",
    "handle_registered_players_event",
    "handle_available_games_event",
    "handle_player_registered_event",
    "handle_player_reregistered_event",
    "handle_player_unregistered_event",
    "handle_player_disconnected_event",
    "handle_player_idle_event",
    "handle_player_inactive_event",
    "handle_player_message_received_event",
    "handle_game_advertised_event",
    "handle_game_invitation_event",
    "handle_game_joined_event",
    "handle_game_started_event",
    "handle_game_cancelled_event",
    "handle_game_completed_event",
    "handle_game_idle_event",
    "handle_game_inactive_event",
    "handle_game_obsolete_event",
    "handle_game_player_quit_event",
    "handle_game_player_change_event",
    "handle_game_state_change_event",
    "handle_game_player_turn_event",
]

log = logging.getLogger("apologies.event")


async def send_message(
    message: Message,
    websockets: Optional[List[WebSocketServerProtocol]] = None,
    player_ids: Optional[List[str]] = None,
    handles: Optional[List[str]] = None,
) -> None:
    """Send a message as JSON to one or more websockets, provided explicitly and/or identified by player id and/or handle."""
    data = message.to_json()
    destinations = set(websockets) if websockets else set()
    destinations.update(await lookup_websockets(player_ids=player_ids, handles=handles))
    log.debug("Sending message to %d websockets: %s", len(destinations), data)
    await asyncio.wait([destination.send(data) for destination in destinations])
    # TODO: not sure what happens here if sending data fails; may need to handle an error and disconnect the player?


# noinspection PyBroadException
async def handle_request_failed_event(websocket: WebSocketServerProtocol, exception: Exception) -> None:
    """Handle the Request Failed event."""
    log.info("EVENT[Request Failed] -- %s %s", websocket, str(exception))
    try:
        raise exception
    except ProcessingError as e:
        context = RequestFailedContext(e.reason, e.comment if e.comment else e.reason.value)
    except ValueError as e:
        context = RequestFailedContext(FailureReason.INVALID_REQUEST, str(e))
    except Exception as e:  # pylint: disable=broad-except
        context = RequestFailedContext(FailureReason.INTERNAL_ERROR, FailureReason.INTERNAL_ERROR.value)
    message = Message(MessageType.REQUEST_FAILED, context)
    await send_message(message, websockets=[websocket])


async def handle_server_shutdown_event() -> None:
    """Handle the Server Shutdown event."""
    log.info("EVENT[Server Shutdown]")
    message = Message(MessageType.SERVER_SHUTDOWN)
    websockets = await lookup_all_websockets()
    await send_message(message, websockets=websockets)


async def handle_registered_players_event(player_id: str) -> None:
    """Handle the Registered Players event."""
    log.info("EVENT[Registered Players]")
    players = [await player.to_registered_player() for player in await lookup_connected_players()]
    context = RegisteredPlayersContext(players=players)
    message = Message(MessageType.REGISTERED_PLAYERS, context)
    await send_message(message, player_ids=[player_id])


async def handle_available_games_event(player_id: str) -> None:
    """Handle the Available Games event."""
    log.info("EVENT[Available Games]")
    games = [await game.to_available_game() for game in await lookup_available_games(player_id)]
    context = AvailableGamesContext(games=games)
    message = Message(MessageType.AVAILABLE_GAMES, context)
    await send_message(message, player_ids=[player_id])


async def handle_player_registered_event(websocket: WebSocketServerProtocol, handle: str) -> None:
    """Handle the Player Registered event."""
    log.info("EVENT[Player Registered]")
    player_id = await track_player(websocket, handle)
    context = PlayerRegisteredContext(player_id=player_id)
    message = Message(MessageType.PLAYER_REGISTERED, context)
    await send_message(message, websockets=[websocket])


async def handle_player_reregistered_event(player_id: str) -> None:
    """Handle the Player Registered event."""
    log.info("EVENT[Player Registered]")
    player = await lookup_player(player_id)
    if not player:
        raise ProcessingError(FailureReason.UNKNOWN_PLAYER)
    context = PlayerRegisteredContext(player_id=player_id)
    message = Message(MessageType.PLAYER_REGISTERED, context)
    await send_message(message, player_ids=[player_id])


async def handle_player_unregistered_event(player_id: str) -> None:
    """Handle the Player Unregistered event."""
    log.info("EVENT[Player Unregistered]")
    handle, game_id, viable = await mark_player_quit(player_id)
    if game_id:
        comment = "Player %s unregistered" % handle
        await handle_game_player_change_event(game_id, comment)
        if not viable:
            await handle_game_cancelled_event(game_id, CancelledReason.NOT_VIABLE, comment)
    await delete_player(player_id)


async def handle_player_disconnected_event(player_id: str) -> None:
    """Handle the Player Disconnected event."""
    log.info("EVENT[Player Disconnected]")
    handle, game_id, viable = await mark_player_disconnected(player_id)
    if game_id:
        comment = "Player %s was disconnected" % handle
        await handle_game_player_change_event(game_id, comment)
        if not viable:
            await handle_game_cancelled_event(game_id, CancelledReason.NOT_VIABLE, comment)


async def handle_player_idle_event(player_id: str) -> None:
    """Handle the Player Idle event."""
    log.info("EVENT[Player Idle]")
    message = Message(MessageType.PLAYER_IDLE)
    await send_message(message, player_ids=[player_id])
    await mark_player_idle(player_id)


async def handle_player_inactive_event(player_id: str) -> None:
    """Handle the Player Inactive event."""
    log.info("EVENT[Player Inactive]")
    message = Message(MessageType.PLAYER_INACTIVE)
    await send_message(message, player_ids=[player_id])
    await disconnect_player(player_id)
    await handle_player_unregistered_event(player_id)


async def handle_player_message_received_event(player_id: str, recipient_handles: List[str], sender_message: str) -> None:
    """Handle the Player Message Received event."""
    log.info("EVENT[Player Message Received]")
    sender_handle = await lookup_player_handle(player_id)
    if sender_handle:
        context = PlayerMessageReceivedContext(sender_handle, recipient_handles, sender_message)
        message = Message(MessageType.PLAYER_MESSAGE_RECEIVED, context)
        await send_message(message, handles=recipient_handles)


async def handle_game_advertised_event(player_id: str, advertised: AdvertiseGameContext) -> None:
    """Handle the Game Advertised event."""
    log.info("EVENT[Game Advertised]")
    game = await track_game(player_id, advertised)
    available = await game.to_available_game()
    context = GameAdvertisedContext(game=available)
    message = Message(MessageType.GAME_ADVERTISED, context)
    await send_message(message, player_ids=[player_id])


async def handle_game_invitation_event(player_id: str, game_id: str) -> None:
    """Handle the Game Invitation event."""
    log.info("EVENT[Game Invitation]")
    game = await lookup_game(game_id)
    if not game:
        raise ProcessingError(FailureReason.INTERNAL_ERROR)
    available = await game.to_available_game()
    context = GameInvitationContext(game=available)
    message = Message(MessageType.GAME_INVITATION, context)
    await send_message(message, player_ids=[player_id])


async def handle_game_joined_event(player_id: str, game_id: str) -> None:
    """Handle the Game Joined event."""
    log.info("EVENT[Game Joined]")
    context = GameJoinedContext(game_id=game_id)
    message = Message(MessageType.GAME_JOINED, context)
    await mark_player_joined(player_id, game_id)
    await send_message(message, player_ids=[player_id])


async def handle_game_started_event(game_id: str) -> None:
    """Handle the Game Started event."""
    log.info("EVENT[Game Started]")
    message = Message(MessageType.GAME_STARTED)
    handles = await mark_game_started(game_id)
    await send_message(message, handles=handles)


async def handle_game_cancelled_event(game_id: str, reason: CancelledReason, comment: Optional[str] = None) -> None:
    """Handle the Game Cancelled event."""
    log.info("EVENT[Game Cancelled]")
    context = GameCancelledContext(reason=reason, comment=comment)
    message = Message(MessageType.GAME_CANCELLED, context)
    handles = await mark_game_cancelled(game_id, reason, comment)
    await send_message(message, handles=handles)


async def handle_game_completed_event(game_id: str, comment: Optional[str] = None) -> None:
    """Handle the Game Completed event."""
    log.info("EVENT[Game Completed]")
    context = GameCompletedContext(comment=comment)
    message = Message(MessageType.GAME_COMPLETED, context)
    handles = await mark_game_completed(game_id, comment)
    await send_message(message, handles=handles)


async def handle_game_idle_event(game_id: str) -> None:
    """Handle the Game Idle event."""
    log.info("EVENT[Game Idle]")
    message = Message(MessageType.GAME_IDLE)
    handles = await mark_game_idle(game_id)
    await send_message(message, handles=handles)


async def handle_game_inactive_event(game_id: str) -> None:
    """Handle the Game Inactive event."""
    log.info("EVENT[Game Inactive]")
    message = Message(MessageType.GAME_CANCELLED)
    handles = await mark_game_cancelled(game_id, CancelledReason.INACTIVE)
    await send_message(message, handles=handles)


async def handle_game_obsolete_event(game_id: str) -> None:
    """Handle the Game Obsolete event."""
    log.info("EVENT[Game Obsolete]")
    await delete_game(game_id)


async def handle_game_player_quit_event(player_id: str) -> None:
    """Handle the Player Unregistered event."""
    log.info("EVENT[Game Player Quit]")
    handle, game_id, viable = await mark_player_quit(player_id)
    if game_id:
        comment = "Player %s quit" % handle
        await handle_game_player_change_event(game_id, comment)
        if not viable:
            await handle_game_cancelled_event(game_id, CancelledReason.NOT_VIABLE, comment)
    await delete_player(player_id)


async def handle_game_player_change_event(game_id: str, comment: str) -> None:
    """Handle the Game Player Change event."""
    log.info("EVENT[Game Player Change]")
    players = await lookup_game_players(game_id)
    handles = [player.handle for player in players.values() if player.handle is not None]
    context = GamePlayerChangeContext(comment=comment, players=players)
    message = Message(MessageType.GAME_PLAYER_CHANGE, context)
    await send_message(message, handles=handles)


async def handle_game_state_change_event(game_id: str, requester_handle: Optional[str] = None) -> None:
    """Handle the Game State Change event."""
    log.info("EVENT[Game State Change]")
    state = await lookup_game_state(game_id)
    for handle, view in state.items():
        if not requester_handle or handle == requester_handle:
            context = GameStateChangeContext.for_view(view)
            message = Message(MessageType.GAME_STATE_CHANGE, context)
            await send_message(message, handles=[handle])


async def handle_game_player_turn_event(player_id: str, moves: List[Move]) -> None:
    """Handle the Game Player Turn event."""
    log.info("EVENT[Game Player Turn]")
    context = GamePlayerTurnContext.for_moves(moves)
    message = Message(MessageType.GAME_PLAYER_TURN, context)
    await send_message(message, player_ids=[player_id])
