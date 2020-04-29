# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:

"""Coroutines to handle scheduled tasks, executed on a periodic basis."""

import logging

from periodic import Periodic

from .config import config

logger = logging.getLogger("apologies.scheduled")


async def handle_idle_player_check_task() -> None:
    """Execute the Idle Player Check task."""
    logger.info("SCHEDULED[Idle Player Check]")


async def handle_idle_game_check_task() -> None:
    """Execute the Idle Game Check task."""
    logger.info("SCHEDULED[Idle Game Check]")


async def handle_obsolete_game_check_task() -> None:
    """Execute the Obsolete Game Check task."""
    logger.info("SCHEDULED[Obsolete Game Check]")


async def schedule_idle_player_check() -> None:
    """Schedule the Idle Player Check task to run periodically, with a delay before starting."""
    period = config().idle_player_check_period_sec
    delay = config().idle_player_check_delay_sec
    p = Periodic(period, handle_idle_player_check_task)
    await p.start(delay=delay)


async def schedule_idle_game_check() -> None:
    """Schedule the Idle Game Check task to run periodically, with a delay before starting."""
    period = config().idle_game_check_period_sec
    delay = config().idle_game_check_delay_sec
    p = Periodic(period, handle_idle_game_check_task)
    await p.start(delay=delay)


async def schedule_obsolete_game_check() -> None:
    """Schedule the Obsolete Check task to run periodically, with a delay before starting."""
    period = config().obsolete_game_check_period_sec
    delay = config().obsolete_game_check_delay_sec
    p = Periodic(period, handle_obsolete_game_check_task)
    await p.start(delay=delay)


SCHEDULED_TASKS = [schedule_idle_player_check, schedule_idle_game_check, schedule_obsolete_game_check]
