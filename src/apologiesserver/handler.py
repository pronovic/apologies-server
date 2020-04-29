# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import,unused-variable,unused-argument

# TODO: remove unused-variable and unused-argument once code is done
# TODO: all of the coroutines need some sort of logging so we can track what is going on

from asyncio import Future  # pylint: disable=unused-import
from typing import Optional

from websockets import WebSocketServerProtocol

from .interface import *

__all__ = [
    "handle_idle_game_check",
    "handle_idle_player_check",
    "handle_obsolete_game_check",
    "handle_register_player",
    "handle_reregister_player",
    "handle_unregister_player",
    "handle_list_players",
    "handle_advertise_game",
    "handle_list_available_games",
    "handle_join_game",
    "handle_quit_game",
    "handle_start_game",
    "handle_cancel_game",
    "handle_execute_move",
    "handle_retrieve_game_state",
    "handle_send_message",
    "handle_server_shutdown",
    "handle_request_failed",
]


async def _handle_registered_players() -> None:
    """Handle the Registered Players event."""


async def _handle_available_games() -> None:
    """Handle the AvailableGames event."""


async def _handle_player_registered(player_id: str) -> None:
    """Handle the Player Registered event."""
    # context = PlayerRegisteredContext(player_id)
    # message = Message(MessageType.PLAYER_REGISTERED, context)
    # await _send(message, [player_id])


async def _handle_player_disconnected() -> None:
    """Handle the Player Disconnected event."""


async def _handle_player_idle(player_id: str) -> None:
    """Handle the Player Idle event."""
    # message = Message(MessageType.PLAYER_IDLE)
    # await _send(message, [player_id])


async def _handle_player_inactive() -> None:
    """Handle the Player Inactive event."""


async def _handle_player_message_received() -> None:
    """Handle the Player Message Received event."""


async def _handle_game_advertised() -> None:
    """Handle the GameAdvertised event."""


async def _handle_game_invitation() -> None:
    """Handle the Game Invitation event."""


async def _handle_game_joined() -> None:
    """Handle the Game Joined event."""


async def _handle_game_started() -> None:
    """Handle the Game Started event."""


async def _handle_game_cancelled(game_id: str, reason: CancelledReason) -> None:
    """Handle the Game Cancelled event."""


async def _handle_game_completed(game_id: str, comment: str) -> None:
    """Handle the Game Completed event."""
    # context = GameCompletedContext(comment)
    # message = Message(MessageType.GAME_COMPLETED, context)
    # recipients = lookup_websockets(game_id=game_id)
    # await _send(message, recipients)


async def _handle_game_idle(game_id: str) -> None:
    """Handle the Game Idle event."""
    # message = Message(MessageType.GAME_IDLE)
    # recipients = lookup_websockets(game_id=game_id)
    # await _send(message, recipients)


async def _handle_game_inactive(game_id: str) -> None:
    """Handle the Game Inactive event."""
    # await _handle_game_cancelled(game_id, CancelledReason.INACTIVE)


async def _handle_game_obsolete(game_id: str) -> None:
    """Handle the Game Obsolete event."""
    # stop_tracking_game(game_id)


async def _handle_game_player_change(player_id: str) -> None:
    """Handle the Game PlayerChange event."""


async def _handle_game_state_change(game_id: str, player_id: Optional[str]) -> None:
    """Handle the Game State Change event."""
    # for id in [player_id] if player_id else lookup_player_ids(game_id=game_id):
    #     recipient = lookup_websocket(id)
    #     context = retrieve_game_state(game_id, id)
    #     message = Message(MessageType.GAME_STATE_CHANGE, context)
    #     await _send(message, [recipient])


async def _handle_game_player_turn() -> None:
    """Handle the Game Player Turn event."""


# async def _send(message: Message, recipients: Sequence[WebSocketServerProtocol]) -> None:
#     """Send the same message to a set of websockets."""
#     # TODO: this should probably be in terms of player ids, so we can check whether they're not disconnected before sending?
#     data = message.to_json()
#     await asyncio.wait([recipient.send(data) for recipient in recipients])


