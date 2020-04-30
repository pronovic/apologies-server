# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import

"""
Code to manage application state.
"""

from __future__ import annotations  # see: https://stackoverflow.com/a/33533514/2907667

import asyncio
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

import attr
import pendulum
from apologies.game import GameMode, PlayerColor, PlayerView
from pendulum.datetime import DateTime
from websockets import WebSocketServerProtocol

from .interface import *
from .util import copydate

__all__ = [
    "TrackedPlayer",
    "TrackedGame",
    "track_game",
    "track_player",
    "delete_game",
    "disconnect_player",
    "delete_player",
    "lookup_websocket",
    "lookup_all_websockets",
    "lookup_websockets",
    "lookup_available_games",
    "lookup_game",
    "lookup_connected_players",
    "lookup_player",
    "lookup_player_handle",
    "lookup_player_id",
    "lookup_player_game_id",
    "lookup_game_completion",
    "lookup_game_player_handles",
    "lookup_game_activity",
    "lookup_game_state",
    "lookup_game_players",
    "lookup_player_activity",
    "mark_game_active",
    "mark_game_started",
    "mark_game_idle",
    "mark_game_completed",
    "mark_game_cancelled",
    "mark_player_active",
    "mark_player_idle",
    "mark_player_joined",
    "mark_player_quit",
    "mark_player_disconnected",
]


