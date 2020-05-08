# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import

# TODO: this needs unit tests, but probably after the other code is done
# TODO: this does not actually include any way to manage game state or engine yet (that's the next big design step)

"""
Code to manage application state.
"""

# Note: I suspect (but can't yet prove) that there may be some race conditions here that  I am
#       not handling correctly right now.  Game state and player state are not locked globally
#       (i.e. we don't do all game updates behind a single lock) and I think that may make it
#       possible to get into some weird situations under load, when a lot of requests and
#       events are being processed concurrently.  An example here is someone quitting a game as
#       it's in the process of being started, or something like that.  I think that all the
#       actual updates are appropriately properly behind locks, etc.  The problem is more that
#       individual pieces of data are updated independently, not always behind the same lock.
#       I think that's where the risk probably is, depending on how Python manages all of these
#       sorta-concurrent coroutine operations in practice.  However, I don't understand this
#       software model well enough to know what I'm doing wrong.  I may need to rework the lock
#       behavior later, but at least it's mostly encapsulated here.

from __future__ import annotations  # see: https://stackoverflow.com/a/33533514/2907667

import asyncio
import random
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

import attr
import pendulum
from apologies.game import GameMode, Player, PlayerColor, PlayerView
from pendulum.datetime import DateTime
from websockets import WebSocketServerProtocol

from .interface import *

__all__ = [
    "TrackedPlayer",
    "TrackedGame",
    "track_game",
    "delete_game",
    "lookup_game",
    "lookup_all_games",
    "lookup_in_progress_games",
    "lookup_game_players",
    "lookup_available_games",
    "track_player",
    "delete_player",
    "lookup_player",
    "lookup_all_players",
    "lookup_websocket",
    "lookup_websockets",
    "lookup_all_websockets",
    "lookup_player_for_websocket",
]

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


# pylint: disable=too-many-instance-attributes
@attr.s
class TrackedPlayer:
    """
    The state that is tracked for a player within the game server.
    
    Any code that wishes to read or write attributes on a TrackedPlayer object must acquire the
    object's asyncio lock first, or else call one of the helper methods that takes care of the
    lock.  It is safe to reference the player id or handle without locking the object, since
    these values must never be changed after the player is created.  (Unfortunately, there is
    no way to enforce this using attrs at the present time.)
    """

    player_id = attr.ib(type=str, repr=False)  # treat as read-only; this is a secret, so we don't want it printed or logged
    handle = attr.ib(type=str)  # treat as read-only
    websocket = attr.ib(type=Optional[WebSocketServerProtocol])
    registration_date = attr.ib(type=DateTime)
    last_active_date = attr.ib(type=DateTime)
    activity_state = attr.ib(type=ActivityState, default=ActivityState.ACTIVE)
    connection_state = attr.ib(type=ConnectionState, default=ConnectionState.CONNECTED)
    player_state = attr.ib(type=PlayerState, default=PlayerState.WAITING)
    game_id = attr.ib(type=Optional[str], default=None)
    lock = attr.ib(type=asyncio.Lock)

    @registration_date.default
    def _default_registration_date(self) -> DateTime:
        return pendulum.now()

    @last_active_date.default
    def _default_last_active_date(self) -> DateTime:
        return pendulum.now()

    @lock.default
    def _default_lock(self) -> asyncio.Lock:
        return asyncio.Lock()

    @staticmethod
    def for_context(player_id: str, websocket: WebSocketServerProtocol, handle: str) -> TrackedPlayer:
        """Create a tracked player based on provided context."""
        return TrackedPlayer(player_id=player_id, websocket=websocket, handle=handle)

    async def to_registered_player(self) -> RegisteredPlayer:
        """Convert this TrackedPlayer to a RegisteredPlayer."""
        async with self.lock:
            return RegisteredPlayer(
                handle=self.handle,
                registration_date=self.registration_date,
                last_active_date=self.last_active_date,
                connection_state=self.connection_state,
                activity_state=self.activity_state,
                player_state=self.player_state,
                game_id=self.game_id,
            )

    async def set_websocket(self, websocket: WebSocketServerProtocol) -> None:
        """Set the webhook for this player."""
        async with self.lock:
            self.websocket = websocket

    async def is_connected(self) -> bool:
        """Whether the player is connected."""
        async with self.lock:
            return self.connection_state == ConnectionState.CONNECTED

    async def disconnect(self) -> None:
        async with self.lock:
            if self.websocket:
                try:
                    await self.websocket.close()
                except:  # pylint: disable=bare-except
                    pass
        await self.mark_disconnected()

    async def mark_active(self) -> None:
        """Mark the player as active."""
        async with self.lock:
            self.last_active_date = pendulum.now()
            self.activity_state = ActivityState.ACTIVE
            self.connection_state = ConnectionState.CONNECTED

    async def mark_idle(self) -> None:
        """Mark the player as idle."""
        async with self.lock:
            self.activity_state = ActivityState.IDLE

    async def mark_inactive(self) -> None:
        """Mark the player as inactive."""
        async with self.lock:
            self.activity_state = ActivityState.INACTIVE

    async def mark_joined(self, game: TrackedGame) -> None:
        """Mark that the player has joined a game."""
        async with self.lock:
            self.game_id = game.game_id
            self.player_state = PlayerState.JOINED

    async def mark_playing(self) -> None:
        """Mark that the player is playing a game."""
        async with self.lock:
            self.player_state = PlayerState.PLAYING

    async def mark_quit(self) -> None:
        """Mark that the player has quit a game."""
        async with self.lock:
            self.game_id = None
            self.player_state = PlayerState.WAITING  # they go right through QUIT and back to WAITING

    async def mark_disconnected(self) -> None:
        """Mark the player as disconnected."""
        await self.mark_quit()
        async with self.lock:
            self.websocket = None
            self.activity_state = ActivityState.IDLE
            self.connection_state = ConnectionState.DISCONNECTED


