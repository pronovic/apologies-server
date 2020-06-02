# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import,too-many-lines

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

The transaction boundary is handled by a single lock on the StateManager object.  Callers
must ensure that they get that lock before reading or modifying state in any way.  Other 
than that, none of the objects defined in this module are thread-safe, or even thread-aware.  
There are no asynchronous methods or await calls.  This simplifies the implementation and 
avoids confusion.
"""

from __future__ import annotations  # see: https://stackoverflow.com/a/33533514/2907667

import asyncio
import logging
import random
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

import attr
import pendulum
from apologies.engine import Character, Engine
from apologies.game import GameMode, History, PlayerColor, PlayerView
from apologies.rules import Move
from apologies.source import NoOpInputSource
from ordered_set import OrderedSet  # this makes expected results easier to articulate in test code
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
class TrackedWebsocket:
    """The state that is tracked for a websocket within the state manager."""

    websocket = attr.ib(type=WebSocketServerProtocol)
    registration_date = attr.ib(type=DateTime)
    last_active_date = attr.ib(type=DateTime)
    activity_state = attr.ib(type=ActivityState, default=ActivityState.ACTIVE)
    player_ids = attr.ib(type=OrderedSet[str])

    @registration_date.default
    def _default_registration_date(self) -> DateTime:
        return pendulum.now()

    @last_active_date.default
    def _default_last_active_date(self) -> DateTime:
        return pendulum.now()

    @player_ids.default
    def _default_player_ids(self) -> OrderedSet[str]:
        return OrderedSet()

    def mark_active(self) -> None:
        """Mark the websocket as active."""
        self.last_active_date = pendulum.now()
        self.activity_state = ActivityState.ACTIVE

    def mark_idle(self) -> None:
        """Mark the websocket as idle."""
        self.activity_state = ActivityState.IDLE

    def mark_inactive(self) -> None:
        """Mark the websocket as inactive."""
        self.activity_state = ActivityState.INACTIVE


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


@attr.s(frozen=True)
class CurrentTurn:

    handle = attr.ib(type=str)
    color = attr.ib(type=PlayerColor)
    view = attr.ib(type=PlayerView)
    movelist = attr.ib(type=List[Move])
    movedict = attr.ib(type=Dict[str, Move])

    def draw_again(self, engine: Engine) -> CurrentTurn:
        return CurrentTurn.for_handle(engine, self.handle, self.color)

    @staticmethod
    def next_player(engine: Engine) -> CurrentTurn:
        color, character = engine.next_turn()
        return CurrentTurn.for_handle(engine, character.name, color)

    @staticmethod
    def for_handle(engine: Engine, handle: str, color: PlayerColor) -> CurrentTurn:
        view = engine.game.create_player_view(color)
        _, movelist = engine.construct_legal_moves(view)
        movedict = {move.id: move for move in movelist}
        return CurrentTurn(handle=handle, color=color, view=view, movelist=movelist, movedict=movedict)


@attr.s
class TrackedEngine:
    """Wrapper over an Apologies game engine, to manage game play state for TrackedGame."""

    _engine = attr.ib(type=Optional[Engine], default=None)
    _colors = attr.ib(type=Dict[str, PlayerColor])
    _current = attr.ib(type=Optional[CurrentTurn], default=None)

    @_colors.default
    def _default_colors(self) -> Dict[str, PlayerColor]:
        return {}

    def start_game(self, mode: GameMode, handles: List[str]) -> Dict[str, PlayerColor]:
        """Start the game, returning a map from handle to assigned color."""
        if self._engine:
            raise ProcessingError(FailureReason.INTERNAL_ERROR, "Illegal state for operation")
        characters = [Character(name=handle, source=NoOpInputSource()) for handle in handles]
        self._engine = Engine(mode, characters=characters)
        self._engine.start_game()
        self._colors = {character.name: color for color, character in self._engine.colors.items()}
        self._current = CurrentTurn.next_player(self._engine)
        return self._colors.copy()  # copy so caller can't mess with internal state

    def stop_game(self) -> None:
        """Stop the game after the game is completed or has been cancelled."""
        self._engine = None
        self._colors = {}
        self._current = None

    def get_next_turn(self) -> str:
        """Get the handle of the player that should play the next turn."""
        if not self._current:
            raise ProcessingError(FailureReason.INTERNAL_ERROR, "Illegal state for operation")
        return self._current.handle

    def get_legal_moves(self, handle: str) -> List[Move]:
        """Get the legal moves for the player at this stage in the game."""
        if not self._current or handle != self._current.handle:
            raise ProcessingError(FailureReason.INTERNAL_ERROR, "Illegal state for operation")
        return self._current.movelist[:]

    def get_player_view(self, handle: str) -> PlayerView:
        """Get the player's view of the game state."""
        if not self._engine or handle not in self._colors:
            raise ProcessingError(FailureReason.INTERNAL_ERROR, "Illegal state for operation")
        color = self._colors[handle]
        return self._engine.game.create_player_view(color)

    def get_recent_history(self, max_entries: int) -> List[History]:
        """Return up to a certain number of game history entries."""
        if not self._engine or not self._engine.game:
            raise ProcessingError(FailureReason.INTERNAL_ERROR, "Illegal state for operation")
        return self._engine.game.history[-max_entries:]

    def is_move_pending(self, handle: str) -> bool:
        """Whether a move is pending for the player with the passed-in handle."""
        if not self._current:
            raise ProcessingError(FailureReason.INTERNAL_ERROR, "Illegal state for operation")
        return handle == self._current.handle

    def is_legal_move(self, handle: str, move_id: str) -> bool:
        """Whether the passed-in move id is a legal move for the player."""
        if not self._current:
            raise ProcessingError(FailureReason.INTERNAL_ERROR, "Illegal state for operation")
        return handle == self._current.handle and move_id in self._current.movedict

    def execute_move(self, handle: str, move_id: str) -> Tuple[bool, Optional[str]]:
        """Execute a player's move, returning whether the game was completed (and a comment if so)."""
        if (
            not self._engine
            or not self._current
            or not handle == self._current.handle
            or handle not in self._colors
            or move_id not in self._current.movedict
        ):
            raise ProcessingError(FailureReason.INTERNAL_ERROR, "Illegal state for operation")
        color = self._colors[handle]
        move = self._current.movedict[move_id]
        done = self._engine.execute_move(color, move)
        if self._engine.completed:
            self._current = None
            character, player = self._engine.winner()  # type: ignore
            comment = "Player %s (%s) won after %d turns" % (character.name, player.color.name, player.turns)
            return True, comment
        self._current = CurrentTurn.next_player(self._engine) if done else self._current.draw_again(self._engine)
        return False, None


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
    _engine = attr.ib(type=TrackedEngine)

    @advertised_date.default
    def _default_advertised_date(self) -> DateTime:
        return pendulum.now()

    @last_active_date.default
    def _default_last_active_date(self) -> DateTime:
        return pendulum.now()

    @game_players.default
    def _default_game_players(self) -> Dict[str, GamePlayer]:
        return {}

    @_engine.default
    def _default_engine(self) -> TrackedEngine:
        return TrackedEngine()

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

    def get_available_players(self) -> List[GamePlayer]:
        """Get the players that are still available to play the game."""
        return [
            player for player in self.get_game_players() if player.player_state not in (PlayerState.QUIT, PlayerState.DISCONNECTED)
        ]

    def get_available_player_count(self) -> int:
        """Get the number of players that are still available to play the game."""
        return len(self.get_available_players())

    def get_next_turn(self) -> Tuple[str, PlayerType]:
        """Get the next turn to be played."""
        handle = self._engine.get_next_turn()
        player = self.game_players[handle]
        return handle, player.player_type

    def get_legal_moves(self, handle: str) -> List[Move]:
        """Get the legal moves for the player at this stage in the game."""
        return self._engine.get_legal_moves(handle)

    def get_player_view(self, handle: str) -> PlayerView:
        """Get the player's view of the game state."""
        return self._engine.get_player_view(handle)

    def get_recent_history(self, max_entries: int) -> List[History]:
        """Return up to a certain number of game history entries."""
        return self._engine.get_recent_history(max_entries)

    def is_available(self, handle: str) -> bool:
        """Whether the game is available to be joined by the passed-in player."""
        return self.game_state == GameState.ADVERTISED and (self.visibility == Visibility.PUBLIC or handle in self.invited_handles)

    def is_advertised(self) -> bool:
        """Whether a game is currently being advertised."""
        return self.game_state == GameState.ADVERTISED

    def is_playing(self) -> bool:
        """Whether a game is being played."""
        return self.game_state == GameState.PLAYING

    def is_in_progress(self) -> bool:
        """Whether a game is in-progress, meaning it is advertised or being played."""
        return self.is_advertised() or self.is_playing()

    def is_fully_joined(self) -> bool:
        """Whether the number of requested players have joined the game."""
        return self.players == len(self.game_players)

    def is_viable(self) -> bool:
        """Whether the game is viable."""
        # Advertised games are always viable. Otherwise, the game is only viable if at least two players remain to play turns.
        if self.is_advertised():
            return True
        else:
            return self.get_available_player_count() >= 2

    def is_move_pending(self, handle: str) -> bool:
        """Whether a move is pending for the player with the passed-in handle."""
        return self._engine.is_move_pending(handle)

    def is_legal_move(self, handle: str, move_id: str) -> bool:
        """Whether the passed-in move id is a legal move for the player."""
        return self._engine.is_legal_move(handle, move_id)

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

    def mark_joined(self, handle: str) -> None:
        """Mark that a player has joined a game."""
        if self.game_state != GameState.ADVERTISED:
            raise ProcessingError(FailureReason.INTERNAL_ERROR, "Illegal state for operation")
        player_color = None  # will be assigned after game starts
        player_type = PlayerType.HUMAN
        player_state = PlayerState.JOINED
        self.game_players[handle] = GamePlayer(handle, player_color, player_type, player_state)

    def mark_started(self) -> None:
        """Mark the game as started."""
        if self.game_state != GameState.ADVERTISED:
            raise ProcessingError(FailureReason.INTERNAL_ERROR, "Illegal state for operation")
        self.game_state = GameState.PLAYING
        self.last_active_date = pendulum.now()
        self.started_date = pendulum.now()
        for _ in range(0, self.players - len(self.game_players)):
            self._mark_joined_programmatic()  # fill in remaining players as necessary
        colors = self._engine.start_game(self.mode, list(self.game_players.keys()))
        for handle in self.game_players:
            self.game_players[handle] = attr.evolve(
                self.game_players[handle], player_color=colors[handle], player_state=PlayerState.PLAYING
            )

    def mark_completed(self, comment: Optional[str]) -> None:
        """Mark the game as completed."""
        if self.game_state != GameState.PLAYING:
            raise ProcessingError(FailureReason.INTERNAL_ERROR, "Illegal state for operation")
        self.completed_date = pendulum.now()
        self.game_state = GameState.COMPLETED
        self.completed_comment = comment
        for handle in self.game_players:
            self.game_players[handle] = attr.evolve(self.game_players[handle], player_state=PlayerState.FINISHED)
        self._engine.stop_game()

    def mark_cancelled(self, reason: CancelledReason, comment: Optional[str] = None) -> None:
        """Mark the game as cancelled."""
        if self.game_state not in [GameState.ADVERTISED, GameState.PLAYING]:
            raise ProcessingError(FailureReason.INTERNAL_ERROR, "Illegal state for operation")
        self.completed_date = pendulum.now()
        self.game_state = GameState.CANCELLED
        self.cancelled_reason = reason
        self.completed_comment = comment
        for handle in self.game_players:
            self.game_players[handle] = attr.evolve(self.game_players[handle], player_state=PlayerState.FINISHED)
        self._engine.stop_game()

    def mark_quit(self, handle: str) -> None:
        """Mark that the player has quit a game."""
        # We assume that if the player is in the middle of their turn, that the caller handles that cleanup
        if self.game_state == GameState.ADVERTISED:
            del self.game_players[handle]  # if the game hasn't started, just remove them
        elif self.game_state == GameState.PLAYING:
            self.game_players[handle] = attr.evolve(self.game_players[handle], player_state=PlayerState.QUIT)
        else:
            raise ProcessingError(FailureReason.INTERNAL_ERROR, "Illegal state for operation")

    def execute_move(self, handle: str, move_id: str) -> Tuple[bool, Optional[str]]:
        """Execute a player's move, returning an indication of whether the game was completed (and a comment if so)."""
        return self._engine.execute_move(handle, move_id)

    def _mark_joined_programmatic(self) -> None:
        """Create an join a programmatic player, assumed to be called from within a lock."""
        handle = self._assign_handle()
        player_color = None  # will be assigned after game starts
        player_type = PlayerType.PROGRAMMATIC
        player_state = PlayerState.JOINED
        self.game_players[handle] = GamePlayer(handle, player_color, player_type, player_state)

    def _assign_handle(self) -> str:
        """Assign a handle to the newly-joined programmatic player, assumed to be called from within a lock."""
        all_handles = set(_NAMES)
        used_handles = {player.handle for player in self.game_players.values()}
        available_handles = all_handles - used_handles
        return random.choice(list(available_handles))


