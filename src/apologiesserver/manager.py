# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import,too-many-lines

# TODO: what to do with too-many-lines?  Split this up somehow?  Maybe event and request stuff can eventually split back out?
# TODO: this needs unit tests, but probably after the other code is done
# TODO: this does not actually include any way to manage game state or engine yet (that's the next big design step)

"""
State manager.

Python's asyncio is primarily meant for use in single-threaded code, but there is still
concurrent execution happening any time we hit a yield from or await.

We want to minimize the risk of unexpected behavior when there are conflicting requests.
For instance, if we simultaneously get a request to start a game and to quit a game, we
want to make sure that one operation completes entirely before the next one starts.  This
means that we need thread synchronization whenever state is updated.

I've chosen to synchronize all state upate operations behind a single transaction boundary
(a single lock).  This is easier to follow and easier to write (correctly) than tracking
individual locks at a more granular level, like at the player or the game level.  The
state will never be locked for all that long, because state update operations are all done
in-memory and are quite fast.  The slow stuff like network requests all happen outside the
lock, whether we're processing a request or executing a scheduled task.

The design would be different if we were using a database to save state, but this seems
like the best compromise for the simple in-memory design that we're using now.

None of the objects defined in this module are thread-safe, or even thread-aware.  There
are no asynchronous methods or await calls.  Instead, the transaction boundary is handled
at the level of the module.  This simplifies the implementation and avoids confusion.
"""

from __future__ import annotations  # see: https://stackoverflow.com/a/33533514/2907667

import asyncio
import logging
import random
from typing import Dict, List, Optional, Tuple, cast
from uuid import uuid4

import attr
import pendulum
from apologies.game import GameMode, Player, PlayerColor, PlayerView
from apologies.rules import Move
from pendulum.datetime import DateTime
from websockets import WebSocketServerProtocol

from .interface import *

log = logging.getLogger("apologies.manager")


# These are names we can assign to programmatic players.
_NAMES = [
    "Aragorn",
    "Arwen",
    "Bilbo",
    "Boromir",
    "Elrond",
    "Éomer",
    "Éowyn",
    "Faramir",
    "Frodo",
    "Galadriel",
    "Gandalf",
    "Gimli",
    "Gollum",
    "Isildur",
    "Legolas",
    "Merry",
    "Pippen",
    "Radagast",
    "Samwise",
    "Saruman",
    "Sauron",
    "Shelob",
    "Théoden",
    "Treebeard",
]


@attr.s
class MessageQueue:

    """A queue of messages to be sent."""

    messages = attr.ib(type=List[Tuple[Message, WebSocketServerProtocol]])

    @messages.default
    def _messages_default(self) -> List[Tuple[Message, WebSocketServerProtocol]]:
        return []

    def add(
        self,
        message: Message,
        websockets: Optional[List[WebSocketServerProtocol]] = None,
        players: Optional[List[TrackedPlayer]] = None,
    ) -> None:
        """Enqueue a message to one or more destination websockets."""
        destinations = set(websockets) if websockets else set()
        destinations.update([player.websocket for player in players if player.websocket] if players else [])
        self.messages.extend([(message, destination) for destination in destinations])

    async def send(self) -> None:
        """Send all messages in the queue."""
        await asyncio.wait([websocket.send(message.to_json()) for message, websocket in self.messages])


# pylint: disable=too-many-instance-attributes
@attr.s
class TrackedPlayer:
    """The state that is tracked for a player within the state manager."""

    player_id = attr.ib(type=str, repr=False)  # treat as read-only; this is a secret, so we don't want it printed or logged
    handle = attr.ib(type=str)  # treat as read-only
    websocket = attr.ib(type=Optional[WebSocketServerProtocol])
    registration_date = attr.ib(type=DateTime)
    last_active_date = attr.ib(type=DateTime)
    activity_state = attr.ib(type=ActivityState, default=ActivityState.ACTIVE)
    connection_state = attr.ib(type=ConnectionState, default=ConnectionState.CONNECTED)
    player_state = attr.ib(type=PlayerState, default=PlayerState.WAITING)
    game_id = attr.ib(type=Optional[str], default=None)

    @registration_date.default
    def _default_registration_date(self) -> DateTime:
        return pendulum.now()

    @last_active_date.default
    def _default_last_active_date(self) -> DateTime:
        return pendulum.now()

    @staticmethod
    def for_context(player_id: str, websocket: WebSocketServerProtocol, handle: str) -> TrackedPlayer:
        """Create a tracked player based on provided context."""
        return TrackedPlayer(player_id=player_id, websocket=websocket, handle=handle)

    def to_registered_player(self) -> RegisteredPlayer:
        """Convert this TrackedPlayer to a RegisteredPlayer."""
        return RegisteredPlayer(
            handle=self.handle,
            registration_date=self.registration_date,
            last_active_date=self.last_active_date,
            connection_state=self.connection_state,
            activity_state=self.activity_state,
            player_state=self.player_state,
            game_id=self.game_id,
        )

    def is_connected(self) -> bool:
        """Whether the player is connected."""
        return self.connection_state == ConnectionState.CONNECTED

    async def disconnect(self) -> None:
        if self.websocket:
            try:
                await self.websocket.close()
            except:  # pylint: disable=bare-except
                pass
        self.mark_disconnected()

    def mark_active(self) -> None:
        """Mark the player as active."""
        self.last_active_date = pendulum.now()
        self.activity_state = ActivityState.ACTIVE
        self.connection_state = ConnectionState.CONNECTED

    def mark_idle(self) -> None:
        """Mark the player as idle."""
        self.activity_state = ActivityState.IDLE

    def mark_inactive(self) -> None:
        """Mark the player as inactive."""
        self.activity_state = ActivityState.INACTIVE

    def mark_joined(self, game: TrackedGame) -> None:
        """Mark that the player has joined a game."""
        self.game_id = game.game_id
        self.player_state = PlayerState.JOINED

    def mark_playing(self) -> None:
        """Mark that the player is playing a game."""
        self.player_state = PlayerState.PLAYING

    def mark_quit(self) -> None:
        """Mark that the player has quit a game."""
        self.game_id = None
        self.player_state = PlayerState.WAITING  # they go right through QUIT and back to WAITING

    def mark_disconnected(self) -> None:
        """Mark the player as disconnected."""
        self.mark_quit()
        self.websocket = None
        self.activity_state = ActivityState.IDLE
        self.connection_state = ConnectionState.DISCONNECTED