# pylint: disable=too-many-instance-attributes,too-many-public-methods
@attr.s
class TrackedGame:
    """
    The state that is tracked for a game within the game server.
    
    Any code that wishes to read or write attributes on a TrackedGame object must acquire the
    object's asyncio lock first, or else call one of the helper methods that takes care of the
    lock.  It is safe to reference the game id, advertiser handle, name, mode, players,
    visibility, and invited handles without locking the class, since they must not be changed
    after the game is created.  (Unfortunately, there is no way to enforce this using attrs at
    the present time.)
    """

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
    lock = attr.ib(type=asyncio.Lock)

    @advertised_date.default
    def _default_advertised_date(self) -> DateTime:
        return pendulum.now()

    @last_active_date.default
    def _default_last_active_date(self) -> DateTime:
        return pendulum.now()

    @lock.default
    def _default_lock(self) -> asyncio.Lock:
        return asyncio.Lock()

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

    async def to_advertised_game(self) -> AdvertisedGame:
        """Convert this tracked game to an AdvertisedGame."""
        async with self.lock:
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

    async def get_game_players(self) -> List[GamePlayer]:
        """Get a list of game players."""
        async with self.lock:
            return list(self.game_players.values())

    async def is_available(self, player: TrackedPlayer) -> bool:
        """Whether the game is available to be joined by the passed-in player."""
        async with self.lock:
            return self.game_state == GameState.ADVERTISED and (
                self.visibility == Visibility.PUBLIC or player.handle in self.invited_handles
            )

    async def is_in_progress(self) -> bool:
        """Whether a game is in-progress, meaning it is advertised or being played."""
        return await self.is_advertised() or await self.is_playing()

    async def is_advertised(self) -> bool:
        """Whether a game is currently being advertised."""
        async with self.lock:
            return self.game_state == GameState.ADVERTISED

    async def is_playing(self) -> bool:
        """Whether a game is being played."""
        async with self.lock:
            return self.game_state == GameState.PLAYING

    # TODO: this needs to take into account game state
    #       if the game has not been started, a player leaving does not impact viability
    #       if the game has not been started, if the advertising player leaves, that cancels the game
    async def is_viable(self) -> bool:
        """Whether the game is viable."""
        async with self.lock:
            available = len([player for player in self.game_players.values() if player.is_available()])
            return self.players - available > 2  # game is only viable if at least 2 players remain to play turns

    async def is_fully_joined(self) -> bool:
        """Whether the number of requested players have joined the game."""
        async with self.lock:
            return self.players == len(self.game_players)

    # TODO: remove unused-argument when method is implemented
    # pylint: disable=unused-argument
    async def is_move_pending(self, handle: str) -> bool:
        """Whether a move is pending for the player with the passed-in handle."""
        # TODO: implement is_move_pending() - if we are waiting for the player and the game is not completed or cancelled
        return True

    # TODO: remove unused-argument when method is implemented
    # pylint: disable=unused-argument
    async def is_legal_move(self, handle: str, move_id: str) -> bool:
        """Whether the passed-in move id is a legal move for the player."""
        # TODO: implement is_legal_move() - this is actually a superset of is_move_pending() but is separate for clarity
        return True

    async def mark_active(self) -> None:
        """Mark the game as active."""
        async with self.lock:
            self.last_active_date = pendulum.now()
            self.activity_state = ActivityState.ACTIVE

    async def mark_idle(self) -> None:
        """Mark the game as idle."""
        async with self.lock:
            self.activity_state = ActivityState.IDLE

    async def mark_inactive(self) -> None:
        """Mark the game as inactive."""
        async with self.lock:
            self.activity_state = ActivityState.INACTIVE

    async def mark_started(self) -> None:
        """Mark the game as started."""
        async with self.lock:
            self.game_state = GameState.PLAYING
            self.last_active_date = pendulum.now()
            self.started_date = pendulum.now()
            for _ in range(0, self.players - len(self.game_players)):
                self._mark_joined_programmatic()  # fill in remaining players as necessary
            for handle in self.game_players:
                self.game_players[handle] = attr.evolve(self.game_players[handle], state=PlayerState.PLAYING)

    async def mark_completed(self, comment: Optional[str]) -> None:
        """Mark the game as completed."""
        async with self.lock:
            self.completed_date = pendulum.now()
            self.game_state = GameState.COMPLETED
            self.completed_comment = comment
            for handle in self.game_players:
                self.game_players[handle] = attr.evolve(self.game_players[handle], state=PlayerState.FINISHED)

    async def mark_cancelled(self, reason: CancelledReason, comment: Optional[str] = None) -> None:
        """Mark the game as cancelled."""
        async with self.lock:
            self.completed_date = pendulum.now()
            self.game_state = GameState.CANCELLED
            self.cancelled_reason = reason
            self.completed_comment = comment
            for handle in self.game_players:
                self.game_players[handle] = attr.evolve(self.game_players[handle], state=PlayerState.FINISHED)

    async def mark_joined(self, player: TrackedPlayer) -> None:
        """Mark that a player has joined a game."""
        async with self.lock:
            player_type = PlayerType.HUMAN
            player_state = PlayerState.JOINED
            player_color = self._assign_color()
            self.game_players[player.handle] = GamePlayer(player.handle, player_color, player_type, player_state)

    async def mark_quit(self, player: TrackedPlayer) -> None:
        """Mark that the player has quit a game."""
        async with self.lock:
            if self.game_state == GameState.ADVERTISED:
                del self.game_players[player.handle]  # if the game hasn't started, just remove them
            else:
                self.game_players[player.handle] = attr.evolve(self.game_players[player.handle], state=PlayerState.QUIT)

    # pylint: disable=unused-argument
    async def get_player_view(self, player: TrackedPlayer) -> PlayerView:
        """Get the player's view of the game state."""
        # TODO: remove pylint unused-argument once this is implemented
        # TODO: implement get_player_view() once we have a way to manage game state (within a lock, presumably)
        return PlayerView(player=Player(PlayerColor.RED, [], []), opponents={})

    # pylint: disable=unused-argument
    async def execute_move(self, player: TrackedPlayer, move_id: str) -> Tuple[bool, Optional[str]]:
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