@attr.s
class TrackedPlayer:
    """
    The state that is tracked for a player within the game server.
    
    Any code that wishes to read or write attributes on a TrackedPlayer object 
    must acquire the object's asyncio lock first, or else call one of the
    helper methods that takes care of the lock.
    """

    player_id = attr.ib(type=str, repr=False)  # this is a secret, so we don't want it printed or logged
    websocket = attr.ib(type=Optional[WebSocketServerProtocol])
    handle = attr.ib(type=str)
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
    
    Any code that wishes to read or write attributes on a TrackedGame object 
    must acquire the object's asyncio lock first, or else call one of the
    helper methods that takes care of the lock.
    """

    game_id = attr.ib(type=str)
    advertiser_handle = attr.ib(type=str)
    name = attr.ib(type=str)
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
    color_map = attr.ib(type=Dict[PlayerColor, str])
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

    @color_map.default
    def _default_color_map(self) -> Dict[PlayerColor, str]:
        return {}

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

    async def is_advertised(self, handle: str) -> bool:
        """Whether the game is currently being advertised to be joined by the handle."""
        async with self.lock:
            return self.game_state == GameState.ADVERTISED and (
                self.visibility == Visibility.PUBLIC or handle in self.invited_handles
            )

    async def is_viable(self) -> bool:
        """Whether the game is viable."""
        return True  # TODO: I have no idea how I am going to do this; it has something to do with number of remaining human players

    async def mark_active(self) -> None:
        """Mark the game as active."""
        async with self.lock:
            self.activity_state = ActivityState.ACTIVE
            self.last_active_date = pendulum.now()

    async def mark_idle(self) -> List[str]:
        """Mark the game as idle, returning list of handles to notify."""
        async with self.lock:
            self.activity_state = ActivityState.IDLE
            return self.joined_handles

    async def mark_inactive(self) -> List[str]:
        """Mark the game as inactive, returning list of handles to notify."""
        async with self.lock:
            self.activity_state = ActivityState.INACTIVE
            return self.joined_handles

    async def mark_joined(self, handle: str) -> List[str]:
        """Mark that the player has joined a game, returning list of handles to notify."""
        async with self.lock:
            self.joined_handles.append(handle)
            return self.joined_handles

    async def mark_quit(self, handle: str) -> List[str]:
        """Mark that the player has quit a game, returning list of handles to notify."""
        async with self.lock:
            if handle in self.joined_handles:
                self.joined_handles.remove(handle)
            return self.joined_handles

    async def mark_started(self) -> List[str]:
        """Mark the game as started, returning list of handles to notify."""
        async with self.lock:
            self.game_state = GameState.PLAYING
            self.last_active_date = pendulum.now()
            self.started_date = pendulum.now()
            # TODO: fill in the color map - not sure how I deal with this for programmatic players
            #       I'm missing everything to deal properly with programmatic playrs.  Are they joined?  Or something else?
            #       I don't think I want them in the joined handles, because that's for notification, but at the same
            #       time I need to deal with it somehow - otherwise the list of players makes no sense and doesn't include them.
            return self.joined_handles

    async def mark_completed(self, comment: Optional[str]) -> List[str]:
        """Mark the game as completed, returning list of handles to notify."""
        async with self.lock:
            self.game_state = GameState.COMPLETED
            self.completed_date = pendulum.now()
            self.completed_comment = comment
            return self.joined_handles

    async def mark_cancelled(self, reason: CancelledReason, comment: Optional[str] = None) -> List[str]:
        """Mark the game as cancelled, returning list of handles to notify."""
        async with self.lock:
            self.game_state = GameState.CANCELLED
            self.completed_date = pendulum.now()
            self.cancelled_reason = reason
            self.completed_comment = comment
            return self.joined_handles

    async def to_available_game(self) -> AvailableGame:
        """Convert this TrackedGame to an AvailableGame."""
        async with self.lock:
            return AvailableGame(
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


async def track_game(player_id: str, advertised: AdvertiseGameContext) -> TrackedGame:
    """Track a newly-advertised game, returning the tracked game."""
    player = await lookup_player(player_id)
    if not player:
        raise ProcessingError(FailureReason.UNKNOWN_PLAYER)
    async with player.lock:
        handle = player.handle
    async with _LOCK:
        game_id = "%s" % uuid4()
        _GAME_MAP[game_id] = TrackedGame.for_context(handle, game_id, advertised)
        return _GAME_MAP[game_id]


async def track_player(websocket: WebSocketServerProtocol, handle: str) -> str:
    """Track a newly-registered player, returning the player id."""
    async with _LOCK:
        if handle in _HANDLE_MAP:
            raise ProcessingError(FailureReason.DUPLICATE_USER)
        player_id = "%s" % uuid4()
        _PLAYER_MAP[player_id] = TrackedPlayer.for_context(player_id, websocket, handle)
        _HANDLE_MAP[handle] = player_id
        return player_id


async def delete_game(game_id: str) -> None:
    """Delete a tracked game, so it is no longer tracked."""
    async with _LOCK:
        if game_id in _GAME_MAP:
            del _GAME_MAP[game_id]


# noinspection PyBroadException
async def disconnect_player(player_id: str) -> None:
    """Disconnect a player's websocket."""
    player = await lookup_player(player_id)
    if not player:
        return
    async with player.lock:
        websocket = player.websocket
    await player.mark_disconnected()
    if websocket:
        try:
            await websocket.close()
        except:  # pylint: disable=bare-except
            pass


async def delete_player(player_id: str) -> None:
    """Delete a tracked player, so it is no longer tracked."""
    async with _LOCK:
        if player_id in _PLAYER_MAP:
            player = _PLAYER_MAP[player_id]
            async with player.lock:
                handle = player.handle
            if handle in _HANDLE_MAP:
                del _HANDLE_MAP[handle]
            del _PLAYER_MAP[player_id]


async def lookup_websocket(player_id: Optional[str] = None, handle: Optional[str] = None) -> Optional[WebSocketServerProtocol]:
    """Look up the websocket for a player id or handle, returning None if the player can't be found or is disconnected."""
    if player_id:
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


async def lookup_all_websockets() -> List[WebSocketServerProtocol]:
    """Return a list of websockets for all connected players."""
    async with _LOCK:
        return [player.websocket for player in _PLAYER_MAP.values() if player.websocket is not None]


async def lookup_websockets(
    player_ids: Optional[List[str]] = None, handles: Optional[List[str]] = None
) -> List[WebSocketServerProtocol]:
    """Look up the websockets for a list of player ids and/or handles, for players that can be found and are connected."""
    websockets = set()
    if player_ids:
        websockets.update([await lookup_websocket(player_id=player_id) for player_id in player_ids])
    if handles:
        websockets.update([await lookup_websocket(handle=handle) for handle in handles])
    return list([websocket for websocket in websockets if websocket is not None])