# pylint: disable=too-many-instance-attributes,too-many-public-methods
@attr.s
class TrackedGame:
    """The state that is tracked for a game within the state manager."""

    game_id = attr.ib(type=str)  # treat as read-only
    advertiser_handle = attr.ib(type=str)  # treat as read-only
    name = attr.ib(type=str)  # treat as read-only
    mode = attr.ib(type=GameMode)  # treat as read-only
    players = attr.ib(type=int)  # treat as read-only
    visibility = attr.ib(type=Visibility)  # treat as read-only
    invited_handles = attr.ib(type=List[str])  # treat as read-only
    advertised_date = attr.ib(type=DateTime)
    last_active_date = attr.ib(type=DateTime)
    started_date = attr.ib(type=Optional[DateTime], default=None)
    completed_date = attr.ib(type=Optional[DateTime], default=None)
    game_state = attr.ib(type=GameState, default=GameState.ADVERTISED)
    activity_state = attr.ib(type=ActivityState, default=ActivityState.ACTIVE)
    cancelled_reason = attr.ib(type=Optional[CancelledReason], default=None)
    completed_comment = attr.ib(type=Optional[str], default=None)
    game_players = attr.ib(type=Dict[str, GamePlayer])

    @advertised_date.default
    def _default_advertised_date(self) -> DateTime:
        return pendulum.now()

    @last_active_date.default
    def _default_last_active_date(self) -> DateTime:
        return pendulum.now()

    @game_players.default
    def _default_game_players(self) -> List[GamePlayer]:
        return []

    @staticmethod
    def for_context(advertiser_handle: str, game_id: str, context: AdvertiseGameContext) -> TrackedGame:
        """Create a tracked game based on provided context."""
        return TrackedGame(
            game_id=game_id,
            advertiser_handle=advertiser_handle,
            name=context.name,
            mode=context.mode,
            players=context.players,
            visibility=context.visibility,
            invited_handles=context.invited_handles[:],
        )

    def to_advertised_game(self) -> AdvertisedGame:
        """Convert this tracked game to an AdvertisedGame."""
        return AdvertisedGame(
            game_id=self.game_id,
            name=self.name,
            mode=self.mode,
            advertiser_handle=self.advertiser_handle,
            players=self.players,
            available=self.players - len(self.game_players),
            visibility=self.visibility,
            invited_handles=self.invited_handles[:],
        )

    def get_game_players(self) -> List[GamePlayer]:
        """Get a list of game players."""
        return list(self.game_players.values())

    def is_available(self, player: TrackedPlayer) -> bool:
        """Whether the game is available to be joined by the passed-in player."""
        return self.game_state == GameState.ADVERTISED and (
            self.visibility == Visibility.PUBLIC or player.handle in self.invited_handles
        )

    def is_in_progress(self) -> bool:
        """Whether a game is in-progress, meaning it is advertised or being played."""
        return self.is_advertised() or self.is_playing()

    def is_advertised(self) -> bool:
        """Whether a game is currently being advertised."""
        return self.game_state == GameState.ADVERTISED

    def is_playing(self) -> bool:
        """Whether a game is being played."""
        return self.game_state == GameState.PLAYING

    # TODO: this needs to take into account game state
    #       if the game has not been started, a player leaving does not impact viability
    #       if the game has not been started, if the advertising player leaves, that cancels the game
    def is_viable(self) -> bool:
        """Whether the game is viable."""
        available = len([player for player in self.game_players.values() if player.is_available()])
        return self.players - available > 2  # game is only viable if at least 2 players remain to play turns

    def is_fully_joined(self) -> bool:
        """Whether the number of requested players have joined the game."""
        return self.players == len(self.game_players)

    # TODO: remove unused-argument when method is implemented
    # pylint: disable=unused-argument
    def is_move_pending(self, handle: str) -> bool:
        """Whether a move is pending for the player with the passed-in handle."""
        # TODO: implement is_move_pending() - if we are waiting for the player and the game is not completed or cancelled
        return True

    # TODO: remove unused-argument when method is implemented
    # pylint: disable=unused-argument
    def is_legal_move(self, handle: str, move_id: str) -> bool:
        """Whether the passed-in move id is a legal move for the player."""
        # TODO: implement is_legal_move() - this is actually a superset of is_move_pending() but is separate for clarity
        return True

    def mark_active(self) -> None:
        """Mark the game as active."""
        self.last_active_date = pendulum.now()
        self.activity_state = ActivityState.ACTIVE

    def mark_idle(self) -> None:
        """Mark the game as idle."""
        self.activity_state = ActivityState.IDLE

    def mark_inactive(self) -> None:
        """Mark the game as inactive."""
        self.activity_state = ActivityState.INACTIVE

    def mark_started(self) -> None:
        """Mark the game as started."""
        self.game_state = GameState.PLAYING
        self.last_active_date = pendulum.now()
        self.started_date = pendulum.now()
        for _ in range(0, self.players - len(self.game_players)):
            self._mark_joined_programmatic()  # fill in remaining players as necessary
        for handle in self.game_players:
            self.game_players[handle] = attr.evolve(self.game_players[handle], state=PlayerState.PLAYING)

    def mark_completed(self, comment: Optional[str]) -> None:
        """Mark the game as completed."""
        self.completed_date = pendulum.now()
        self.game_state = GameState.COMPLETED
        self.completed_comment = comment
        for handle in self.game_players:
            self.game_players[handle] = attr.evolve(self.game_players[handle], state=PlayerState.FINISHED)

    def mark_cancelled(self, reason: CancelledReason, comment: Optional[str] = None) -> None:
        """Mark the game as cancelled."""
        self.completed_date = pendulum.now()
        self.game_state = GameState.CANCELLED
        self.cancelled_reason = reason
        self.completed_comment = comment
        for handle in self.game_players:
            self.game_players[handle] = attr.evolve(self.game_players[handle], state=PlayerState.FINISHED)

    def mark_joined(self, player: TrackedPlayer) -> None:
        """Mark that a player has joined a game."""
        player_type = PlayerType.HUMAN
        player_state = PlayerState.JOINED
        player_color = self._assign_color()
        self.game_players[player.handle] = GamePlayer(player.handle, player_color, player_type, player_state)

    def mark_quit(self, player: TrackedPlayer) -> None:
        """Mark that the player has quit a game."""
        if self.game_state == GameState.ADVERTISED:
            del self.game_players[player.handle]  # if the game hasn't started, just remove them
        else:
            self.game_players[player.handle] = attr.evolve(self.game_players[player.handle], state=PlayerState.QUIT)

    # pylint: disable=unused-argument
    def get_player_view(self, player: TrackedPlayer) -> PlayerView:
        """Get the player's view of the game state."""
        # TODO: remove pylint unused-argument once this is implemented
        # TODO: implement get_player_view() once we have a way to manage game state (within a lock, presumably)
        return PlayerView(player=Player(PlayerColor.RED, [], []), opponents={})

    # pylint: disable=unused-argument
    def execute_move(self, player: TrackedPlayer, move_id: str) -> Tuple[bool, Optional[str]]:
        """Execute a player's move, returning an indication of whether the game was completed (and a comment if so)."""
        # TODO: remove pylint unused-argument once this is implemented
        # TODO: implement execute_move() once we have a way to manage game state (within a lock, presumably)
        return False, None

    def _mark_joined_programmatic(self) -> None:
        """Create an join a programmatic player, assumed to be called from within a lock."""
        handle = self._assign_handle()
        player_color = self._assign_color()
        player_type = PlayerType.PROGRAMMATIC
        player_state = PlayerState.JOINED
        self.game_players[handle] = GamePlayer(handle, player_color, player_type, player_state)

    def _assign_color(self) -> PlayerColor:
        """Randomly assign a color to a newly-joined player. assumed to be called from within a lock."""
        all_colors = set(list(PlayerColor)[: self.players])
        used_colors = {player.player_color for player in self.game_players.values()}
        available_colors = all_colors - used_colors
        return random.choice(list(available_colors))

    def _assign_handle(self) -> str:
        """Assign a handle to the newly-joined programmatic player, assumed to be called from within a lock."""
        all_handles = set(_NAMES)
        used_handles = {player.handle for player in self.game_players.values()}
        available_handles = all_handles - used_handles
        return random.choice(list(available_handles))


