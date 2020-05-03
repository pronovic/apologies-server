# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import

# TODO: this needs unit tests, but only once the code is better understood and cleaned up
# TODO: need to go through and make sure all methods and functions are used and have a non-duplicitive purpose
# TODO: I feel like there is way too much business logic in here.  I think a lot of the functions
#       are really only used one place, and that business logic can be pulled out into the associated
#       event function instead.  It's still ok for TrackedPlayer and TrackedGame to have things like
#       mark_started() or whatever, but composing which combinations of things... that feels like it's
#       in the wrong place.

"""
Code to manage application state.
"""

from __future__ import annotations  # see: https://stackoverflow.com/a/33533514/2907667

import asyncio
from typing import Dict, List, Optional
from uuid import uuid4

import attr
import pendulum
from apologies.game import GameMode
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

    async def mark_disconnected(self) -> None:
        """Mark the player as disconnected."""
        async with self.lock:
            self.websocket = None
            self.game_id = None  # if they disconnect, it's like quitting
            self.activity_state = ActivityState.IDLE
            self.connection_state = ConnectionState.DISCONNECTED

    async def mark_joined(self, game_id: str) -> None:
        """Mark that the player has joined a game."""
        async with self.lock:
            self.game_id = game_id
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


# pylint: disable=too-many-instance-attributes
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
    mode = attr.ib(type=GameMode)
    players = attr.ib(type=int)
    visibility = attr.ib(type=Visibility)
    invited_handles = attr.ib(type=List[str])
    advertised_date = attr.ib(type=DateTime)
    last_active_date = attr.ib(type=DateTime)
    started_date = attr.ib(type=Optional[DateTime], default=None)
    completed_date = attr.ib(type=Optional[DateTime], default=None)
    game_state = attr.ib(type=GameState, default=GameState.ADVERTISED)
    activity_state = attr.ib(type=ActivityState, default=ActivityState.ACTIVE)
    cancelled_reason = attr.ib(type=Optional[CancelledReason], default=None)
    completed_comment = attr.ib(type=Optional[str], default=None)
    joined_handles = attr.ib(type=List[str])
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

    @joined_handles.default
    def _default_joined_handles(self) -> List[str]:
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

    async def is_available(self, player: TrackedPlayer) -> bool:
        """Whether the game is available to be joined by the passed-in player."""
        async with self.lock:
            return self.game_state == GameState.ADVERTISED and (
                self.visibility == Visibility.PUBLIC or player.handle in self.invited_handles
            )

    async def is_viable(self) -> bool:
        """Whether the game is viable."""
        # TODO: I have no idea how I am going to do this; it has something to do with number of remaining human players
        #       I think there's some additional logic or state somewhere to track human vs. programmatic players?
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

    async def mark_joined(self, handle: str) -> None:
        """Mark that the player has joined a game."""
        async with self.lock:
            self.joined_handles.append(handle)

    async def mark_quit(self, handle: str) -> None:
        """Mark that the player has quit a game."""
        async with self.lock:
            if handle in self.joined_handles:
                self.joined_handles.remove(handle)

    async def mark_started(self) -> None:
        """Mark the game as started."""
        # TODO: something has to happen here to assign programmatic players to any empty slots
        async with self.lock:
            self.game_state = GameState.PLAYING
            self.last_active_date = pendulum.now()
            self.started_date = pendulum.now()

    async def mark_completed(self, comment: Optional[str]) -> None:
        """Mark the game as completed."""
        async with self.lock:
            self.joined_handles = []
            self.completed_date = pendulum.now()
            self.game_state = GameState.COMPLETED
            self.completed_comment = comment

    async def mark_cancelled(self, reason: CancelledReason, comment: Optional[str] = None) -> None:
        """Mark the game as cancelled."""
        async with self.lock:
            self.joined_handles = []
            self.completed_date = pendulum.now()
            self.game_state = GameState.CANCELLED
            self.cancelled_reason = reason
            self.completed_comment = comment

    async def to_advertised_game(self) -> AdvertisedGame:
        """Convert this TrackedGame to an AdvertisedGame."""
        async with self.lock:
            return AdvertisedGame(
                game_id=self.game_id,
                name=self.name,
                mode=self.mode,
                advertiser_handle=self.advertiser_handle,
                players=self.players,
                available=self.players - len(self.joined_handles),
                visibility=self.visibility,
                invited_handles=self.invited_handles,
            )


_LOCK = asyncio.Lock()
_GAME_MAP: Dict[str, TrackedGame] = {}
_PLAYER_MAP: Dict[str, TrackedPlayer] = {}
_HANDLE_MAP: Dict[str, str] = {}


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


async def lookup_game_players(game: TrackedGame) -> List[TrackedPlayer]:
    """Lookup the players that are currently playing a game."""
    # TODO: need to ensure that joined_handles only includes human players, connected to a websocket
    #       not sure where/how I'm going to track the programmatic players.  needs some more state?
    async with game.lock:
        handles = game.joined_handles[:]
    players = [await lookup_player(handle=handle) for handle in handles]
    return [player for player in players if player is not None]


async def lookup_available_games(player: TrackedPlayer) -> List[TrackedGame]:
    """Return a list of games the passed-in player may join."""
    games = await lookup_all_games()
    return [game for game in games if game.is_available(player)]


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