async def lookup_available_games(player_id: str) -> List[TrackedGame]:
    """Return a list of all advertised games."""
    handle = await lookup_player_handle(player_id)
    async with _LOCK:
        return [] if not handle else [game for game in _GAME_MAP.values() if game.is_advertised(handle)]


async def lookup_game(game_id: str) -> Optional[TrackedGame]:
    """Look up a game by id."""
    async with _LOCK:
        return _GAME_MAP[game_id] if game_id in _GAME_MAP else None


async def lookup_connected_players() -> List[TrackedPlayer]:
    """Return a list of all active players."""
    async with _LOCK:
        return [player for player in _PLAYER_MAP.values() if player.is_connected()]


async def lookup_player(player_id: Optional[str] = None, handle: Optional[str] = None) -> Optional[TrackedPlayer]:
    """Look up a player by either player id or handle."""
    async with _LOCK:
        if player_id:
            return _PLAYER_MAP[player_id] if player_id in _PLAYER_MAP else None
        elif handle:
            if handle not in _HANDLE_MAP:
                raise ProcessingError(FailureReason.UNKNOWN_PLAYER)
            player_id = _HANDLE_MAP[handle]
            return _PLAYER_MAP[player_id] if player_id in _PLAYER_MAP else None
        else:
            return None


async def lookup_player_handle(player_id: str) -> Optional[str]:
    """Lookup the handle associated with a player id."""
    player = await lookup_player(player_id=player_id)
    if not player:
        return None
    else:
        with player.lock:
            return player.handle


async def lookup_player_id(handle: str) -> Optional[str]:
    """Lookup the player id associated with a handle."""
    player = await lookup_player(handle=handle)
    if not player:
        return None
    else:
        with player.lock:
            return player.player_id


async def lookup_player_game_id(player_id: str) -> Optional[str]:  # TODO: are there other places this can be used?
    """Lookup the game id for the player, if any."""
    player = await lookup_player(player_id=player_id)
    if not player:
        return None
    else:
        with player.lock:
            return player.game_id


async def lookup_game_completion() -> Dict[str, DateTime]:
    """Look up the completed date for all completed games."""
    result = {}
    async with _LOCK:
        for game in _GAME_MAP.values():
            async with game.lock:
                if game.game_state == GameState.COMPLETED:
                    result[game.game_id] = copydate(game.completed_date)  # type: ignore
    return result


async def lookup_game_player_handles(game_id: str) -> List[str]:
    """Lookup handles for players that have joined a game, or empty if game can't be found."""
    game = await lookup_game(game_id)
    if not game:
        return []
    else:
        async with game.lock:
            return game.joined_handles


async def lookup_game_activity() -> Dict[str, DateTime]:
    """Look up the last active date for all games."""
    result = {}
    async with _LOCK:
        for game in _GAME_MAP.values():
            async with game.lock:
                result[game.game_id] = copydate(game.last_active_date)
    return result


# TODO: remove unused-argument
async def lookup_game_players(game_id: str) -> Dict[PlayerColor, GamePlayer]:  # pylint: disable=unused-argument
    """Look up the players associated with a game."""
    return {}  # TODO: implement this


# TODO: remove unused-argument
async def lookup_game_state(game_id: str) -> Dict[str, PlayerView]:  # pylint: disable=unused-argument
    """Look up the game state by player, a map from player handle to PlayerView."""
    return {}  # TODO: implement this


async def lookup_player_activity() -> Dict[str, Tuple[DateTime, ConnectionState]]:
    """Look up the last active date and connection state for all players."""
    result = {}
    async with _LOCK:
        for player in _PLAYER_MAP.values():
            async with player.lock:
                result[player.player_id] = (copydate(player.last_active_date), player.connection_state)
    return result


async def mark_game_active(game_id: str) -> TrackedGame:
    """Mark that a game is active, and return the up-to-date game."""
    game = await lookup_game(game_id=game_id)
    if not game:
        raise ProcessingError(FailureReason.UNKNOWN_GAME)
    await game.mark_active()
    return game


