# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import,unused-argument

# TODO: need to review these events vs. my docs in API.md (at request and event level) to see whether I've missed anything obvious
# TODO: I think that I am probably not appropriately marking the game as active in all the places that I should
# TODO: this needs unit tests, but probably after the other code is done
# TODO: there are race conditions in here, which I have not fully explored (i.e. player quits game as we're starting it)

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
    "handle_game_execute_move_event",
    "handle_game_player_turn_event",
]

log = logging.getLogger("apologies.event")


async def send_message(
    message: Message,
    websockets: Optional[List[WebSocketServerProtocol]] = None,
    players: Optional[List[TrackedPlayer]] = None,
    player_ids: Optional[List[str]] = None,
    handles: Optional[List[str]] = None,
) -> None:
    """Send a message as JSON to one or more websockets, provided explicitly and/or identified by player id and/or handle."""
    data = message.to_json()
    destinations = set(websockets) if websockets else set()
    destinations.update(await lookup_websockets(players=players, player_ids=player_ids, handles=handles))
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


async def handle_registered_players_event(player: TrackedPlayer) -> None:
    """Handle the Registered Players event."""
    log.info("EVENT[Registered Players]")
    players = [await player.to_registered_player() for player in await lookup_all_players()]
    context = RegisteredPlayersContext(players=players)
    message = Message(MessageType.REGISTERED_PLAYERS, context)
    await send_message(message, players=[player])


async def handle_available_games_event(player: TrackedPlayer) -> None:
    """Handle the Available Games event."""
    log.info("EVENT[Available Games]")
    games = [await game.to_advertised_game() for game in await lookup_available_games(player)]
    context = AvailableGamesContext(games=games)
    message = Message(MessageType.AVAILABLE_GAMES, context)
    await send_message(message, players=[player])


async def handle_player_registered_event(websocket: WebSocketServerProtocol, handle: str) -> None:
    """Handle the Player Registered event."""
    log.info("EVENT[Player Registered]")
    player = await track_player(websocket, handle)
    context = PlayerRegisteredContext(player_id=player.player_id)
    message = Message(MessageType.PLAYER_REGISTERED, context)
    await send_message(message, websockets=[websocket])


async def handle_player_reregistered_event(player: TrackedPlayer, websocket: WebSocketServerProtocol) -> None:
    """Handle the Player Registered event."""
    log.info("EVENT[Player Registered]")
    async with player.lock:
        player.websocket = websocket
    context = PlayerRegisteredContext(player_id=player.player_id)
    message = Message(MessageType.PLAYER_REGISTERED, context)
    await send_message(message, players=[player])


async def handle_player_unregistered_event(player: TrackedPlayer, game: Optional[TrackedGame] = None) -> None:
    """Handle the Player Unregistered event."""
    log.info("EVENT[Player Unregistered]")
    await player.mark_quit()
    if game:
        comment = "Player %s unregistered" % player.handle
        await game.mark_quit(player)
        await handle_game_player_change_event(game, comment)
        if not await game.is_viable():
            await handle_game_cancelled_event(game, CancelledReason.NOT_VIABLE, comment)
    await delete_player(player)


async def handle_player_disconnected_event(websocket: WebSocketServerProtocol) -> None:
    """Handle the Player Disconnected event."""
    log.info("EVENT[Player Disconnected]")
    player = await lookup_player_for_websocket(websocket)
    if player:
        game = await lookup_game(player=player)
        await player.mark_disconnected()
        if game:
            comment = "Player %s disconnected" % player.handle
            await game.mark_quit(player)
            await handle_game_player_change_event(game, comment)
            if not await game.is_viable():
                await handle_game_cancelled_event(game, CancelledReason.NOT_VIABLE, comment)


async def handle_player_idle_event(player: TrackedPlayer) -> None:
    """Handle the Player Idle event."""
    log.info("EVENT[Player Idle]")
    message = Message(MessageType.PLAYER_IDLE)
    await send_message(message, players=[player])
    await player.mark_idle()


async def handle_player_inactive_event(player: TrackedPlayer) -> None:
    """Handle the Player Inactive event."""
    log.info("EVENT[Player Inactive]")
    message = Message(MessageType.PLAYER_INACTIVE)
    game = await lookup_game(player=player)
    await send_message(message, players=[player])
    await player.disconnect()
    await handle_player_unregistered_event(player, game)


async def handle_player_message_received_event(sender_handle: str, recipient_handles: List[str], sender_message: str) -> None:
    """Handle the Player Message Received event."""
    log.info("EVENT[Player Message Received]")
    context = PlayerMessageReceivedContext(sender_handle, recipient_handles, sender_message)
    message = Message(MessageType.PLAYER_MESSAGE_RECEIVED, context)
    await send_message(message, handles=recipient_handles)


async def handle_game_advertised_event(player: TrackedPlayer, advertised: AdvertiseGameContext) -> None:
    """Handle the Game Advertised event."""
    log.info("EVENT[Game Advertised]")
    game = await track_game(player, advertised)
    context = GameAdvertisedContext(game=await game.to_advertised_game())
    message = Message(MessageType.GAME_ADVERTISED, context)
    await send_message(message, players=[player])