# noinspection PyMethodMayBeStatic
@attr.s
class StateManager:

    """Manages system state."""

    lock = attr.ib(type=asyncio.Lock)
    _websocket_map = attr.ib(type=Dict[WebSocketServerProtocol, TrackedWebsocket])
    _game_map = attr.ib(type=Dict[str, TrackedGame])
    _player_map = attr.ib(type=Dict[str, TrackedPlayer])
    _handle_map = attr.ib(type=Dict[str, str])

    @lock.default
    def _default_lock(self) -> asyncio.Lock:
        return asyncio.Lock()

    @_websocket_map.default
    def _default_websocket_map(self) -> Dict[WebSocketServerProtocol, TrackedWebsocket]:
        return {}

    @_game_map.default
    def _default_game_map(self) -> Dict[str, TrackedGame]:
        return {}

    @_player_map.default
    def _default_player_map(self) -> Dict[str, TrackedPlayer]:
        return {}

    @_handle_map.default
    def _default_handle_map(self) -> Dict[str, str]:
        return {}

    def mark_active(self, player: TrackedPlayer) -> None:
        """Mark a player and its associated websocket as active."""
        if player.websocket:
            # The player might not have a websocket if they've been disconnected.
            # However, if the player has a websocket, then it must be valid or we have a problem of internal consistency.
            if player.websocket not in self._websocket_map:
                raise ProcessingError(FailureReason.INTERNAL_ERROR, comment="Did not find player websocket", handle=player.handle)
            websocket = self._websocket_map[player.websocket]
            websocket.mark_active()
        player.mark_active()

    def track_websocket(self, websocket: WebSocketServerProtocol) -> None:
        """Track a connected websocket."""
        if websocket in self._websocket_map:
            raise ProcessingError(FailureReason.INTERNAL_ERROR, comment="Duplicate websocket encountered")
        self._websocket_map[websocket] = TrackedWebsocket(websocket=websocket)

    def delete_websocket(self, websocket: WebSocketServerProtocol) -> None:
        """Delete a websocket, so it is no longer tracked."""
        if websocket in self._websocket_map:
            del self._websocket_map[websocket]

    def get_websocket_count(self) -> int:
        """Return the number of connected websockets in the system."""
        return len(self._websocket_map)

    def lookup_all_websockets(self) -> List[WebSocketServerProtocol]:
        """Return a list of websockets for all tracked players."""
        return list(self._websocket_map.keys())

    def lookup_players_for_websocket(self, websocket: WebSocketServerProtocol) -> List[TrackedPlayer]:
        """Look up the players associated with a websocket, if any."""
        players = []
        if websocket in self._websocket_map:
            players = [self.lookup_player(player_id=player_id) for player_id in self._websocket_map[websocket].player_ids]
        return [player for player in players if player is not None]

    def track_game(self, player: TrackedPlayer, advertised: AdvertiseGameContext) -> TrackedGame:
        """Track a newly-advertised game."""
        game_id = "%s" % uuid4()
        self._game_map[game_id] = TrackedGame.for_context(player.handle, game_id, advertised)
        return self._game_map[game_id]

    def delete_game(self, game: TrackedGame) -> None:
        """Delete a tracked game, so it is no longer tracked."""
        if game.game_id in self._game_map:
            del self._game_map[game.game_id]

    def get_total_game_count(self) -> int:
        """Return the total number of games in the system."""
        return len(self._game_map)

    def get_in_progress_game_count(self) -> int:
        """Return the number of in-progress games in the system."""
        return len([game for game in self._game_map.values() if game.is_in_progress()])

    def lookup_game(self, game_id: Optional[str] = None, player: Optional[TrackedPlayer] = None) -> Optional[TrackedGame]:
        """Look up a game by id, returning None if the game is not found."""
        if game_id:
            return self._game_map[game_id] if game_id in self._game_map else None
        elif player:
            return self.lookup_game(game_id=player.game_id)
        else:
            return None

    def lookup_all_games(self) -> List[TrackedGame]:
        """Return a list of all tracked games."""
        return list(self._game_map.values())

    def lookup_in_progress_games(self) -> List[TrackedGame]:
        """Return a list of all in-progress games."""
        return [game for game in self.lookup_all_games() if game.is_in_progress()]

    def lookup_game_players(self, game: TrackedGame) -> List[TrackedPlayer]:
        """Lookup the players that are currently playing a game."""
        handles = [player.handle for player in game.game_players.values() if player.player_type == PlayerType.HUMAN]
        players = [self.lookup_player(handle=handle) for handle in handles]
        return [player for player in players if player is not None]

    def lookup_available_games(self, player: TrackedPlayer) -> List[TrackedGame]:
        """Return a list of games the passed-in player may join."""
        games = self.lookup_all_games()
        return [game for game in games if game.is_available(player.handle)]

    def track_player(self, websocket: WebSocketServerProtocol, handle: str) -> TrackedPlayer:
        """Track a newly-registered player."""
        if handle in self._handle_map:
            raise ProcessingError(FailureReason.DUPLICATE_USER, handle=handle)
        player_id = "%s" % uuid4()
        self._websocket_map[websocket].mark_active()  # we never want a websocket to time out before an associated player
        self._websocket_map[websocket].player_ids.add(player_id)
        self._player_map[player_id] = TrackedPlayer.for_context(player_id, websocket, handle)
        self._handle_map[handle] = player_id
        return self._player_map[player_id]

    def retrack_player(self, player: TrackedPlayer, websocket: WebSocketServerProtocol) -> None:
        """Re-track and existing player, associating it with a different websocket."""
        player.websocket = websocket
        self._websocket_map[websocket].mark_active()  # we never want a websocket to time out before an associated player
        self._websocket_map[websocket].player_ids.add(player.player_id)

    def delete_player(self, player: TrackedPlayer) -> None:
        """Delete a tracked player, so it is no longer tracked."""
        if player.websocket and player.websocket in self._websocket_map:
            self._websocket_map[player.websocket].player_ids.discard(player.player_id)
        if player.handle in self._handle_map:
            del self._handle_map[player.handle]
        if player.player_id in self._player_map:
            del self._player_map[player.player_id]

    def get_registered_player_count(self) -> int:
        """Return the number of registered players in the system."""
        return len(self._player_map)

    def lookup_player(self, player_id: Optional[str] = None, handle: Optional[str] = None) -> Optional[TrackedPlayer]:
        """Look up a player by either player id or handle."""
        if player_id:
            return self._player_map[player_id] if player_id in self._player_map else None
        elif handle:
            player_id = self._handle_map[handle] if handle in self._handle_map else None
            return self.lookup_player(player_id=player_id)
        else:
            return None

    def lookup_all_players(self) -> List[TrackedPlayer]:
        """Return a list of all tracked players."""
        return list(self._player_map.values())

    def lookup_websocket_activity(self) -> List[Tuple[TrackedWebsocket, DateTime, int]]:
        """Look up the last active date and number of registered players for all websockets."""
        result: List[Tuple[TrackedWebsocket, DateTime, int]] = []
        for websocket in self._websocket_map.values():
            result.append((websocket, websocket.last_active_date, len(websocket.player_ids)))
        return result

    def lookup_player_activity(self) -> List[Tuple[TrackedPlayer, DateTime, ConnectionState]]:
        """Look up the last active date and connection state for all players."""
        result: List[Tuple[TrackedPlayer, DateTime, ConnectionState]] = []
        for player in self._player_map.values():
            result.append((player, player.last_active_date, player.connection_state))
        return result

    def lookup_game_activity(self) -> List[Tuple[TrackedGame, DateTime]]:
        """Look up the last active date for all games."""
        result: List[Tuple[TrackedGame, DateTime]] = []
        for game in self._game_map.values():
            result.append((game, game.last_active_date))
        return result

    def lookup_game_completion(self) -> List[Tuple[TrackedGame, Optional[DateTime]]]:
        """Look up the completed date for all completed games."""
        result: List[Tuple[TrackedGame, Optional[DateTime]]] = []
        for game in self._game_map.values():
            if game.game_state == GameState.COMPLETED:
                result.append((game, game.completed_date))
        return result


_MANAGER = StateManager()


def manager() -> StateManager:
    """Return the state manager."""
    return _MANAGER
