# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import

"""Coroutines to handle scheduled tasks, executed on a periodic basis."""

import logging

import pendulum
from periodic import Periodic

from .config import config
from .event import *
from .interface import ConnectionState
from .state import lookup_game_activity, lookup_game_completion, lookup_player_activity

log = logging.getLogger("apologies.scheduled")


async def handle_idle_player_check_task() -> None:
    """Execute the Idle Player Check task."""
    log.info("SCHEDULED[Idle Player Check]")
    idle = 0
    inactive = 0
    now = pendulum.now()
    dates = await lookup_player_activity()
    for player_id, (last_active_date, connection_state) in dates.items():
        disconnected = connection_state == ConnectionState.DISCONNECTED
        if now.diff(last_active_date).in_minutes > config().player_inactive_thresh_min:
            inactive += 1
            await handle_player_inactive_event(player_id)
        elif now.diff(last_active_date).in_minutes > config().player_idle_thresh_min:
            if disconnected:
                inactive += 1
                await handle_player_inactive_event(player_id)
            else:
                idle += 1
                await handle_player_idle_event(player_id)
    log.debug("Idle player check completed, found %d idle and %d inactive players", idle, inactive)


async def handle_idle_game_check_task() -> None:
    """Execute the Idle Game Check task."""
    log.info("SCHEDULED[Idle Game Check]")
    idle = 0
    inactive = 0
    now = pendulum.now()
    dates = await lookup_game_activity()
    for game_id, last_active_date in dates.items():
        if now.diff(last_active_date).in_minutes > config().game_inactive_thresh_min:
            inactive += 1
            await handle_game_inactive_event(game_id)
        elif now.diff(last_active_date).in_minutes > config().game_idle_thresh_min:
            idle += 1
            await handle_game_idle_event(game_id)
    log.debug("Idle game check completed, found %d idle and %d inactive games", idle, inactive)


async def handle_obsolete_game_check_task() -> None:
    """Execute the Obsolete Game Check task."""
    log.info("SCHEDULED[Obsolete Game Check]")
    obsolete = 0
    now = pendulum.now()
    dates = await lookup_game_completion()
    for game_id, completed_date in dates.items():
        if now.diff(completed_date).in_minutes > config().game_retension_thresh_min:
            obsolete += 1
            await handle_game_obsolete_event(game_id)
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
