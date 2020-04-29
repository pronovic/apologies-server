# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import

"""Coroutines to events, most of which publish data to Websocket connections."""

# TODO: all of the coroutines need some sort of logging so we can track what is going on

import asyncio
from typing import List, Optional, Sequence

from websockets import WebSocketServerProtocol

from .interface import *
from .state import lookup_websockets


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
    await asyncio.wait([destination.send(data) for destination in destinations])


# noinspection PyBroadException
async def handle_request_failed_event(websocket: WebSocketServerProtocol, exception: Exception) -> None:
    """Handle the Request Failed event."""
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


async def handle_registered_players_event() -> None:
    """Handle the Registered Players event."""


async def handle_available_games_event() -> None:
    """Handle the AvailableGames event."""


async def handle_player_registered_event() -> None:
    """Handle the Player Registered event."""


async def handle_player_disconnected_event() -> None:
    """Handle the Player Disconnected event."""


async def handle_player_idle_event() -> None:
    """Handle the Player Idle event."""


async def handle_player_inactive_event() -> None:
    """Handle the Player Inactive event."""


async def handle_player_message_received_event() -> None:
    """Handle the Player Message Received event."""


async def handle_game_advertised_event() -> None:
    """Handle the GameAdvertised event."""


async def handle_game_invitation_event() -> None:
    """Handle the Game Invitation event."""


async def handle_game_joined_event() -> None:
    """Handle the Game Joined event."""


async def handle_game_started_event() -> None:
    """Handle the Game Started event."""


async def handle_game_cancelled_event() -> None:
    """Handle the Game Cancelled event."""


async def handle_game_completed_event() -> None:
    """Handle the Game Completed event."""


async def handle_game_idle_event() -> None:
    """Handle the Game Idle event."""


async def handle_game_inactive_event() -> None:
    """Handle the Game Inactive event."""


async def handle_game_obsolete_event() -> None:
    """Handle the Game Obsolete event."""


async def handle_game_player_change_event() -> None:
    """Handle the Game PlayerChange event."""


async def handle_game_state_change_event() -> None:
    """Handle the Game State Change event."""


async def handle_game_player_turn_event() -> None:
    """Handle the Game Player Turn event."""
