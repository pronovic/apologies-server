# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import

"""
Event handlers.

All event handlers operate in terms of passed-in state, encapsulated in the StateManager
object.  The caller must ensure that 1) the state manager is locked before calling any
handler methods other than execute() and 2) that the execute() method is called once 
at the end of processing but outside of the manager lock.  The goal is to ensure that 
state-related operations are fast and non-blocking, and happen behind a clear transaction 
boundary.  Any tasks that might block (such as network requests) should be added to the 
task queue, to be executed by the execute() method once state updates have been completed.  
"""

from __future__ import annotations  # see: https://stackoverflow.com/a/33533514/2907667

import asyncio
import logging
from typing import List, Optional, Set, Tuple, cast

import attr
import pendulum
from apologies.rules import Move, Rules
from apologies.source import RewardV1InputSource
from ordered_set import OrderedSet  # this makes expected results easier to articulate in test code
from websockets import WebSocketServerProtocol

from .config import config
from .interface import *
from .manager import StateManager, TrackedGame, TrackedPlayer, TrackedWebsocket
from .util import close, send

log = logging.getLogger("apologies.event")


@attr.s(frozen=True)
class RequestContext:
    """Context provided to a request handler method."""

    message = attr.ib(type=Message)
    websocket = attr.ib(type=WebSocketServerProtocol)
    player = attr.ib(type=TrackedPlayer)
    game = attr.ib(type=Optional[TrackedGame], default=None)


# noinspection PyMethodMayBeStatic
@attr.s
class TaskQueue:

    """A queue of asynchronous tasks to be executed."""

    messages = attr.ib(type=List[Tuple[str, WebSocketServerProtocol]])
    disconnects = attr.ib(type=Set[WebSocketServerProtocol])

    @messages.default
    def _messages_default(self) -> List[Tuple[str, WebSocketServerProtocol]]:
        return []

    @disconnects.default
    def _disconnects_default(self) -> OrderedSet[WebSocketServerProtocol]:
        return OrderedSet()

    def is_empty(self) -> bool:
        return len(self.messages) == 0 and len(self.disconnects) == 0

    def clear(self) -> None:
        del self.messages[:]
        self.disconnects.clear()

    def message(
        self,
        message: Message,
        websockets: Optional[List[WebSocketServerProtocol]] = None,
        players: Optional[List[TrackedPlayer]] = None,
    ) -> None:
        """Enqueue a task to send a message to one or more destination websockets."""
        destinations = OrderedSet(websockets) if websockets else OrderedSet()
        destinations.update([player.websocket for player in players if player.websocket] if players else [])
        self.messages.extend([(message.to_json(), destination) for destination in destinations])

    def disconnect(self, websocket: Optional[WebSocketServerProtocol]) -> None:
        """Enqueue a task to disconnect a websocket."""
        if websocket:
            self.disconnects.add(websocket)

    async def execute(self) -> None:
        """Execute all tasks in the queue, sending messages first and then disconnecting websockets."""
        # It seems like there could be a race condition here.  The messages need to be sent in order,
        # and that does seem to work.  However, if things happen really fast (i.e. a client receives
        # a message and triggers another event before we finish sending all of these messages) then it
        # seems possible that the messages for that second event could be intermingled with these.  I
        # guess it's unlikely?  But I'm leaving this note here in case I ever have to debug some strange
        # behavior with messages being received out-of-order.
        tasks = [send(websocket, message) for message, websocket in self.messages]
        if tasks:
            for task in tasks:
                await asyncio.wait([task])  # if we do them all at once, they can get sent out of order
        tasks = [close(websocket) for websocket in self.disconnects]
        if tasks:
            await asyncio.wait(tasks)  # TODO: not entirely sure how we handle errors that happen here