@attr.s(frozen=True)
class RequestContext:
    """Context provided to a request handler when dispatching a message."""

    message = attr.ib(type=Message)
    websocket = attr.ib(type=WebSocketServerProtocol)
    player = attr.ib(type=TrackedPlayer)
    game = attr.ib(type=Optional[TrackedGame], default=None)
    queue = attr.ib(type=MessageQueue)

    @queue.default
    def _queue_default(self) -> MessageQueue:
        return MessageQueue()


# TODO: remove pylint stuff once implemented
# pylint: disable=unused-argument
# noinspection PyMethodMayBeStatic
@attr.s
class StateManager:

    """Manages system state."""

    _game_map = attr.ib(type=Dict[str, TrackedGame])
    _player_map = attr.ib(type=Dict[str, TrackedPlayer])
    _handle_map = attr.ib(type=Dict[str, str])

    @_game_map.default
    def _default_game_map(self) -> Dict[str, TrackedGame]:
        return {}

    @_player_map.default
    def _default_player_map(self) -> Dict[str, TrackedPlayer]:
        return {}

    @_handle_map.default
    def _default_handle_map(self) -> Dict[str, str]:
        return {}

    def handle_shutdown(self) -> MessageQueue:
        """Handle system shutdown."""
        queue = MessageQueue()
        self._handle_server_shutdown_event(queue)
        return queue

    def handle_idle_players(self, idle_thresh_min: int, inactive_thresh_min: int) -> MessageQueue:
        """Handle idle players."""
        queue = MessageQueue()
        self._handle_idle_player_check_task(queue, idle_thresh_min, inactive_thresh_min)
        return queue

    def handle_idle_games(self, idle_thresh_min: int, inactive_thresh_min: int) -> MessageQueue:
        """Handle idle games."""
        queue = MessageQueue()
        self._handle_idle_game_check_task(queue, idle_thresh_min, inactive_thresh_min)
        return queue

    def handle_obsolete_games(self, retention_thresh_min: int) -> MessageQueue:
        """Handle obsolete games."""
        queue = MessageQueue()
        self._handle_obsolete_game_check_task(queue, retention_thresh_min)
        return queue

    def handle_register(self, message: Message, websocket: WebSocketServerProtocol) -> MessageQueue:
        """Handle a REGISTER_PLAYER message received on a websocket."""
        queue = MessageQueue()
        self._handle_register_player_request(queue, message, websocket)
        return queue

    def handle_disconnect(self, websocket: WebSocketServerProtocol) -> MessageQueue:
        """Handle a disconnected websocket."""
        queue = MessageQueue()
        self._handle_player_disconnected_event(queue, websocket)
        return queue

    def handle_message(self, player_id: str, message: Message, websocket: WebSocketServerProtocol) -> MessageQueue:
        """Handle a message received on a websocket."""
        player = self.lookup_player(player_id=player_id)
        if not player:
            raise ProcessingError(FailureReason.INVALID_PLAYER)
        log.debug("Request is for player: %s", player)
        player.mark_active()
        game = self.lookup_game(game_id=player.game_id)
        request = RequestContext(message, websocket, player, game)
        self._dispatch_request(request)
        return request.queue

    def lookup_game(self, game_id: Optional[str] = None, player: Optional[TrackedPlayer] = None) -> Optional[TrackedGame]:
        """Look up a game by id, returning None if the game is not found."""
        if game_id:
            return self._game_map[game_id] if game_id in self._game_map else None
        elif player:
            return self.lookup_game(game_id=player.game_id)
        else:
            return None

    def lookup_player(self, player_id: Optional[str] = None, handle: Optional[str] = None) -> Optional[TrackedPlayer]:
        """Look up a player by either player id or handle."""
        if player_id:
            return self._player_map[player_id] if player_id in self._player_map else None
        elif handle:
            player_id = self._handle_map[handle] if handle in self._handle_map else None
            return self.lookup_player(player_id=player_id)
        else:
            return None

    # TODO: requirements for this function come from the Advertise Game request
    # TODO: decide whether I need to validate arguments (min/max players, etc.) or interface validation is enough
    def _track_game(self, player: TrackedPlayer, advertised: AdvertiseGameContext) -> TrackedGame:
        """Track a newly-advertised game, returning the tracked game."""
        game_id = "%s" % uuid4()
        self._game_map[game_id] = TrackedGame.for_context(player.handle, game_id, advertised)
        return self._game_map[game_id]

    def _delete_game(self, game: TrackedGame) -> None:
        """Delete a tracked game, so it is no longer tracked."""
        if game.game_id in self._game_map:
            del self._game_map[game.game_id]

    def _lookup_all_games(self) -> List[TrackedGame]:
        """Return a list of all tracked games."""
        return list(self._game_map.values())

    def _lookup_in_progress_games(self) -> List[TrackedGame]:
        """Return a list of all in-progress games."""
        return [game for game in self._lookup_all_games() if game.is_in_progress()]

    def _lookup_game_players(self, game: TrackedGame) -> List[TrackedPlayer]:
        """Lookup the players that are currently playing a game."""
        handles = [player.handle for player in game.game_players.values() if player.player_type == PlayerType.HUMAN]
        players = [self.lookup_player(handle=handle) for handle in handles]
        return [player for player in players if player is not None]

    # TODO: requirements for this function come from the List Available Games request and the Available Games event
    # TODO: I don't think we implement everything yet (i.e. should only show games that haven't been started, etc.)
    def _lookup_available_games(self, player: TrackedPlayer) -> List[TrackedGame]:
        """Return a list of games the passed-in player may join."""
        games = self._lookup_all_games()
        return [game for game in games if game.is_available(player)]

    # TODO: requirements for this function come from the Register Player request
    def _track_player(self, websocket: WebSocketServerProtocol, handle: str) -> TrackedPlayer:
        """Track a newly-registered player, the tracked player."""
        if handle in self._handle_map:
            raise ProcessingError(FailureReason.DUPLICATE_USER)
        player_id = "%s" % uuid4()
        self._player_map[player_id] = TrackedPlayer.for_context(player_id, websocket, handle)
        self._handle_map[handle] = player_id
        return self._player_map[player_id]

    def _delete_player(self, player: TrackedPlayer) -> None:
        """Delete a tracked player, so it is no longer tracked."""
        if player.handle in self._handle_map:
            del self._handle_map[player.handle]
        if player.player_id in self._player_map:
            del self._player_map[player.player_id]

    def _lookup_all_players(self) -> List[TrackedPlayer]:
        """Return a list of all tracked players."""
        return list(self._player_map.values())

    def _lookup_websocket(
        self, player: Optional[TrackedPlayer] = None, player_id: Optional[str] = None, handle: Optional[str] = None
    ) -> Optional[WebSocketServerProtocol]:
        """Look up the websocket for a player, player id or handle, returning None for an unknown or disconnected player."""
        if player:
            return player.websocket
        elif player_id:
            player = self.lookup_player(player_id=player_id)
            return player.websocket if player else None
        elif handle:
            player = self.lookup_player(handle=handle)
            return player.websocket if player else None
        else:
            return None

    def _lookup_websockets(
        self, players: Optional[List[TrackedPlayer]], player_ids: Optional[List[str]] = None, handles: Optional[List[str]] = None
    ) -> List[WebSocketServerProtocol]:
        """Look up the websockets for a list of players, player ids and/or handles, for players that are connected."""
        websockets = set()
        if players:
            websockets.update([self._lookup_websocket(player=player) for player in players])
        if player_ids:
            websockets.update([self._lookup_websocket(player_id=player_id) for player_id in player_ids])
        if handles:
            websockets.update([self._lookup_websocket(handle=handle) for handle in handles])
        return list([websocket for websocket in websockets if websocket is not None])

    def _lookup_all_websockets(self) -> List[WebSocketServerProtocol]:
        """Return a list of websockets for all tracked players."""
        return self._lookup_websockets(players=self._lookup_all_players())

    def _lookup_player_for_websocket(self, websocket: WebSocketServerProtocol) -> Optional[TrackedPlayer]:
        """Look up the player associated with a websocket, if any."""
        # We can't track this in a map because it's not a constant identifying aspect of a player
        for player in self._lookup_all_players():
            if websocket is self._lookup_websocket(player=player):
                return player
        return None

    def _lookup_player_activity(self) -> List[Tuple[TrackedPlayer, DateTime, ConnectionState]]:
        """Look up the last active date and connection state for all players."""
        result: List[Tuple[TrackedPlayer, DateTime, ConnectionState]] = []
        for player in self._lookup_all_players():
            result.append((player, player.last_active_date, player.connection_state))
        return result

    def _lookup_game_activity(self) -> List[Tuple[TrackedGame, DateTime]]:
        """Look up the last active date for all games."""
        result: List[Tuple[TrackedGame, DateTime]] = []
        for game in self._lookup_all_games():
            result.append((game, game.last_active_date))
        return result

    def _lookup_game_completion(self) -> List[Tuple[TrackedGame, Optional[DateTime]]]:
        """Look up the completed date for all completed games."""
        result: List[Tuple[TrackedGame, Optional[DateTime]]] = []
        for game in self._lookup_all_games():
            if game.game_state == GameState.COMPLETED:
                result.append((game, game.completed_date))
        return result

    # pylint: disable=too-many-branches
    def _dispatch_request(self, request: RequestContext) -> None:
        """Dispatch a request to the proper handler method based on message type."""
        if request.message.message == MessageType.REREGISTER_PLAYER:
            self._handle_reregister_player_request(request)
        elif request.message.message == MessageType.UNREGISTER_PLAYER:
            self._handle_unregister_player_request(request)
        elif request.message.message == MessageType.LIST_PLAYERS:
            self._handle_list_players_request(request)
        elif request.message.message == MessageType.ADVERTISE_GAME:
            self._handle_advertise_game_request(request)
        elif request.message.message == MessageType.LIST_AVAILABLE_GAMES:
            self._handle_list_available_games_request(request)
        elif request.message.message == MessageType.JOIN_GAME:
            self._handle_join_game_request(request)
        elif request.message.message == MessageType.QUIT_GAME:
            self._handle_quit_game_request(request)
        elif request.message.message == MessageType.START_GAME:
            self._handle_start_game_request(request)
        elif request.message.message == MessageType.CANCEL_GAME:
            self._handle_cancel_game_request(request)
        elif request.message.message == MessageType.EXECUTE_MOVE:
            self._handle_execute_move_request(request)
        elif request.message.message == MessageType.RETRIEVE_GAME_STATE:
            self._handle_retrieve_game_state_request(request)
        elif request.message.message == MessageType.SEND_MESSAGE:
            self._handle_send_message_request(request)
        else:
            raise ProcessingError(FailureReason.INTERNAL_ERROR, "Unknown message type %s" % request.message.message)

    def _handle_register_player_request(self, queue: MessageQueue, message: Message, websocket: WebSocketServerProtocol) -> None:
        """Handle the Rgister Player request."""
        log.info("REQUEST[Register Player]")
        context = cast(RegisterPlayerContext, message.context)
        self._handle_player_registered_event(queue, websocket, context.handle)

    def _handle_reregister_player_request(self, request: RequestContext) -> None:
        """Handle the Reregister Player request."""
        log.info("REQUEST[Reregister Player]")
        self._handle_player_reregistered_event(request.queue, request.player, request.websocket)

    def _handle_unregister_player_request(self, request: RequestContext) -> None:
        """Handle the Unregister Player request."""
        log.info("REQUEST[Unregister Player]")
        self._handle_player_unregistered_event(request.queue, request.player, request.game)

    def _handle_list_players_request(self, request: RequestContext) -> None:
        """Handle the List Players request."""
        log.info("REQUEST[List Players]")
        self._handle_registered_players_event(request.queue, request.player)

    def _handle_advertise_game_request(self, request: RequestContext) -> None:
        """Handle the Advertise Game request."""
        log.info("REQUEST[Advertise Game]")
        if request.game:
            raise ProcessingError(FailureReason.ALREADY_PLAYING)
        context = cast(AdvertiseGameContext, request.message.context)
        self._handle_game_advertised_event(request.queue, request.player, context)

    def _handle_list_available_games_request(self, request: RequestContext) -> None:
        """Handle the List Available Games request."""
        log.info("REQUEST[List Available Games]")
        self._handle_available_games_event(request.queue, request.player)

    def _handle_join_game_request(self, request: RequestContext) -> None:
        """Handle the Join Game request."""
        log.info("REQUEST[Join Game]")
        if request.game:
            raise ProcessingError(FailureReason.ALREADY_PLAYING)
        context = cast(JoinGameContext, request.message.context)
        self._handle_game_joined_event(request.queue, request.player, context.game_id)

    def _handle_quit_game_request(self, request: RequestContext) -> None:
        """Handle the Quit Game request."""
        log.info("REQUEST[Quit Game]")
        if not request.game:
            raise ProcessingError(FailureReason.NOT_PLAYING)
        if not request.game.is_in_progress():
            raise ProcessingError(FailureReason.INVALID_GAME, "Game is not in progress")
        if request.player.handle == request.game.advertiser_handle:
            raise ProcessingError(FailureReason.ADVERTISER_MAY_NOT_QUIT)
        self._handle_game_player_quit_event(request.queue, request.player, request.game)

    def _handle_start_game_request(self, request: RequestContext) -> None:
        """Handle the Start Game request."""
        log.info("REQUEST[Start Game]")
        if not request.game:
            raise ProcessingError(FailureReason.NOT_PLAYING)
        if request.game.is_playing():
            raise ProcessingError(FailureReason.INVALID_GAME, "Game is already being played")
        if request.game.advertiser_handle != request.player.handle:
            raise ProcessingError(FailureReason.NOT_ADVERTISER)
        self._handle_game_started_event(request.queue, request.game)

    def _handle_cancel_game_request(self, request: RequestContext) -> None:
        """Handle the Cancel Game request."""
        log.info("REQUEST[Cancel Game]")
        if not request.game:
            raise ProcessingError(FailureReason.NOT_PLAYING)
        if not request.game.is_in_progress():
            raise ProcessingError(FailureReason.INVALID_GAME, "Game is not in progress")
        if request.game.advertiser_handle != request.player.handle:
            raise ProcessingError(FailureReason.NOT_ADVERTISER)
        self._handle_game_cancelled_event(request.queue, request.game, CancelledReason.CANCELLED)

    def _handle_execute_move_request(self, request: RequestContext) -> None:
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
        self._handle_game_execute_move_event(request.queue, request.player, request.game, context.move_id)

    def _handle_retrieve_game_state_request(self, request: RequestContext) -> None:
        """Handle the Retrieve Game State request."""
        log.info("REQUEST[Retrieve Game]")
        if not request.game:
            raise ProcessingError(FailureReason.NOT_PLAYING)
        if not request.game.is_playing():
            raise ProcessingError(FailureReason.INVALID_GAME, "Game is not being played")
        self._handle_game_state_change_event(request.queue, request.game, request.player)

    def _handle_send_message_request(self, request: RequestContext) -> None:
        """Handle the Send Message request."""
        log.info("REQUEST[Send Message]")
        context = cast(SendMessageContext, request.message.context)
        self._handle_player_message_received_event(request.queue, request.player.handle, context.recipient_handles, context.message)

    # noinspection PyTypeChecker
    def _handle_idle_player_check_task(self, queue: MessageQueue, idle_thresh_min: int, inactive_thresh_min: int) -> None:
        """Execute the Idle Player Check task."""
        log.info("SCHEDULED[Idle Player Check]")
        idle = 0
        inactive = 0
        now = pendulum.now()
        for (player, last_active_date, connection_state) in self._lookup_player_activity():
            disconnected = connection_state == ConnectionState.DISCONNECTED
            if now.diff(last_active_date).in_minutes > inactive_thresh_min:
                inactive += 1
                self._handle_player_inactive_event(queue, player)
            elif now.diff(last_active_date).in_minutes > idle_thresh_min:
                if disconnected:
                    inactive += 1
                    self._handle_player_inactive_event(queue, player)
                else:
                    idle += 1
                    self._handle_player_idle_event(queue, player)
        log.debug("Idle player check completed, found %d idle and %d inactive players", idle, inactive)

    # noinspection PyTypeChecker
    def _handle_idle_game_check_task(self, queue: MessageQueue, idle_thresh_min: int, inactive_thresh_min: int) -> None:
        """Execute the Idle Game Check task."""
        log.info("SCHEDULED[Idle Game Check]")
        idle = 0
        inactive = 0
        now = pendulum.now()
        for (game, last_active_date) in self._lookup_game_activity():
            if now.diff(last_active_date).in_minutes > inactive_thresh_min:
                inactive += 1
                self._handle_game_inactive_event(queue, game)
            elif now.diff(last_active_date).in_minutes > idle_thresh_min:
                idle += 1
                self._handle_game_idle_event(queue, game)
        log.debug("Idle game check completed, found %d idle and %d inactive games", idle, inactive)

    # noinspection PyTypeChecker
    def _handle_obsolete_game_check_task(self, queue: MessageQueue, retention_thresh_min: int) -> None:
        """Execute the Obsolete Game Check task."""
        log.info("SCHEDULED[Obsolete Game Check]")
        obsolete = 0
        now = pendulum.now()
        for (game, completed_date) in self._lookup_game_completion():
            if completed_date:
                if now.diff(completed_date).in_minutes > retention_thresh_min:
                    obsolete += 1
                    self._handle_game_obsolete_event(queue, game)
        log.debug("Obsolete game check completed, found %d obsolete games", obsolete)

    def _handle_server_shutdown_event(self, queue: MessageQueue) -> None:
        """Handle the Server Shutdown event."""
        log.info("EVENT[Server Shutdown]")
        websockets = self._lookup_all_websockets()
        message = Message(MessageType.SERVER_SHUTDOWN)
        queue.add(message, websockets=websockets)
        for game in self._lookup_in_progress_games():
            self._handle_game_cancelled_event(queue, game, CancelledReason.SHUTDOWN, notify=False)

    def _handle_registered_players_event(self, queue: MessageQueue, player: TrackedPlayer) -> None:
        """Handle the Registered Players event."""
        log.info("EVENT[Registered Players]")
        players = [player.to_registered_player() for player in self._lookup_all_players()]
        context = RegisteredPlayersContext(players=players)
        message = Message(MessageType.REGISTERED_PLAYERS, context)
        queue.add(message, players=[player])

    def _handle_available_games_event(self, queue: MessageQueue, player: TrackedPlayer) -> None:
        """Handle the Available Games event."""
        log.info("EVENT[Available Games]")
        games = [game.to_advertised_game() for game in self._lookup_available_games(player)]
        context = AvailableGamesContext(games=games)
        message = Message(MessageType.AVAILABLE_GAMES, context)
        queue.add(message, players=[player])

    # TODO: implement user registration limit based on configuration
    def _handle_player_registered_event(self, queue: MessageQueue, websocket: WebSocketServerProtocol, handle: str) -> None:
        """Handle the Player Registered event."""
        log.info("EVENT[Player Registered]")
        player = self._track_player(websocket, handle)
        context = PlayerRegisteredContext(player_id=player.player_id)
        message = Message(MessageType.PLAYER_REGISTERED, context)
        queue.add(message, websockets=[websocket])

    def _handle_player_reregistered_event(
        self, queue: MessageQueue, player: TrackedPlayer, websocket: WebSocketServerProtocol
    ) -> None:
        """Handle the Player Registered event."""
        log.info("EVENT[Player Registered]")
        player.websocket = websocket
        context = PlayerRegisteredContext(player_id=player.player_id)
        message = Message(MessageType.PLAYER_REGISTERED, context)
        queue.add(message, players=[player])

    def _handle_player_unregistered_event(
        self, queue: MessageQueue, player: TrackedPlayer, game: Optional[TrackedGame] = None
    ) -> None:
        """Handle the Player Unregistered event."""
        log.info("EVENT[Player Unregistered]")
        player.mark_quit()
        if game:
            comment = "Player %s unregistered" % player.handle
            game.mark_quit(player)
            self._handle_game_player_change_event(queue, game, comment)
            if not game.is_viable():
                self._handle_game_cancelled_event(queue, game, CancelledReason.NOT_VIABLE, comment)
        self._delete_player(player)

    def _handle_player_disconnected_event(self, queue: MessageQueue, websocket: WebSocketServerProtocol) -> None:
        """Handle the Player Disconnected event."""
        log.info("EVENT[Player Disconnected]")
        player = self._lookup_player_for_websocket(websocket)
        if player:
            game = self.lookup_game(player=player)
            player.mark_disconnected()
            if game:
                comment = "Player %s disconnected" % player.handle
                game.mark_quit(player)
                self._handle_game_player_change_event(queue, game, comment)
                if not game.is_viable():
                    self._handle_game_cancelled_event(queue, game, CancelledReason.NOT_VIABLE, comment)

    def _handle_player_idle_event(self, queue: MessageQueue, player: TrackedPlayer) -> None:
        """Handle the Player Idle event."""
        log.info("EVENT[Player Idle]")
        message = Message(MessageType.PLAYER_IDLE)
        queue.add(message, players=[player])
        player.mark_idle()

    def _handle_player_inactive_event(self, queue: MessageQueue, player: TrackedPlayer) -> None:
        """Handle the Player Inactive event."""
        log.info("EVENT[Player Inactive]")
        message = Message(MessageType.PLAYER_INACTIVE)
        game = self.lookup_game(player=player)
        queue.add(message, players=[player])
        player.disconnect()  # TODO: shit, this is the one thing that isn't a message, maybe I need a task queue instead?
        self._handle_player_unregistered_event(queue, player, game)

    def _handle_player_message_received_event(
        self, queue: MessageQueue, sender_handle: str, recipient_handles: List[str], sender_message: str
    ) -> None:
        """Handle the Player Message Received event."""
        log.info("EVENT[Player Message Received]")
        context = PlayerMessageReceivedContext(sender_handle, recipient_handles, sender_message)
        message = Message(MessageType.PLAYER_MESSAGE_RECEIVED, context)
        players = [self.lookup_player(handle=handle) for handle in recipient_handles]
        queue.add(message, players=[player for player in players if player])

    # TODO: implement advertised game limit based on configuration
    def _handle_game_advertised_event(self, queue: MessageQueue, player: TrackedPlayer, advertised: AdvertiseGameContext) -> None:
        """Handle the Game Advertised event."""
        log.info("EVENT[Game Advertised]")
        game = self._track_game(player, advertised)
        context = GameAdvertisedContext(game=game.to_advertised_game())
        message = Message(MessageType.GAME_ADVERTISED, context)
        queue.add(message, players=[player])
        self._handle_game_invitation_event(queue, game)
        self._handle_game_joined_event(queue, player, game.game_id)

    def _handle_game_invitation_event(self, queue: MessageQueue, game: TrackedGame) -> None:
        """Handle the Game Invitation event."""
        log.info("EVENT[Game Invitation]")
        if game.invited_handles:  # safe to reference invited_handles since it does not change
            context = GameInvitationContext(game=game.to_advertised_game())
            message = Message(MessageType.GAME_INVITATION, context)
            players = [self.lookup_player(handle=handle) for handle in game.invited_handles]
            queue.add(message, players=[player for player in players if player])

    def _handle_game_joined_event(self, queue: MessageQueue, player: TrackedPlayer, game_id: str) -> None:
        """Handle the Game Joined event."""
        log.info("EVENT[Game Joined]")
        game = self.lookup_game(game_id=game_id)
        if not game or not game.is_available(player):
            raise ProcessingError(FailureReason.INVALID_GAME)
        game.mark_active()
        player.mark_joined(game)
        game.mark_joined(player)
        context = GameJoinedContext(game_id=game_id)
        message = Message(MessageType.GAME_JOINED, context)
        queue.add(message, players=[player])
        if game.is_fully_joined():
            self._handle_game_started_event(queue, game)

    # TODO: implement in progress game limit based on configuration
    def _handle_game_started_event(self, queue: MessageQueue, game: TrackedGame) -> None:
        """Handle the Game Started event."""
        log.info("EVENT[Game Started]")
        message = Message(MessageType.GAME_STARTED)
        game.mark_active()
        game.mark_started()
        players = self._lookup_game_players(game)
        for player in players:
            player.mark_playing()
        queue.add(message, players=players)
        self._handle_game_player_change_event(queue, game, "Game started")
        self._handle_game_state_change_event(queue, game)

    def _handle_game_cancelled_event(
        self, queue: MessageQueue, game: TrackedGame, reason: CancelledReason, comment: Optional[str] = None, notify: bool = True
    ) -> None:
        """Handle the Game Cancelled event."""
        log.info("EVENT[Game Cancelled]")
        context = GameCancelledContext(reason=reason, comment=comment)
        message = Message(MessageType.GAME_CANCELLED, context)
        players = self._lookup_game_players(game)
        for player in players:
            player.mark_quit()
        game.mark_cancelled(reason, comment)
        if notify:
            queue.add(message, players=players)
            self._handle_game_state_change_event(queue, game)

    # TODO: as of now, nothing triggers this event
    def _handle_game_completed_event(self, queue: MessageQueue, game: TrackedGame, comment: Optional[str] = None) -> None:
        """Handle the Game Completed event."""
        log.info("EVENT[Game Completed]")
        context = GameCompletedContext(comment=comment)
        message = Message(MessageType.GAME_COMPLETED, context)
        players = self._lookup_game_players(game)
        for player in players:
            player.mark_quit()
        game.mark_completed(comment)
        queue.add(message, players=players)
        self._handle_game_state_change_event(queue, game)

    def _handle_game_idle_event(self, queue: MessageQueue, game: TrackedGame) -> None:
        """Handle the Game Idle event."""
        log.info("EVENT[Game Idle]")
        message = Message(MessageType.GAME_IDLE)
        players = self._lookup_game_players(game)
        queue.add(message, players=players)

    def _handle_game_inactive_event(self, queue: MessageQueue, game: TrackedGame) -> None:
        """Handle the Game Inactive event."""
        log.info("EVENT[Game Inactive]")
        self._handle_game_cancelled_event(queue, game, CancelledReason.INACTIVE)

    def _handle_game_obsolete_event(self, queue: MessageQueue, game: TrackedGame) -> None:
        """Handle the Game Obsolete event."""
        log.info("EVENT[Game Obsolete]")
        self._delete_game(game)

    def _handle_game_player_quit_event(self, queue: MessageQueue, player: TrackedPlayer, game: TrackedGame) -> None:
        """Handle the Player Unregistered event."""
        log.info("EVENT[Game Player Quit]")
        comment = "Player %s quit" % player.handle
        game.mark_active()
        player.mark_quit()
        game.mark_quit(player)
        self._handle_game_player_change_event(queue, game, comment)
        if not game.is_viable():
            self._handle_game_cancelled_event(queue, game, CancelledReason.NOT_VIABLE, comment)

    # TODO: this needs to somehow trigger a Game Player Turn event for the next player (not sure how to do that yet)
    def _handle_game_execute_move_event(self, queue: MessageQueue, player: TrackedPlayer, game: TrackedGame, move_id: str) -> None:
        """Handle the Execute Move event."""
        log.info("EVENT[Execute Move]")
        game.mark_active()
        (completed, comment) = game.execute_move(player, move_id)
        if completed:
            self._handle_game_completed_event(queue, game, comment)
        else:
            self._handle_game_state_change_event(queue, game)

    def _handle_game_player_change_event(self, queue: MessageQueue, game: TrackedGame, comment: str) -> None:
        """Handle the Game Player Change event."""
        log.info("EVENT[Game Player Change]")
        players = self._lookup_game_players(game)
        context = GamePlayerChangeContext(comment=comment, players=game.get_game_players())
        message = Message(MessageType.GAME_PLAYER_CHANGE, context=context)
        queue.add(message, players=players)

    # pylint: disable=redefined-argument-from-local
    def _handle_game_state_change_event(
        self, queue: MessageQueue, game: TrackedGame, player: Optional[TrackedPlayer] = None
    ) -> None:
        """Handle the Game State Change event."""
        log.info("EVENT[Game State Change]")
        game.mark_active()
        players = [player] if player else self._lookup_game_players(game)
        for player in players:
            view = game.get_player_view(player)
            context = GameStateChangeContext.for_view(view)
            message = Message(MessageType.GAME_STATE_CHANGE, context=context)
            queue.add(message, players=[player])

    def _handle_game_player_turn_event(
        self, queue: MessageQueue, game: TrackedGame, player: TrackedPlayer, moves: List[Move]
    ) -> None:
        """Handle the Game Player Turn event."""
        log.info("EVENT[Game Player Turn]")
        context = GamePlayerTurnContext.for_moves(moves)
        message = Message(MessageType.GAME_PLAYER_TURN, context)
        queue.add(message, players=[player])


