# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import

"""
Code to manage application state.
"""

from __future__ import annotations  # see: https://stackoverflow.com/a/33533514/2907667

import asyncio
from typing import Dict, List, Optional, Sequence, Tuple
from uuid import uuid4

import attr
import pendulum
from apologies.game import GameMode
from pendulum.datetime import DateTime
from websockets import WebSocketServerProtocol

from .interface import *
from .util import copydate


@attr.s
class TrackedPlayer:
    """
    The state that is tracked for a player within the game server.
    
    Any code that wishes to read or write attributes on a TrackedPlayer object 
    must acquire the object's asyncio lock first, or else call one of the
    helper methods that takes care of the lock.
    """

    player_id = attr.ib(type=str, repr=False)  # this is a secret, so we don't want it printed or logged
    websocket = attr.ib(type=WebSocketServerProtocol)
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

    async def mark_active(self) -> None:
        """Mark the player as active."""
        async with self.lock:
            self.last_active_date = pendulum.now()
            self.activity_state = ActivityState.ACTIVE
            self.connection_state = ConnectionState.CONNECTED


# pylint: disable=too-many-instance-attributes
@attr.s
class TrackedGame:
    """
    The state that is tracked for a game within the game server.
    
    Any code that wishes to read or write attributes on a TrackedGame object 
    must acquire the object's asyncio lock first, or else call one of the
    helper methods that takes care of the lock.
    """

    player_id = attr.ib(type=str)
    game_id = attr.ib(type=str)
    name = attr.ib(type=str)
    mode = attr.ib(type=GameMode)
    players = attr.ib(type=int)
    visibility = attr.ib(type=Visibility)
    invited_handles = attr.ib(type=Sequence[str])
    advertised_date = attr.ib(type=DateTime)
    last_active_date = attr.ib(type=DateTime)
    started_date = attr.ib(type=Optional[DateTime], default=None)
    completed_date = attr.ib(type=Optional[DateTime], default=None)
    game_state = attr.ib(type=GameState, default=GameState.ADVERTISED)
    activity_state = attr.ib(type=ActivityState, default=ActivityState.ACTIVE)
    completed_reason = attr.ib(type=Optional[str], default=None)
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

    @staticmethod
    def for_context(player_id: str, game_id: str, context: AdvertiseGameContext) -> TrackedGame:
        """Create a tracked game based on provided context."""
        return TrackedGame(
            game_id=game_id,
            player_id=player_id,
            name=context.name,
            mode=context.mode,
            players=context.players,
            visibility=context.visibility,
            invited_handles=context.invited_handles[:],
        )

    async def mark_active(self) -> None:
        """Mark the game as active."""
        async with self.lock:
            self.activity_state = ActivityState.ACTIVE
            self.last_active_date = pendulum.now()

    async def mark_started(self) -> None:
        """Mark the game as started"""
        async with self.lock:
            self.game_state = GameState.PLAYING
            self.last_active_date = pendulum.now()
            self.started_date = pendulum.now()

    async def mark_completed(self, reason: str) -> None:
        """Mark the game as completed."""
        async with self.lock:
            self.game_state = GameState.COMPLETED
            self.last_active_date = pendulum.now()
            self.completed_date = pendulum.now()
            self.completed_reason = reason


_LOCK = asyncio.Lock()
_GAME_MAP: Dict[str, TrackedGame] = {}
_PLAYER_MAP: Dict[str, TrackedPlayer] = {}
_HANDLE_MAP: Dict[str, str] = {}


async def track_game(player: TrackedPlayer, context: AdvertiseGameContext) -> TrackedGame:
    """Track a newly-advertised game, returning the tracked game."""
    async with player.lock:
        player_id = player.player_id
    async with _LOCK:
        game_id = "%s" % uuid4()
        _GAME_MAP[game_id] = TrackedGame.for_context(player_id, game_id, context)
        return _GAME_MAP[game_id]


async def track_player(websocket: WebSocketServerProtocol, handle: str) -> TrackedPlayer:
    """Track a newly-registered player, returning the tracked player."""
    async with _LOCK:
        if handle in _HANDLE_MAP:
            raise ProcessingError(FailureReason.DUPLICATE_USER)
        player_id = "%s" % uuid4()
        _PLAYER_MAP[player_id] = TrackedPlayer.for_context(player_id, websocket, handle)
        _HANDLE_MAP[handle] = player_id
        return _PLAYER_MAP[player_id]


