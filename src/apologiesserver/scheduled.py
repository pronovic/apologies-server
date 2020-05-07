# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import

# TODO: should be ok to start unit testing this, I think the structure is final

"""Coroutines to handle scheduled tasks, executed on a periodic basis."""

import logging
from typing import List, Optional, Tuple

import pendulum
from pendulum.datetime import DateTime
from periodic import Periodic

from .config import config
from .event import *
from .interface import ConnectionState, GameState
from .state import TrackedGame, TrackedPlayer, lookup_all_games, lookup_all_players

log = logging.getLogger("apologies.scheduled")


async def _lookup_player_activity() -> List[Tuple[TrackedPlayer, DateTime, ConnectionState]]:
    """Look up the last active date and connection state for all players."""
    result: List[Tuple[TrackedPlayer, DateTime, ConnectionState]] = []
    for player in await lookup_all_players():
        async with player.lock:
            result.append((player, player.last_active_date, player.connection_state))
    return result


async def _lookup_game_activity() -> List[Tuple[TrackedGame, DateTime]]:
    """Look up the last active date for all games."""
    result: List[Tuple[TrackedGame, DateTime]] = []
    for game in await lookup_all_games():
        async with game.lock:
            result.append((game, game.last_active_date))
    return result


async def _lookup_game_completion() -> List[Tuple[TrackedGame, Optional[DateTime]]]:
    """Look up the completed date for all completed games."""
    result: List[Tuple[TrackedGame, Optional[DateTime]]] = []
    for game in await lookup_all_games():
        async with game.lock:
            if game.game_state == GameState.COMPLETED:
                result.append((game, game.completed_date))
    return result


async def handle_idle_player_check_task() -> None:
    """Execute the Idle Player Check task."""
    log.info("SCHEDULED[Idle Player Check]")
    idle = 0
    inactive = 0
    now = pendulum.now()
    for (player, last_active_date, connection_state) in await _lookup_player_activity():
        disconnected = connection_state == ConnectionState.DISCONNECTED
        if now.diff(last_active_date).in_minutes > config().player_inactive_thresh_min:
            inactive += 1
            await handle_player_inactive_event(player)
        elif now.diff(last_active_date).in_minutes > config().player_idle_thresh_min:
            if disconnected:
                inactive += 1
                await handle_player_inactive_event(player)
            else:
                idle += 1
                await handle_player_idle_event(player)
    log.debug("Idle player check completed, found %d idle and %d inactive players", idle, inactive)


async def handle_idle_game_check_task() -> None:
    """Execute the Idle Game Check task."""
    log.info("SCHEDULED[Idle Game Check]")
    idle = 0
    inactive = 0
    now = pendulum.now()
    for (game, last_active_date) in await _lookup_game_activity():
        if now.diff(last_active_date).in_minutes > config().game_inactive_thresh_min:
            inactive += 1
            await handle_game_inactive_event(game)
        elif now.diff(last_active_date).in_minutes > config().game_idle_thresh_min:
            idle += 1
            await handle_game_idle_event(game)
    log.debug("Idle game check completed, found %d idle and %d inactive games", idle, inactive)


async def handle_obsolete_game_check_task() -> None:
    """Execute the Obsolete Game Check task."""
    log.info("SCHEDULED[Obsolete Game Check]")
    obsolete = 0
    now = pendulum.now()
    for (game, completed_date) in await _lookup_game_completion():
        if completed_date:
            if now.diff(completed_date).in_minutes > config().game_retention_thresh_min:
                obsolete += 1
                await handle_game_obsolete_event(game)
    log.debug("Obsolete game check completed, found %d obsolete games", obsolete)


async def schedule_idle_player_check() -> None:
    """Schedule the Idle Player Check task to run periodically, with a delay before starting."""
    period = config().idle_player_check_period_sec
    delay = config().idle_player_check_delay_sec
    p = Periodic(period, handle_idle_player_check_task)
    await p.start(delay=delay)
    log.debug("Completed scheduling idle player check with period %d and delay %d", period, delay)


async def schedule_idle_game_check() -> None:
    """Schedule the Idle Game Check task to run periodically, with a delay before starting."""
    period = config().idle_game_check_period_sec
    delay = config().idle_game_check_delay_sec
    p = Periodic(period, handle_idle_game_check_task)
    await p.start(delay=delay)
    log.debug("Completed scheduling idle game check with period %d and delay %d", period, delay)


async def schedule_obsolete_game_check() -> None:
    """Schedule the Obsolete Check task to run periodically, with a delay before starting."""
    period = config().obsolete_game_check_period_sec
    delay = config().obsolete_game_check_delay_sec
    p = Periodic(period, handle_obsolete_game_check_task)
    await p.start(delay=delay)
    log.debug("Completed scheduling obsolete game check with period %d and delay %d", period, delay)


SCHEDULED_TASKS = [schedule_idle_player_check, schedule_idle_game_check, schedule_obsolete_game_check]
