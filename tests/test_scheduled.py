# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import

# TODO: finish unit testing this - I broke the tests with the refactoring

from unittest.mock import MagicMock

import pytest
from asynctest import CoroutineMock
from asynctest import MagicMock as AsyncMock
from asynctest import patch

from apologiesserver.scheduled import (
    _execute_idle_game_check,
    _execute_idle_player_check,
    _execute_obsolete_game_check,
    _schedule_idle_game_check,
    _schedule_idle_player_check,
    _schedule_obsolete_game_check,
    scheduled_tasks,
)


class TestFunctions:
    """
    Test Python functions.
    """

    @patch("apologiesserver.scheduled._schedule_obsolete_game_check")
    @patch("apologiesserver.scheduled._schedule_idle_game_check")
    @patch("apologiesserver.scheduled._schedule_idle_player_check")
    def test_scheduled_tasks(self, schedule_idle_player_check, schedule_idle_game_check, schedule_obsolete_game_check):
        assert scheduled_tasks() == [schedule_idle_player_check, schedule_idle_game_check, schedule_obsolete_game_check]


class TestCoroutines:
    """
    Test Python coroutines.
    """

    pytestmark = pytest.mark.asyncio

    # @patch("apologiesserver.scheduled.handle_idle_players")
    # @patch("apologiesserver.scheduled.config")
    # async def test_execute_idle_player_check(self, config, handle_idle_players):
    #     queue = AsyncMock()
    #     queue.send = CoroutineMock()
    #     handle_idle_players.return_value = queue
    #     config.return_value = MagicMock(player_idle_thresh_min=1, player_inactive_thresh_min=2)
    #     await _execute_idle_player_check()
    #     handle_idle_players.assert_awaited_once_with(1, 2)
    #     queue.send.assert_awaited_once()
    #
    # @patch("apologiesserver.scheduled.handle_idle_games")
    # @patch("apologiesserver.scheduled.config")
    # async def test_execute_idle_game_check(self, config, handle_idle_games):
    #     queue = AsyncMock()
    #     queue.send = CoroutineMock()
    #     handle_idle_games.return_value = queue
    #     config.return_value = MagicMock(game_idle_thresh_min=1, game_inactive_thresh_min=2)
    #     await _execute_idle_game_check()
    #     handle_idle_games.assert_awaited_once_with(1, 2)
    #     queue.send.assert_awaited_once()
    #
    # @patch("apologiesserver.scheduled.handle_obsolete_games")
    # @patch("apologiesserver.scheduled.config")
    # async def test_execute_obsolete_game_check(self, config, handle_obsolete_games):
    #     queue = AsyncMock()
    #     queue.send = CoroutineMock()
    #     handle_obsolete_games.return_value = queue
    #     config.return_value = MagicMock(game_retention_thresh_min=1)
    #     await _execute_obsolete_game_check()
    #     handle_obsolete_games.assert_awaited_once_with(1)
    #     queue.send.assert_awaited_once()

    @patch("apologiesserver.scheduled.config")
    @patch("apologiesserver.scheduled.Periodic", autospec=True)
    async def test_schedule_idle_player_check(self, periodic, config):
        p = AsyncMock()
        p.start = CoroutineMock()
        periodic.return_value = p
        config.return_value = MagicMock(idle_player_check_period_sec=1, idle_player_check_delay_sec=2)
        await _schedule_idle_player_check()
        p.start.assert_awaited_once_with(delay=2)
        periodic.assert_called_once_with(1, _execute_idle_player_check)

    @patch("apologiesserver.scheduled.config")
    @patch("apologiesserver.scheduled.Periodic", autospec=True)
    async def test_schedule_idle_game_check(self, periodic, config):
        p = AsyncMock()
        p.start = CoroutineMock()
        periodic.return_value = p
        config.return_value = MagicMock(idle_game_check_period_sec=1, idle_game_check_delay_sec=2)
        await _schedule_idle_game_check()
        p.start.assert_awaited_once_with(delay=2)
        periodic.assert_called_once_with(1, _execute_idle_game_check)

    @patch("apologiesserver.scheduled.config")
    @patch("apologiesserver.scheduled.Periodic", autospec=True)
    async def test_schedule_obsolete_game_check(self, periodic, config):
        p = AsyncMock()
        p.start = CoroutineMock()
        periodic.return_value = p
        config.return_value = MagicMock(obsolete_game_check_period_sec=1, obsolete_game_check_delay_sec=2)
        await _schedule_obsolete_game_check()
        p.start.assert_awaited_once_with(delay=2)
        periodic.assert_called_once_with(1, _execute_obsolete_game_check)