async def handle_game_invitation_event(game: TrackedGame, player: Optional[TrackedPlayer] = None) -> None:
    """Handle the Game Invitation event."""
    log.info("EVENT[Game Invitation]")
    context = GameInvitationContext(game=await game.to_advertised_game())
    message = Message(MessageType.GAME_INVITATION, context)
    if player:
        await send_message(message, players=[player])
    else:
        await send_message(message, handles=game.invited_handles)  # safe to reference invited_handles since it does not change


async def handle_game_joined_event(player: TrackedPlayer, game_id: str) -> None:
    """Handle the Game Joined event."""
    log.info("EVENT[Game Joined]")
    game = await lookup_game(game_id=game_id)
    if not game:
        raise ProcessingError(FailureReason.UNKNOWN_GAME)
    await player.mark_joined(game)
    await game.mark_joined(player)
    context = GameJoinedContext(game_id=game_id)
    message = Message(MessageType.GAME_JOINED, context)
    await send_message(message, players=[player])
    if game.is_fully_joined():
        await handle_game_started_event(game)


async def handle_game_started_event(game: TrackedGame) -> None:
    """Handle the Game Started event."""
    log.info("EVENT[Game Started]")
    message = Message(MessageType.GAME_STARTED)
    await game.mark_started()
    players = await lookup_game_players(game)
    for player in players:
        await player.mark_playing()
    await send_message(message, players=players)


async def handle_game_cancelled_event(game: TrackedGame, reason: CancelledReason, comment: Optional[str] = None) -> None:
    """Handle the Game Cancelled event."""
    log.info("EVENT[Game Cancelled]")
    context = GameCancelledContext(reason=reason, comment=comment)
    message = Message(MessageType.GAME_CANCELLED, context)
    players = await lookup_game_players(game)
    for player in players:
        await player.mark_quit()
    await game.mark_cancelled(CancelledReason.CANCELLED, comment)
    await send_message(message, players=players)


async def handle_game_completed_event(game: TrackedGame, comment: Optional[str] = None) -> None:
    """Handle the Game Completed event."""
    log.info("EVENT[Game Completed]")
    context = GameCompletedContext(comment=comment)
    message = Message(MessageType.GAME_COMPLETED, context)
    players = await lookup_game_players(game)
    for player in players:
        await player.mark_quit()
    await game.mark_completed(comment)
    await send_message(message, players=players)


async def handle_game_idle_event(game: TrackedGame) -> None:
    """Handle the Game Idle event."""
    log.info("EVENT[Game Idle]")
    message = Message(MessageType.GAME_IDLE)
    players = await lookup_game_players(game)
    await send_message(message, players=players)


async def handle_game_inactive_event(game: TrackedGame) -> None:
    """Handle the Game Inactive event."""
    log.info("EVENT[Game Inactive]")
    await handle_game_cancelled_event(game, CancelledReason.INACTIVE)


async def handle_game_obsolete_event(game: TrackedGame) -> None:
    """Handle the Game Obsolete event."""
    log.info("EVENT[Game Obsolete]")
    await delete_game(game)


async def handle_game_player_quit_event(player: TrackedPlayer, game: TrackedGame) -> None:
    """Handle the Player Unregistered event."""
    log.info("EVENT[Game Player Quit]")
    comment = "Player %s quit" % player.handle
    await player.mark_quit()
    await game.mark_quit(player)
    await handle_game_player_change_event(game, comment)
    if not await game.is_viable():
        await handle_game_cancelled_event(game, CancelledReason.NOT_VIABLE, comment)


async def handle_game_player_change_event(game: TrackedGame, comment: str) -> None:
    """Handle the Game Player Change event."""
    log.info("EVENT[Game Player Change]")
    async with game.lock:
        players = list(game.game_players.values())
    context = GamePlayerChangeContext(comment=comment, players=players)
    message = Message(MessageType.GAME_PLAYER_CHANGE, context=context)
    await send_message(message, handles=[player.handle for player in players])


# pylint: disable=redefined-argument-from-local
async def handle_game_state_change_event(game: TrackedGame, player: Optional[TrackedPlayer] = None) -> None:
    """Handle the Game State Change event."""
    log.info("EVENT[Game State Change]")
    players = [player] if player else await lookup_game_players(game)
    for player in players:
        view = await game.get_player_view(player)
        context = GameStateChangeContext.for_view(view)
        message = Message(MessageType.GAME_STATE_CHANGE, context=context)
        await send_message(message, players=[player])


async def handle_game_execute_move_event(player: TrackedPlayer, game: TrackedGame, move_id: str) -> None:
    """Handle the Execute Move event."""
    log.info("EVENT[Execute Move]")
    await game.execute_move(player, move_id)
    await handle_game_state_change_event(game)


async def handle_game_player_turn_event(game: TrackedGame, player: TrackedPlayer, moves: List[Move]) -> None:
    """Handle the Game Player Turn event."""
    log.info("EVENT[Game Player Turn]")
    context = GamePlayerTurnContext.for_moves(moves)
    message = Message(MessageType.GAME_PLAYER_TURN, context)
    await send_message(message, players=[player])
