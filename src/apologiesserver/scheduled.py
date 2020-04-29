# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:

"""Coroutines to handle scheduled tasks, executed on a periodic basis."""

# TODO: all of the coroutines need some sort of logging so we can track what is going on

from periodic import Periodic


async def handle_idle_game_check_task() -> None:
    """Execute the Idle Game Check task."""


async def handle_idle_player_check_task() -> None:
    """Execute the Idle Player Check task."""


async def handle_obsolete_game_check_task() -> None:
    """Execute the Obsolete Game Check task."""


async def schedule_idle_game_check(period: int = 60, delay: int = 120) -> None:
    """Schedule the Idle Game Check task to run periodically, with a delay before starting."""
    p = Periodic(period, handle_idle_game_check_task)
    await p.start(delay=delay)


async def schedule_idle_player_check(period: int = 60, delay: int = 120) -> None:
    """Schedule the Idle Player Check task to run periodically, with a delay before starting."""
    p = Periodic(period, handle_idle_player_check_task)
    await p.start(delay=delay)


async def schedule_obsolete_game_check(period: int = 60, delay: int = 120) -> None:
    """Schedule the Obsolete Check task to run periodically, with a delay before starting."""
    p = Periodic(period, handle_obsolete_game_check_task)
    await p.start(delay=delay)


SCHEDULED_TASKS = [schedule_idle_game_check, schedule_idle_player_check, schedule_obsolete_game_check]
"""List of tasks to be scheduled."""