# pylint: disable=too-many-public-methods
@attr.s
class EventHandler:

    manager = attr.ib(type=StateManager)
    queue = attr.ib(type=TaskQueue)

    @queue.default
    def _default_queue(self) -> TaskQueue:
        return TaskQueue()

    def __enter__(self) -> EventHandler:
        self.queue.clear()
        return self

    def __exit__(self, _type, _value, _tb) -> None:  # type: ignore
        self.queue.clear()

    async def execute_tasks(self) -> None:
        """Send all enqueued tasks."""
        # This should not be invoked from within the manager lock!  We want code within the lock to run fast, without blocking.
        await self.queue.execute()

    # noinspection PyTypeChecker
    def handle_idle_websocket_check_task(self) -> Tuple[int, int]:
        """Execute the Idle Websocket Check task, returning tuple of (idle, inactive)."""
        log.info("Scheduled - IDLE_WEBSOCKET_CHECK")
        idle = 0
        inactive = 0
        now = pendulum.now()
        idle_thresh_min = config().websocket_idle_thresh_min
        inactive_thresh_min = config().websocket_inactive_thresh_min
        for (websocket, last_active_date, players) in self.manager.lookup_websocket_activity():
            if players < 1:  # by definition, a websocket is not idle until or unless it has no registered players
                since_active = now.diff(last_active_date).in_minutes()
                if since_active >= inactive_thresh_min:
                    inactive += 1
                    self.handle_websocket_inactive_event(websocket)
                elif since_active >= idle_thresh_min:
                    idle += 1
                    self.handle_websocket_idle_event(websocket)
        log.debug("Idle websocket check completed, found %d idle and %d inactive websockets", idle, inactive)
        return idle, inactive

    # noinspection PyTypeChecker
    def handle_idle_player_check_task(self) -> Tuple[int, int]:
        """Execute the Idle Player Check task, returning tuple of (idle, inactive)."""
        log.info("Scheduled - IDLE_PLAYER_CHECK")
        idle = 0
        inactive = 0
        now = pendulum.now()
        idle_thresh_min = config().player_idle_thresh_min
        inactive_thresh_min = config().player_inactive_thresh_min
        for (player, last_active_date, connection_state) in self.manager.lookup_player_activity():
            disconnected = connection_state == ConnectionState.DISCONNECTED
            since_active = now.diff(last_active_date).in_minutes()
            if since_active >= inactive_thresh_min:
                inactive += 1
                self.handle_player_inactive_event(player)
            elif since_active >= idle_thresh_min:
                if disconnected:
                    inactive += 1
                    self.handle_player_inactive_event(player)
                else:
                    idle += 1
                    self.handle_player_idle_event(player)
        log.debug("Idle player check completed, found %d idle and %d inactive players", idle, inactive)
        return idle, inactive

    # noinspection PyTypeChecker
    def handle_idle_game_check_task(self) -> Tuple[int, int]:
        """Execute the Idle Game Check task, returning tuple of (idle, inactive)."""
        log.info("Scheduled - IDLE_GAME_CHECK")
        idle = 0
        inactive = 0
        now = pendulum.now()
        idle_thresh_min = config().game_idle_thresh_min
        inactive_thresh_min = config().game_inactive_thresh_min
        for (game, last_active_date) in self.manager.lookup_game_activity():
            since_active = now.diff(last_active_date).in_minutes()
            if since_active >= inactive_thresh_min:
                inactive += 1
                self.handle_game_inactive_event(game)
            elif since_active >= idle_thresh_min:
                idle += 1
                self.handle_game_idle_event(game)
        log.debug("Idle game check completed, found %d idle and %d inactive games", idle, inactive)
        return idle, inactive

    # noinspection PyTypeChecker
    def handle_obsolete_game_check_task(self) -> int:
        """Execute the Obsolete Game Check task returning obsolete games."""
        log.info("Scheduled - OBSOLETE_GAME_CHECK")
        obsolete = 0
        now = pendulum.now()
        retention_thresh_min = config().game_retention_thresh_min
        for (game, completed_date) in self.manager.lookup_game_completion():
            since_completed = now.diff(completed_date).in_minutes()
            if since_completed >= retention_thresh_min:
                obsolete += 1
                self.handle_game_obsolete_event(game)
        log.debug("Obsolete game check completed, found %d obsolete games", obsolete)
        return obsolete

    def handle_register_player_request(self, message: Message, websocket: WebSocketServerProtocol) -> None:
        """Handle the Register Player request."""
        context = cast(RegisterPlayerContext, message.context)
        log.info("Request - REGISTER PLAYER - %s on %s", context.handle, id(websocket))
        if self.manager.get_registered_player_count() >= config().registered_player_limit:
            raise ProcessingError(FailureReason.USER_LIMIT, handle=context.handle)
        self.handle_player_registered_event(websocket, context.handle)

    def handle_reregister_player_request(self, request: RequestContext) -> None:
        """Handle the Reregister Player request."""
        log.info("Request - REREGISTER PLAYER - %s", request.player.handle)
        self.handle_player_reregistered_event(request.player, request.websocket)

    def handle_unregister_player_request(self, request: RequestContext) -> None:
        """Handle the Unregister Player request."""
        log.info("Request - UNREGISTER PLAYER - %s", request.player.handle)
        self.handle_player_unregistered_event(request.player, request.game)

    def handle_list_players_request(self, request: RequestContext) -> None:
        """Handle the List Players request."""
        log.info("Request - LIST PLAYERS - %s", request.player.handle)
        self.handle_registered_players_event(request.player)

    def handle_advertise_game_request(self, request: RequestContext) -> None:
        """Handle the Advertise Game request."""
        log.info("Request - ADVERTISE GAME - %s", request.player.handle)
        if request.game:
            raise ProcessingError(FailureReason.ALREADY_PLAYING, handle=request.player.handle)
        if self.manager.get_total_game_count() >= config().total_game_limit:
            raise ProcessingError(FailureReason.GAME_LIMIT, handle=request.player.handle)
        context = cast(AdvertiseGameContext, request.message.context)
        self.handle_game_advertised_event(request.player, context)

    def handle_list_available_games_request(self, request: RequestContext) -> None:
        """Handle the List Available Games request."""
        log.info("Request - LIST AVAILABLE_GAMES - %s", request.player.handle)
        self.handle_available_games_event(request.player)

    def handle_join_game_request(self, request: RequestContext) -> None:
        """Handle the Join Game request."""
        context = cast(JoinGameContext, request.message.context)
        log.info("Request - JOIN GAME - %s for %s", request.player.handle, context.game_id)
        if request.game:
            raise ProcessingError(FailureReason.ALREADY_PLAYING, handle=request.player.handle)
        self.handle_game_joined_event(request.player, game_id=context.game_id)

    def handle_quit_game_request(self, request: RequestContext) -> None:
        """Handle the Quit Game request."""
        log.info("Request - QUIT GAME - %s quit %s", request.player.handle, request.player.game_id)
        if not request.game:
            raise ProcessingError(FailureReason.NOT_PLAYING, handle=request.player.handle)
        if not request.game.is_in_progress():
            raise ProcessingError(FailureReason.INVALID_GAME, comment="Game is not in progress", handle=request.player.handle)
        if request.player.handle == request.game.advertiser_handle:
            raise ProcessingError(FailureReason.ADVERTISER_MAY_NOT_QUIT, handle=request.player.handle)
        self.handle_game_player_quit_event(request.player, request.game)

    def handle_start_game_request(self, request: RequestContext) -> None:
        """Handle the Start Game request."""
        log.info("Request - START GAME - %s started %s", request.player.handle, request.player.game_id)
        if not request.game:
            raise ProcessingError(FailureReason.NOT_PLAYING, handle=request.player.handle)
        if request.game.is_playing():
            raise ProcessingError(FailureReason.INVALID_GAME, comment="Game is already being played", handle=request.player.handle)
        if request.game.advertiser_handle != request.player.handle:
            raise ProcessingError(FailureReason.NOT_ADVERTISER, handle=request.player.handle)
        if self.manager.get_in_progress_game_count() >= config().in_progress_game_limit:
            raise ProcessingError(FailureReason.GAME_LIMIT, handle=request.player.handle)
        self.handle_game_started_event(request.game)

    def handle_cancel_game_request(self, request: RequestContext) -> None:
        """Handle the Cancel Game request."""
        log.info("Request - CANCEL GAME - %s cancelled %s", request.player.handle, request.player.game_id)
        if not request.game:
            raise ProcessingError(FailureReason.NOT_PLAYING, handle=request.player.handle)
        if not request.game.is_in_progress():
            raise ProcessingError(FailureReason.INVALID_GAME, comment="Game is not in progress", handle=request.player.handle)
        if request.game.advertiser_handle != request.player.handle:
            raise ProcessingError(FailureReason.NOT_ADVERTISER, handle=request.player.handle)
        self.handle_game_cancelled_event(request.game, CancelledReason.CANCELLED)

    def handle_execute_move_request(self, request: RequestContext) -> None:
        """Handle the Execute Move request."""
        context = cast(ExecuteMoveContext, request.message.context)
        log.info("Request - EXECUTE MOVE - %s for %s, move %s", request.player.handle, request.player.game_id, context.move_id)
        if not request.game:
            raise ProcessingError(FailureReason.NOT_PLAYING, handle=request.player.handle)
        if not request.game.is_playing():
            raise ProcessingError(FailureReason.INVALID_GAME, comment="Game is not being played", handle=request.player.handle)
        if not request.game.is_move_pending(request.player.handle):
            raise ProcessingError(FailureReason.NO_MOVE_PENDING, handle=request.player.handle)
        if not request.game.is_legal_move(request.player.handle, context.move_id):
            raise ProcessingError(FailureReason.ILLEGAL_MOVE, handle=request.player.handle)
        self.handle_game_player_move_event(request.player, request.game, context.move_id)

    def handle_optimal_move_request(self, request: RequestContext) -> None:
        """Handle the Optimal Move request."""
        log.info("Request - OPTIMAL MOVE - %s for %s", request.player.handle, request.player.game_id)
        if not request.game:
            raise ProcessingError(FailureReason.NOT_PLAYING, handle=request.player.handle)
        if not request.game.is_playing():
            raise ProcessingError(FailureReason.INVALID_GAME, comment="Game is not being played", handle=request.player.handle)
        if not request.game.is_move_pending(request.player.handle):
            raise ProcessingError(FailureReason.NO_MOVE_PENDING, handle=request.player.handle)
        self.handle_game_programmatic_move_event(request.player.handle, request.game)

    def handle_retrieve_game_state_request(self, request: RequestContext) -> None:
        """Handle the Retrieve Game State request."""
        log.info("Request - RETRIEVE GAME - %s for %s", request.player.handle, request.player.game_id)
        if not request.game:
            raise ProcessingError(FailureReason.NOT_PLAYING, handle=request.player.handle)
        if not request.game.is_playing():
            raise ProcessingError(FailureReason.INVALID_GAME, comment="Game is not being played", handle=request.player.handle)
        self.handle_game_state_change_event(request.game, request.player)

    def handle_send_message_request(self, request: RequestContext) -> None:
        """Handle the Send Message request."""
        context = cast(SendMessageContext, request.message.context)
        log.info(
            "Request - SEND MESSAGE - %s sending %d bytes to %d recipients",
            request.player.handle,
            len(context.message),
            len(context.recipient_handles),
        )
        self.handle_player_message_received_event(request.player.handle, context.recipient_handles, context.message)

    def handle_server_shutdown_event(self) -> None:
        """Handle the Server Shutdown event."""
        log.info("Event - SERVER SHUTDOWN")
        websockets = self.manager.lookup_all_websockets()
        message = Message(MessageType.SERVER_SHUTDOWN)
        self.queue.message(message, websockets=websockets)
        for game in self.manager.lookup_in_progress_games():
            self.handle_game_cancelled_event(game, CancelledReason.SHUTDOWN, notify=False)

    def handle_websocket_connected_event(self, websocket: WebSocketServerProtocol) -> None:
        """Handle the Websocket Connected event."""
        log.info("Event - WEBSOCKET CONNECTED - %s", id(websocket))
        if self.manager.get_websocket_count() >= config().websocket_limit:
            raise ProcessingError(FailureReason.WEBSOCKET_LIMIT)
        self.manager.track_websocket(websocket)

    def handle_websocket_disconnected_event(self, websocket: WebSocketServerProtocol) -> None:
        """Handle the Websocket Disconnected event."""
        log.info("Event - WEBSOCKET DISCONNECTED - %s", id(websocket))
        players = self.manager.lookup_players_for_websocket(websocket)
        for player in players:
            self.handle_player_disconnected_event(player)
        self.manager.delete_websocket(websocket)

    def handle_websocket_idle_event(self, websocket: TrackedWebsocket) -> None:
        """Handle the Websocket Idle event."""
        log.info("Event - WEBSOCKET IDLE - %s", id(websocket.websocket))
        if websocket.activity_state != ActivityState.IDLE:
            message = Message(MessageType.WEBSOCKET_IDLE)
            self.queue.message(message, websockets=[websocket.websocket])
            websocket.mark_idle()

    def handle_websocket_inactive_event(self, websocket: TrackedWebsocket) -> None:
        """Handle the Websocket Inactive event."""
        log.info("Event - WEBSOCKET INACTIVE - %s", id(websocket.websocket))
        if websocket.activity_state != ActivityState.INACTIVE:
            websocket.mark_inactive()
            message = Message(MessageType.WEBSOCKET_INACTIVE)
            self.queue.message(message, websockets=[websocket.websocket])
            self.queue.disconnect(websocket.websocket)  # will eventually trigger handle_websocket_disconnected_event()

    def handle_registered_players_event(self, player: TrackedPlayer) -> None:
        """Handle the Registered Players event."""
        log.info("Event - REGISTERED PLAYERS - %s", player.handle)
        players = [player.to_registered_player() for player in self.manager.lookup_all_players()]
        context = RegisteredPlayersContext(players=players)
        message = Message(MessageType.REGISTERED_PLAYERS, context=context)
        self.queue.message(message, players=[player])

    def handle_available_games_event(self, player: TrackedPlayer) -> None:
        """Handle the Available Games event."""
        log.info("Event - AVAILABLE GAMES - %s", player.handle)
        games = [game.to_advertised_game() for game in self.manager.lookup_available_games(player)]
        context = AvailableGamesContext(games=games)
        message = Message(MessageType.AVAILABLE_GAMES, context=context)
        self.queue.message(message, players=[player])

    def handle_player_registered_event(self, websocket: WebSocketServerProtocol, handle: str) -> None:
        """Handle the Player Registered event."""
        log.info("Event - PLAYER REGISTERED - %s on %s", handle, id(websocket))
        player = self.manager.track_player(websocket, handle)
        context = PlayerRegisteredContext(handle=player.handle)
        message = Message(MessageType.PLAYER_REGISTERED, player_id=player.player_id, context=context)
        self.queue.message(message, websockets=[websocket])

    def handle_player_reregistered_event(self, player: TrackedPlayer, websocket: WebSocketServerProtocol) -> None:
        """Handle the Player Registered event."""
        log.info("Event - PLAYER REREGISTERED - %s on %s", player.handle, id(websocket))
        self.manager.retrack_player(player, websocket)
        context = PlayerRegisteredContext(handle=player.handle)
        message = Message(MessageType.PLAYER_REGISTERED, player_id=player.player_id, context=context)
        self.queue.message(message, players=[player])

    def handle_player_unregistered_event(self, player: TrackedPlayer, game: Optional[TrackedGame] = None) -> None:
        """Handle the Player Unregistered event."""
        log.info("Event - PLAYER UNREGISTERED - %s with game %s", player.handle, player.game_id)
        player.mark_quit()
        if game:
            comment = "Player %s unregistered" % player.handle
            self.handle_game_player_left_event(player, game, comment)
        context = PlayerUnregisteredContext(handle=player.handle)
        message = Message(MessageType.PLAYER_UNREGISTERED, context=context)
        self.queue.message(message, players=[player])
        self.manager.delete_player(player)

    def handle_player_disconnected_event(self, player: TrackedPlayer) -> None:
        """Handle the Player Disconnected event."""
        log.info("Event - PLAYER DISCONNECTED - %s", player.handle)
        game = self.manager.lookup_game(player=player)
        player.mark_disconnected()
        if game:
            comment = "Player %s disconnected" % player.handle
            self.handle_game_player_left_event(player, game, comment)

    def handle_player_idle_event(self, player: TrackedPlayer) -> None:
        """Handle the Player Idle event."""
        log.info("Event - PLAYER IDLE - %s", player.handle)
        if player.activity_state != ActivityState.IDLE:
            context = PlayerIdleContext(handle=player.handle)
            message = Message(MessageType.PLAYER_IDLE, context=context)
            self.queue.message(message, players=[player])
            player.mark_idle()

    def handle_player_inactive_event(self, player: TrackedPlayer) -> None:
        """Handle the Player Inactive event."""
        # Note that we do not disconnect the websocket, because it might still be in use by other players.
        # If this is the last registered player using the websocket, it will also eventually be marked inactive, and be closed then.
        log.info("Event - PLAYER INACTIVE - %s", player.handle)
        if player.activity_state != ActivityState.INACTIVE:
            player.mark_inactive()
            context = PlayerInactiveContext(handle=player.handle)
            message = Message(MessageType.PLAYER_INACTIVE, context=context)
            game = self.manager.lookup_game(player=player)
            self.queue.message(message, players=[player])
            self.handle_player_unregistered_event(player, game)

    def handle_player_message_received_event(self, sender_handle: str, recipient_handles: List[str], sender_message: str) -> None:
        """Handle the Player Message Received event."""
        log.info(
            "Event - PLAYER MESSAGE RECEIVED - %s sending %d bytes to %d recipients",
            sender_handle,
            len(sender_message),
            len(recipient_handles),
        )
        context = PlayerMessageReceivedContext(sender_handle, recipient_handles, sender_message)
        message = Message(MessageType.PLAYER_MESSAGE_RECEIVED, context=context)
        players = [self.manager.lookup_player(handle=handle) for handle in recipient_handles]
        self.queue.message(message, players=[player for player in players if player])

    def handle_game_advertised_event(self, player: TrackedPlayer, advertised: AdvertiseGameContext) -> None:
        """Handle the Game Advertised event."""
        log.info("Event - GAME ADVERTISED - %s", player.handle)
        game = self.manager.track_game(player, advertised)
        self.handle_game_joined_event(player, game=game)
        self.handle_game_invitation_event(game)
        context = GameAdvertisedContext(game=game.to_advertised_game())  # get result here so it shows advertiser as joined
        message = Message(MessageType.GAME_ADVERTISED, context=context)
        self.queue.message(message, players=[player])

    def handle_game_invitation_event(self, game: TrackedGame) -> None:
        """Handle the Game Invitation event."""
        log.info("Event - GAME INVITATION - %s", game.game_id)
        if game.invited_handles:
            context = GameInvitationContext(game=game.to_advertised_game())
            message = Message(MessageType.GAME_INVITATION, context=context)
            players = [self.manager.lookup_player(handle=handle) for handle in game.invited_handles]
            self.queue.message(message, players=[player for player in players if player])

    def handle_game_joined_event(
        self, player: TrackedPlayer, game_id: Optional[str] = None, game: Optional[TrackedGame] = None
    ) -> None:
        """Handle the Game Joined event."""
        log.info("Event - GAME JOINED - %s", game_id if game_id else game.game_id if game else None)
        if game_id:
            game = self.manager.lookup_game(game_id=game_id)
            if not game or not game.is_available(player.handle):
                raise ProcessingError(FailureReason.INVALID_GAME, handle=player.handle)
        if not game:
            raise ProcessingError(FailureReason.INTERNAL_ERROR, comment="Invalid arguments", handle=player.handle)
        game.mark_active()
        player.mark_joined(game)
        game.mark_joined(player.handle)
        context = GameJoinedContext(
            player_handle=player.handle,
            game_id=game.game_id,
            name=game.name,
            mode=game.mode,
            advertiser_handle=game.advertiser_handle,
        )
        message = Message(MessageType.GAME_JOINED, context=context)
        self.queue.message(message, players=[player])
        self.handle_game_player_change_event(game, "Player joined game")
        if game.is_fully_joined():
            if self.manager.get_in_progress_game_count() >= config().in_progress_game_limit:
                # Rather than giving the caller an error, we just ignore the game and force the
                # advertiser to manually start it sometime later.  At least then, if the limit
                # has still been reached, the player receiving the error will be able to make
                # sense of it.  It doesn't seem right to fail the join operation (which has
                # completed successfully by this point) because the game can't be started.
                log.warning("Game limit reached, so game %s will not be auto-started", game.game_id)
            else:
                self.handle_game_started_event(game)

    def handle_game_started_event(self, game: TrackedGame) -> None:
        """Handle the Game Started event."""
        log.info("Event - GAME STARTED - %s", game.game_id)
        context = GameStartedContext(game_id=game.game_id)
        message = Message(MessageType.GAME_STARTED, context=context)
        game.mark_active()
        game.mark_started()
        players = self.manager.lookup_game_players(game)
        for player in players:
            player.mark_playing()
        self.queue.message(message, players=players)
        self.handle_game_player_change_event(game, "Game started")
        self.handle_game_state_change_event(game)
        self.handle_game_next_turn_event(game)

    def handle_game_cancelled_event(
        self, game: TrackedGame, reason: CancelledReason, comment: Optional[str] = None, notify: bool = True
    ) -> None:
        """Handle the Game Cancelled event."""
        log.info("Event - GAME CANCELLED - %s for %s (%s)", game.game_id, reason, "'%s'" % comment if comment else None)
        context = GameCancelledContext(game_id=game.game_id, reason=reason, comment=comment)
        message = Message(MessageType.GAME_CANCELLED, context=context)
        players = self.manager.lookup_game_players(game)
        for player in players:
            player.mark_quit()
        game.mark_cancelled(reason, comment)
        if notify:
            self.queue.message(message, players=players)
            self.handle_game_state_change_event(game)

    def handle_game_completed_event(self, game: TrackedGame, winner: str, comment: str) -> None:
        """Handle the Game Completed event."""
        log.info("Event - GAME COMPLETED - %s (%s)", game.game_id, "'%s'" % comment if comment else None)
        context = GameCompletedContext(game_id=game.game_id, winner=winner, comment=comment)
        message = Message(MessageType.GAME_COMPLETED, context=context)
        players = self.manager.lookup_game_players(game)
        for player in players:
            player.mark_quit()
        game.mark_completed(comment)
        self.queue.message(message, players=players)
        self.handle_game_state_change_event(game)

    def handle_game_idle_event(self, game: TrackedGame) -> None:
        """Handle the Game Idle event."""
        log.info("Event - GAME IDLE - %s", game.game_id)
        if game.activity_state != ActivityState.IDLE:
            context = GameIdleContext(game_id=game.game_id)
            message = Message(MessageType.GAME_IDLE, context=context)
            players = self.manager.lookup_game_players(game)
            self.queue.message(message, players=players)

    def handle_game_inactive_event(self, game: TrackedGame) -> None:
        """Handle the Game Inactive event."""
        log.info("Event - GAME INACTIVE - %s", game.game_id)
        if game.activity_state != ActivityState.INACTIVE:
            game.mark_inactive()
            context = GameInactiveContext(game_id=game.game_id)
            message = Message(MessageType.GAME_INACTIVE, context=context)
            players = self.manager.lookup_game_players(game)
            self.queue.message(message, players=players)
            self.handle_game_cancelled_event(game, CancelledReason.INACTIVE)

    def handle_game_obsolete_event(self, game: TrackedGame) -> None:
        """Handle the Game Obsolete event."""
        log.info("Event - GAME OBSOLETE - %s", game.game_id)
        self.manager.delete_game(game)

    def handle_game_player_quit_event(self, player: TrackedPlayer, game: TrackedGame) -> None:
        """Handle the Game Player Quit event."""
        log.info("Event - GAME PLAYER QUIT - %s quit %s", player.handle, game.game_id)
        game.mark_active()
        player.mark_quit()
        context = GamePlayerQuitContext(handle=player.handle, game_id=game.game_id)
        message = Message(MessageType.GAME_PLAYER_QUIT, context=context)
        self.queue.message(message, players=[player])
        comment = "Player %s quit" % player.handle
        self.handle_game_player_left_event(player, game, comment)

    def handle_game_player_left_event(self, player: TrackedPlayer, game: TrackedGame, comment: str) -> None:
        """Handle the Game Player Left event."""
        log.info("Event - GAME PLAYER LEFT - %s left %s ('%s')", player.handle, game.game_id, comment)
        if player.handle == game.advertiser_handle:
            self.handle_game_cancelled_event(game, CancelledReason.CANCELLED, comment)
        else:
            game.mark_quit(player.handle)
            self.handle_game_player_change_event(game, comment)
            if not game.is_viable():
                self.handle_game_cancelled_event(game, CancelledReason.NOT_VIABLE, comment)
            elif game.is_playing() and game.is_move_pending(player.handle):
                # if the player is in the middle of their turn when they leave, we need to finish it for them
                self.handle_game_programmatic_move_event(player.handle, game)

    def handle_game_player_move_event(self, player: TrackedPlayer, game: TrackedGame, move_id: str) -> None:
        """Handle the Game Player Move event."""
        log.info("Event - GAME PLAYER MOVE - %s for %s, move %s", player.handle, game.game_id, move_id)
        self.handle_game_move_event(player.handle, game, move_id)

    def handle_game_programmatic_move_event(self, handle: str, game: TrackedGame) -> None:
        """Handle the Game Programmatic Move event."""
        log.info("Event - GAME PROGRAMMATIC MOVE - %s for %s", handle, game.game_id)
        view = game.get_player_view(handle)
        moves = game.get_legal_moves(handle)
        move = RewardV1InputSource().choose_move(game.mode, view, moves, Rules.evaluate_move)
        self.handle_game_move_event(handle, game, move.id)

    def handle_game_move_event(self, handle: str, game: TrackedGame, move_id: str) -> None:
        """Handle the Game Move event."""
        log.info("Event - GAME MOVE - %s for %s, move %s", handle, game.game_id, move_id)
        game.mark_active()
        (completed, winner, comment) = game.execute_move(handle, move_id)
        self.handle_game_state_change_event(game)
        if completed:
            self.handle_game_completed_event(game, winner, comment)  # type: ignore
        else:
            self.handle_game_next_turn_event(game)

    def handle_game_next_turn_event(self, game: TrackedGame) -> None:
        """Handle the Game Next Turn event."""
        log.info("Event - GAME NEXT TURN - %s", game.game_id)
        handle, player_type = game.get_next_turn()
        if player_type == PlayerType.PROGRAMMATIC:
            self.handle_game_programmatic_move_event(handle, game)
        else:
            player = self.manager.lookup_player(handle=handle)
            if player and player.player_state == PlayerState.PLAYING:  # they might have quit or even have unregistered
                moves = game.get_legal_moves(handle)
                self.handle_game_player_turn_event(player, moves)
            else:
                # if the player is no longer available to play, then we execute a move programmatically
                self.handle_game_programmatic_move_event(handle, game)

    def handle_game_player_change_event(self, game: TrackedGame, comment: str) -> None:
        """Handle the Game Player Change event."""
        log.info("Event - GAME PLAYER CHANGE - %s (%s)", game.game_id, "'%s'" % comment if comment else None)
        players = self.manager.lookup_game_players(game)
        context = GamePlayerChangeContext(game_id=game.game_id, comment=comment, players=game.get_game_players())
        message = Message(MessageType.GAME_PLAYER_CHANGE, context=context)
        self.queue.message(message, players=players)

    # pylint: disable=redefined-argument-from-local
    def handle_game_state_change_event(self, game: TrackedGame, player: Optional[TrackedPlayer] = None) -> None:
        """Handle the Game State Change event."""
        log.info("Event - GAME STATE CHANGE - %s for %s", game.game_id, player.handle if player else None)
        game.mark_active()
        if game.is_playing():
            players = [player] if player else self.manager.lookup_game_players(game)
            for player in players:
                view = game.get_player_view(player.handle)
                history = game.get_recent_history(10)  # the last 10 entries in history
                context = GameStateChangeContext.for_context(game_id=game.game_id, view=view, history=history)
                message = Message(MessageType.GAME_STATE_CHANGE, context=context)
                self.queue.message(message, players=[player])

    def handle_game_player_turn_event(self, player: TrackedPlayer, moves: List[Move]) -> None:
        """Handle the Game Player Turn event."""
        log.info("Event - GAME PLAYER TURN - %s for %s (%d moves)", player.handle, player.game_id, len(moves))
        context = GamePlayerTurnContext.for_moves(handle=player.handle, game_id=player.game_id, moves=moves)  # type: ignore
        message = Message(MessageType.GAME_PLAYER_TURN, context=context)
        self.queue.message(message, players=[player])
