# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import,unused-argument

# TODO: remove pylint unused-argument once these functions are implemented

"""Coroutines to events, most of which publish data to Websocket connections."""

import asyncio
import logging
from typing import List, Optional, Sequence

from websockets import WebSocketServerProtocol

from .interface import *
from .state import lookup_websockets

__all__ = [
    "send_message",
    "handle_request_failed_event",
    "handle_server_shutdown_event",
    "handle_registered_players_event",
    "handle_available_games_event",
    "handle_player_registered_event",
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
    "handle_game_player_change_event",
    "handle_game_state_change_event",
    "handle_game_player_turn_event",
]

log = logging.getLogger("apologies.event")


async def send_message(
    message: Message,
    websockets: Optional[Sequence[WebSocketServerProtocol]] = None,
    player_ids: Optional[Sequence[str]] = None,
    handles: Optional[Sequence[str]] = None,
) -> None:
    """Send a message as JSON to one or more websockets, provided explicitly and/or identified by player id and/or handle."""
    data = message.to_json()
    destinations: List[WebSocketServerProtocol] = list(websockets) if websockets else []
    destinations += await lookup_websockets(player_ids=player_ids, handles=handles)
    log.debug("Sending message to %d websockets: %s", len(destinations), data)
    await asyncio.wait([destination.send(data) for destination in destinations])


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


async def handle_registered_players_event() -> None:
    """Handle the Registered Players event."""
    log.info("EVENT[Registered Players]")


async def handle_available_games_event() -> None:
    """Handle the Available Games event."""
    log.info("EVENT[Available Games]")


async def handle_player_registered_event() -> None:
    """Handle the Player Registered event."""
    log.info("EVENT[Player Registered]")


async def handle_player_disconnected_event() -> None:
    """Handle the Player Disconnected event."""
    log.info("EVENT[Player Disconnected]")


async def handle_player_idle_event(player_id: str) -> None:
    """Handle the Player Idle event."""
    log.info("EVENT[Player Idle]")


async def handle_player_inactive_event(player_id: str) -> None:
    """Handle the Player Inactive event."""
    log.info("EVENT[Player Inactive]")


async def handle_player_message_received_event() -> None:
    """Handle the Player Message Received event."""
    log.info("EVENT[Player Message Received]")


async def handle_game_advertised_event() -> None:
    """Handle the Game Advertised event."""
    log.info("EVENT[Game Advertised]")


async def handle_game_invitation_event() -> None:
    """Handle the Game Invitation event."""
    log.info("EVENT[Game Invitation]")


async def handle_game_joined_event() -> None:
    """Handle the Game Joined event."""
    log.info("EVENT[Game Joined]")


async def handle_game_started_event() -> None:
    """Handle the Game Started event."""
    log.info("EVENT[Game Started]")


async def handle_game_cancelled_event() -> None:
    """Handle the Game Cancelled event."""
    log.info("EVENT[Game Cancelled]")


async def handle_game_completed_event() -> None:
    """Handle the Game Completed event."""
    log.info("EVENT[Game Completed]")


async def handle_game_idle_event(game_id: str) -> None:
    """Handle the Game Idle event."""
    log.info("EVENT[Game Idle]")


async def handle_game_inactive_event(game_id: str) -> None:
    """Handle the Game Inactive event."""
    log.info("EVENT[Game Inactive]")


async def handle_game_obsolete_event(game_id: str) -> None:
    """Handle the Game Obsolete event."""
    log.info("EVENT[Game Obsolete]")


async def handle_game_player_change_event() -> None:
    """Handle the Game Player Change event."""
    log.info("EVENT[Game Player Change]")


async def handle_game_state_change_event() -> None:
    """Handle the Game State Change event."""
    log.info("EVENT[Game State Change]")


async def handle_game_player_turn_event() -> None:
    """Handle the Game Player Turn event."""
    log.info("EVENT[Game Player Turn]")
