# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import

# TODO: should be ok to start unit testing this, I think the structure is final

"""Coroutines to handle scheduled tasks, executed on a periodic basis."""

import logging
from typing import Any, Callable, Coroutine, List

from periodic import Periodic

from .config import config
from .event import *
from .interface import ConnectionState, GameState
from .manager import handle_idle_games, handle_idle_players, handle_obsolete_games

log = logging.getLogger("apologies.scheduled")


async def handle_idle_player_check_task() -> None:
    """Execute the Idle Player Check task."""
    log.info("SCHEDULED[Idle Player Check]")
    queue = await handle_idle_players(config().player_idle_thresh_min, config().player_inactive_thresh_min)
    await queue.send()


async def handle_idle_game_check_task() -> None:
    """Execute the Idle Game Check task."""
    log.info("SCHEDULED[Idle Game Check]")
    queue = await handle_idle_games(config().game_idle_thresh_min, config().game_inactive_thresh_min)
    await queue.send()


async def handle_obsolete_game_check_task() -> None:
    """Execute the Obsolete Game Check task."""
    log.info("SCHEDULED[Obsolete Game Check]")
    queue = await handle_obsolete_games(config().game_retention_thresh_min)
    await queue.send()


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


def scheduled_tasks() -> List[Callable[[], Coroutine[Any, Any, None]]]:
    """Get a list of tasks that need to be scheduled."""
    return [schedule_idle_player_check, schedule_idle_game_check, schedule_obsolete_game_check]