_LOCK = asyncio.Lock()
_GAME_MAP: Dict[str, TrackedGame] = {}
_PLAYER_MAP: Dict[str, TrackedPlayer] = {}
_HANDLE_MAP: Dict[str, str] = {}

# TODO: requirements for this function come from the Advertise Game request
# TODO: decide whether I need to validate arguments (min/max players, etc.) or interface validation is enough
async def track_game(player: TrackedPlayer, advertised: AdvertiseGameContext) -> TrackedGame:
    """Track a newly-advertised game, returning the tracked game."""
    async with _LOCK:
        game_id = "%s" % uuid4()
        _GAME_MAP[game_id] = TrackedGame.for_context(player.handle, game_id, advertised)
        return _GAME_MAP[game_id]


async def delete_game(game: TrackedGame) -> None:
    """Delete a tracked game, so it is no longer tracked."""
    async with _LOCK:
        if game.game_id in _GAME_MAP:
            del _GAME_MAP[game.game_id]


async def lookup_game(game_id: Optional[str] = None, player: Optional[TrackedPlayer] = None) -> Optional[TrackedGame]:
    """Look up a game by id, returning None if the game is not found."""
    if game_id:
        async with _LOCK:
            return _GAME_MAP[game_id] if game_id in _GAME_MAP else None
    elif player:
        async with player.lock:
            game_id = player.game_id
        return await lookup_game(game_id=game_id)
    else:
        return None


