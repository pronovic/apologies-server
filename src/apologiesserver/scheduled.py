# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import

"""Coroutines to handle scheduled tasks, executed on a periodic basis."""

import logging
from typing import Any, Callable, Coroutine, List

from periodic import Periodic

from .config import config
from .event import *
from .event import EventHandler
from .interface import ConnectionState, GameState
from .manager import manager

log = logging.getLogger("apologies.scheduled")

# TODO: need some sort of idle websocket check
#       if a client connects, but never registers, we do want to dump them eventually
#       not sure how to detect this - I don't register that websocket anywhere right now
#       maybe we also need a limit on the number of inbound connections


async def _execute_idle_player_check() -> None:
    """Execute the Idle Player Check task."""
    with EventHandler(manager()) as handler:
        async with handler.manager.lock:
            handler.handle_idle_player_check_task()
        await handler.execute_tasks()


async def _execute_idle_game_check() -> None:
    """Execute the Idle Game Check task."""
    with EventHandler(manager()) as handler:
        async with handler.manager.lock:
            handler.handle_idle_game_check_task()
        await handler.execute_tasks()


async def _execute_obsolete_game_check() -> None:
    """Execute the Obsolete Game Check task."""
    with EventHandler(manager()) as handler:
        async with handler.manager.lock:
            handler.handle_obsolete_game_check_task()
        await handler.execute_tasks()


async def _schedule_idle_player_check() -> None:
    """Schedule the Idle Player Check task to run periodically, with a delay before starting."""
    period = config().idle_player_check_period_sec
    delay = config().idle_player_check_delay_sec
    p = Periodic(period, _execute_idle_player_check)
    await p.start(delay=delay)
    log.debug("Completed scheduling idle player check with period %d and delay %d", period, delay)


async def _schedule_idle_game_check() -> None:
    """Schedule the Idle Game Check task to run periodically, with a delay before starting."""
    period = config().idle_game_check_period_sec
    delay = config().idle_game_check_delay_sec
    p = Periodic(period, _execute_idle_game_check)
    await p.start(delay=delay)
    log.debug("Completed scheduling idle game check with period %d and delay %d", period, delay)


async def _schedule_obsolete_game_check() -> None:
    """Schedule the Obsolete Check task to run periodically, with a delay before starting."""
    period = config().obsolete_game_check_period_sec
    delay = config().obsolete_game_check_delay_sec
    p = Periodic(period, _execute_obsolete_game_check)
    await p.start(delay=delay)
    log.debug("Completed scheduling obsolete game check with period %d and delay %d", period, delay)


def scheduled_tasks() -> List[Callable[[], Coroutine[Any, Any, None]]]:
    """Get a list of tasks that need to be scheduled."""
    return [_schedule_idle_player_check, _schedule_idle_game_check, _schedule_obsolete_game_check]