async def mark_game_started(game_id: str) -> List[str]:
    """Mark that a game is started, returning list of handles to notify."""
    game = await lookup_game(game_id=game_id)
    if not game:
        raise ProcessingError(FailureReason.UNKNOWN_GAME)
    return await game.mark_started()


async def mark_game_idle(game_id: str) -> List[str]:
    """Mark that a game is idle, returning list of handles to notify."""
    game = await lookup_game(game_id=game_id)
    if not game:
        raise ProcessingError(FailureReason.UNKNOWN_GAME)
    return await game.mark_idle()


async def mark_game_completed(game_id: str, comment: Optional[str] = None) -> List[str]:
    """Mark that a game is completed, returning list of handles to notify."""
    game = await lookup_game(game_id=game_id)
    if not game:
        raise ProcessingError(FailureReason.UNKNOWN_GAME)
    return await game.mark_completed(comment)


async def mark_game_cancelled(game_id: str, reason: CancelledReason, comment: Optional[str] = None) -> List[str]:
    """Mark that a game is cancelled, returning list of handles to notify."""
    game = await lookup_game(game_id=game_id)
    if not game:
        raise ProcessingError(FailureReason.UNKNOWN_GAME)
    handles = await game.mark_cancelled(reason, comment)
    for handle in handles:
        player = await lookup_player(handle=handle)
        if player:
            await player.mark_quit()
    return handles


async def mark_player_active(player_id: str) -> TrackedPlayer:
    """Mark that a player is active, and return the up-to-date player."""
    player = await lookup_player(player_id=player_id)
    if not player:
        raise ProcessingError(FailureReason.UNKNOWN_PLAYER)
    await player.mark_active()
    return player


async def mark_player_idle(player_id: str) -> None:
    """Mark that a player is idle."""
    player = await lookup_player(player_id)
    if not player:
        raise ProcessingError(FailureReason.UNKNOWN_PLAYER)
    await player.mark_idle()


async def mark_player_joined(player_id: str, game_id: str) -> None:
    """Mark that a player has joined a game."""
    player = await lookup_player(player_id=player_id)
    if not player:
        raise ProcessingError(FailureReason.UNKNOWN_PLAYER)
    async with player.lock:
        handle = player.handle
    game = await lookup_game(game_id=game_id)
    if not game:
        raise ProcessingError(FailureReason.UNKNOWN_GAME)
    await player.mark_joined(game_id)
    await game.mark_joined(handle)


async def mark_player_quit(player_id: str) -> Tuple[str, Optional[str], bool]:
    """Mark that a player has quit any game they are playing."""
    player = await lookup_player(player_id=player_id)  # TODO: what if player does not exist?
    if not player:
        raise ProcessingError(FailureReason.UNKNOWN_PLAYER)
    async with player.lock:
        handle = player.handle
        game_id = player.game_id
    if not game_id:
        return handle, None, False
    else:
        game = await lookup_game(game_id=game_id)  # TODO: what if there is no game?
        if not game:
            raise ProcessingError(FailureReason.UNKNOWN_GAME)
        await player.mark_quit()
        await game.mark_quit(handle)
        viable = await game.is_viable()  # TODO: what if there is no game? is this true?  or false?
        return handle, game_id, viable


async def mark_player_disconnected(player_id: str) -> Tuple[str, Optional[str], bool]:
    """Mark that a player has been disconnected, quitting any game they are playing."""
    player = await lookup_player(player_id=player_id)  # TODO: what if player does not exist
    if not player:
        raise ProcessingError(FailureReason.UNKNOWN_PLAYER)
    async with player.lock:
        handle = player.handle
        game_id = player.game_id
    if not game_id:
        return handle, None, False
    game = await lookup_game(game_id=game_id)  # TODO: what if there is no game?
    if not game:
        raise ProcessingError(FailureReason.UNKNOWN_GAME)
    await player.mark_disconnected()
    await game.mark_quit(handle)
    viable = await game.is_viable()  # TODO: what if there is no game? is this true?  or false?
    return handle, game_id, viable