async def lookup_all_games() -> List[TrackedGame]:
    """Return a list of all tracked games."""
    async with _LOCK:
        return list(_GAME_MAP.values())


async def lookup_in_progress_games() -> List[TrackedGame]:
    """Return a list of all in-progress games."""
    return [game for game in await lookup_all_games() if game.is_in_progress()]


async def lookup_game_players(game: TrackedGame) -> List[TrackedPlayer]:
    """Lookup the players that are currently playing a game."""
    async with game.lock:
        handles = [player.handle for player in game.game_players.values() if player.player_type == PlayerType.HUMAN]
    players = [await lookup_player(handle=handle) for handle in handles]
    return [player for player in players if player is not None]


# TODO: requirements for this function come from the List Available Games request and the Available Games event
# TODO: I don't think we implement everything yet (i.e. should only show games that haven't been started, etc.)
async def lookup_available_games(player: TrackedPlayer) -> List[TrackedGame]:
    """Return a list of games the passed-in player may join."""
    games = await lookup_all_games()
    return [game for game in games if game.is_available(player)]


# TODO: requirements for this function come from the Register Player request
async def track_player(websocket: WebSocketServerProtocol, handle: str) -> TrackedPlayer:
    """Track a newly-registered player, the tracked player."""
    async with _LOCK:
        if handle in _HANDLE_MAP:
            raise ProcessingError(FailureReason.DUPLICATE_USER)
        player_id = "%s" % uuid4()
        _PLAYER_MAP[player_id] = TrackedPlayer.for_context(player_id, websocket, handle)
        _HANDLE_MAP[handle] = player_id
        return _PLAYER_MAP[player_id]


async def delete_player(player: TrackedPlayer) -> None:
    """Delete a tracked player, so it is no longer tracked."""
    async with _LOCK:
        if player.handle in _HANDLE_MAP:
            del _HANDLE_MAP[player.handle]
        if player.player_id in _PLAYER_MAP:
            del _PLAYER_MAP[player.player_id]


async def lookup_player(player_id: Optional[str] = None, handle: Optional[str] = None) -> Optional[TrackedPlayer]:
    """Look up a player by either player id or handle."""
    if player_id:
        async with _LOCK:
            return _PLAYER_MAP[player_id] if player_id in _PLAYER_MAP else None
    elif handle:
        async with _LOCK:
            player_id = _HANDLE_MAP[handle] if handle in _HANDLE_MAP else None
        return await lookup_player(player_id=player_id)
    else:
        return None


async def lookup_all_players() -> List[TrackedPlayer]:
    """Return a list of all tracked players."""
    async with _LOCK:
        return list(_PLAYER_MAP.values())


async def lookup_websocket(
    player: Optional[TrackedPlayer] = None, player_id: Optional[str] = None, handle: Optional[str] = None
) -> Optional[WebSocketServerProtocol]:
    """Look up the websocket for a player, player id or handle, returning None for an unknown or disconnected player."""
    if player:
        async with player.lock:
            return player.websocket
    elif player_id:
        player = await lookup_player(player_id=player_id)
        if not player:
            return None
        async with player.lock:
            return player.websocket
    elif handle:
        player = await lookup_player(handle=handle)
        if not player:
            return None
        async with player.lock:
            return player.websocket
    else:
        return None


async def lookup_websockets(
    players: Optional[List[TrackedPlayer]], player_ids: Optional[List[str]] = None, handles: Optional[List[str]] = None
) -> List[WebSocketServerProtocol]:
    """Look up the websockets for a list of players, player ids and/or handles, for players that are connected."""
    websockets = set()
    if players:
        websockets.update([await lookup_websocket(player=player) for player in players])
    if player_ids:
        websockets.update([await lookup_websocket(player_id=player_id) for player_id in player_ids])
    if handles:
        websockets.update([await lookup_websocket(handle=handle) for handle in handles])
    return list([websocket for websocket in websockets if websocket is not None])


async def lookup_all_websockets() -> List[WebSocketServerProtocol]:
    """Return a list of websockets for all tracked players."""
    return await lookup_websockets(players=await lookup_all_players())


async def lookup_player_for_websocket(websocket: WebSocketServerProtocol) -> Optional[TrackedPlayer]:
    """Look up the player associated with a websocket, if any."""
    # We can't track this in a map because it's not a constant identifying aspect of a player
    for player in await lookup_all_players():
        if websocket is await lookup_websocket(player=player):
            return player
    return None