async def delete_game(game_id: str) -> None:
    """Delete a tracked game, so it is no longer tracked."""
    async with _LOCK:
        if game_id in _GAME_MAP:
            del _GAME_MAP[game_id]


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


async def lookup_game(game_id: str) -> TrackedGame:
    """Look up a game by id."""
    async with _LOCK:
        if game_id not in _GAME_MAP:
            raise ProcessingError(FailureReason.UNKNOWN_GAME)
        return _GAME_MAP[game_id]


async def lookup_player(player_id: Optional[str] = None, handle: Optional[str] = None) -> TrackedPlayer:
    """Look up a player by either player id or handle."""
    async with _LOCK:
        if player_id:
            if player_id not in _PLAYER_MAP:
                raise ProcessingError(FailureReason.UNKNOWN_PLAYER)
            return _PLAYER_MAP[player_id]
        elif handle:
            if handle not in _HANDLE_MAP:
                raise ProcessingError(FailureReason.UNKNOWN_PLAYER)
            player_id = _HANDLE_MAP[handle]
            if player_id not in _PLAYER_MAP:
                raise ProcessingError(FailureReason.INTERNAL_ERROR)
            return _PLAYER_MAP[player_id]
        else:
            raise ProcessingError(FailureReason.INTERNAL_ERROR)


async def lookup_websocket(player_id: Optional[str] = None, handle: Optional[str] = None) -> WebSocketServerProtocol:
    """Look up the websocket for a player id or handle."""
    if player_id:
        player = await lookup_player(player_id=player_id)
        async with player.lock:
            return player.websocket
    elif handle:
        player = await lookup_player(handle=handle)
        with player.lock:
            return player.websocket
    else:
        raise ProcessingError(FailureReason.INTERNAL_ERROR)


async def lookup_websockets(
    player_ids: Optional[Sequence[str]] = None, handles: Optional[Sequence[str]] = None
) -> List[WebSocketServerProtocol]:
    """Look up the websockets for a list of player ids and/or handles."""
    websockets = []
    if player_ids:
        websockets += [await lookup_websocket(player_id) for player_id in player_ids]
    elif handles:
        websockets += [await lookup_websocket(handle) for handle in handles]
    return websockets


async def lookup_game_completion() -> Dict[str, DateTime]:
    """Look up the completed date for all completed games."""
    result = {}
    async with _LOCK:
        for game in _GAME_MAP.values():
            async with game.lock:
                if game.game_state == GameState.COMPLETED:
                    result[game.game_id] = copydate(game.completed_date)  # type: ignore
    return result


async def lookup_game_activity() -> Dict[str, DateTime]:
    """Look up the last active date for all games."""
    result = {}
    async with _LOCK:
        for game in _GAME_MAP.values():
            async with game.lock:
                result[game.game_id] = copydate(game.last_active_date)
    return result


async def lookup_player_activity() -> Dict[str, Tuple[DateTime, ConnectionState]]:
    """Look up the last active date for all players."""
    result = {}
    async with _LOCK:
        for player in _PLAYER_MAP.values():
            async with player.lock:
                result[player.player_id] = (copydate(player.last_active_date), player.connection_state)
    return result


async def mark_game_active(game_id: str) -> TrackedGame:
    """Mark that a game is active, and return the up-to-date game."""
    game = await lookup_game(game_id=game_id)
    await game.mark_active()
    return game


async def mark_game_started(game_id: str) -> None:
    """Mark that a game is completed."""
    game = await lookup_game(game_id=game_id)
    await game.mark_started()


async def mark_game_completed(game_id: str, reason: str) -> None:
    """Mark that a game is completed, with a reason."""
    game = await lookup_game(game_id=game_id)
    await game.mark_completed(reason)


async def mark_player_active(player_id: str) -> TrackedPlayer:
    """Mark that a player is active, and return the up-to-date player."""
    player = await lookup_player(player_id=player_id)
    await player.mark_active()
    return player