_LOCK = asyncio.Lock()
_STATE_MANAGER = StateManager()

# noinspection PyBroadException
async def handle_exception(exception: Exception, websocket: WebSocketServerProtocol) -> None:
    """Handle an exception by sending a request failed event."""
    try:
        raise exception
    except ProcessingError as e:
        context = RequestFailedContext(e.reason, e.comment if e.comment else e.reason.value)
    except ValueError as e:
        context = RequestFailedContext(FailureReason.INVALID_REQUEST, str(e))
    except Exception as e:  # pylint: disable=broad-except
        context = RequestFailedContext(FailureReason.INTERNAL_ERROR, FailureReason.INTERNAL_ERROR.value)
    message = Message(MessageType.REQUEST_FAILED, context)
    await websocket.send(message.to_json())


async def handle_shutdown() -> MessageQueue:
    """Handle system shutdown."""
    with _LOCK:
        return _STATE_MANAGER.handle_shutdown()


async def handle_disconnect(websocket: WebSocketServerProtocol) -> MessageQueue:
    """Handle a disconnected websocket."""
    with _LOCK:
        return _STATE_MANAGER.handle_disconnect(websocket)


async def handle_register(message: Message, websocket: WebSocketServerProtocol) -> MessageQueue:
    """Handle a REGISTER_PLAYER message received on a websocket by dispatching to the state manager."""
    with _LOCK:
        return _STATE_MANAGER.handle_register(message, websocket)


async def handle_message(player_id: str, message: Message, websocket: WebSocketServerProtocol) -> MessageQueue:
    """Handle a message received on a websocket by dispatching to the state manager."""
    with _LOCK:
        return _STATE_MANAGER.handle_message(player_id, message, websocket)


async def handle_idle_players(idle_thresh_min: int, inactive_thresh_min: int) -> MessageQueue:
    """Handle the idle player check by dispatching to the state manager."""
    with _LOCK:
        return _STATE_MANAGER.handle_idle_players(idle_thresh_min, inactive_thresh_min)


async def handle_idle_games(idle_thresh_min: int, inactive_thresh_min: int) -> MessageQueue:
    """Handle idle games by dispatching to the state manager."""
    with _LOCK:
        return _STATE_MANAGER.handle_idle_games(idle_thresh_min, inactive_thresh_min)


async def handle_obsolete_games(retention_thresh_min: int) -> MessageQueue:
    """Handle obsolete games by dispatching to the state manager."""
    with _LOCK:
        return _STATE_MANAGER.handle_obsolete_games(retention_thresh_min)