async def handle_idle_game_check() -> None:
    """Execute the Idle Game Check task."""


async def handle_idle_player_check() -> None:
    """Execute the Idle Player Check task."""


async def handle_obsolete_game_check() -> None:
    """Execute the Obsolete Game Check task."""


async def handle_register_player(websocket: WebSocketServerProtocol, message: Message) -> None:
    """Handle the Register Player request."""
    # player = track_new_player()
    # context = cast(RegisterPlayerContext, message.context)
    # await _handle_player_registered(player)


async def handle_reregister_player(player_id: str, _message: Message) -> None:
    """Handle the Reregister Player request."""
    # player = mark_player_active(player_id)
    # await _handle_player_registered(player_id)


async def handle_unregister_player(player_id: str, _message: Message) -> None:
    """Handle the Unregister Player request."""
    # player = mark_player_active(player_id)
    # await _handle_game_player_change(player_id)


async def handle_list_players(player_id: str, message: Message) -> None:
    """Handle the List Players request."""
    # player = mark_player_active(player_id)


async def handle_advertise_game(player_id: str, message: Message) -> None:
    """Handle the Advertise Game request."""
    # player = mark_player_active(player_id)
    # context = cast(AdvertiseGameContext, message.context)


async def handle_list_available_games(player_id: str, message: Message) -> None:
    """Handle the List Available Games request."""
    # player = mark_player_active(player_id)


async def handle_join_game(player_id: str, message: Message) -> None:
    """Handle the Join Game request."""
    # player = mark_player_active(player_id)
    # context = cast(JoinGameContext, message.context)


async def handle_quit_game(player_id: str, message: Message) -> None:
    """Handle the Quit Game request."""
    # player = mark_player_active(player_id)


async def handle_start_game(player_id: str, message: Message) -> None:
    """Handle the Start Game request."""
    # player = mark_player_active(player_id)


async def handle_cancel_game(player_id: str, message: Message) -> None:
    """Handle the Cancel Game request."""
    # player = mark_player_active(player_id)


async def handle_execute_move(player_id: str, message: Message) -> None:
    """Handle the Execute Move request."""
    # player = mark_player_active(player_id)
    # context = cast(ExecuteMoveContext, message.context)


async def handle_retrieve_game_state(player_id: str, message: Message) -> None:
    """Handle the Retrieve Game State request."""
    # player = mark_player_active(player_id)
    # await _handle_game_state_change(player.game_id, player)


async def handle_send_message(player_id: str, message: Message) -> None:
    """Handle the Send Message request."""
    # player = mark_player_active(player_id)
    # context = cast(SendMessageContext, message.context)


async def handle_server_shutdown() -> None:
    """Handle the Server Shutdown event."""
    # message = Message(MessageType.SERVER_SHUTDOWN)
    # await _send(message, lookup_all_players(disconnected=False))


# noinspection PyBroadException
async def handle_request_failed(websocket: WebSocketServerProtocol, exception: Exception) -> None:
    """Handle the Request Failed event."""
    # try:
    #     raise exception
    # except ProcessingError as e:
    #     context = RequestFailedContext(e.reason, e.comment)
    # except ValueError as e:
    #     context = RequestFailedContext(FailureReason.INVALID_REQUEST, "%s" % e)
    # except Exception as e:  # pylint: disable=broad-except
    #     context = RequestFailedContext(FailureReason.INTERNAL_ERROR, FailureReason.INTERNAL_ERROR.value)
    # message = Message(MessageType.REQUEST_FAILED, context)
    # await _send(message, websocket)    # try:
    #     raise exception
    # except ProcessingError as e:
    #     context = RequestFailedContext(e.reason, e.comment)
    # except ValueError as e:
    #     context = RequestFailedContext(FailureReason.INVALID_REQUEST, "%s" % e)
    # except Exception as e:  # pylint: disable=broad-except
    #     context = RequestFailedContext(FailureReason.INTERNAL_ERROR, FailureReason.INTERNAL_ERROR.value)
    # message = Message(MessageType.REQUEST_FAILED, context)
    # await _send(message, websocket)
