# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import

from unittest.mock import MagicMock

import pytest
from asynctest import CoroutineMock
from asynctest import MagicMock as AsyncMock
from asynctest import patch

from apologiesserver.scheduled import (
    _execute_idle_game_check,
    _execute_idle_player_check,
    _execute_idle_websocket_check,
    _execute_obsolete_game_check,
    _schedule_idle_game_check,
    _schedule_idle_player_check,
    _schedule_idle_websocket_check,
    _schedule_obsolete_game_check,
    scheduled_tasks,
)

from .util import mock_handler


class TestFunctions:
    """
    Test Python functions.
    """

    @patch("apologiesserver.scheduled._schedule_obsolete_game_check")
    @patch("apologiesserver.scheduled._schedule_idle_game_check")
    @patch("apologiesserver.scheduled._schedule_idle_player_check")
    @patch("apologiesserver.scheduled._schedule_idle_websocket_check")
    def test_scheduled_tasks(
        self, _schedule_idle_websocket_check, schedule_idle_player_check, schedule_idle_game_check, schedule_obsolete_game_check
    ):
        assert scheduled_tasks() == [
            _schedule_idle_websocket_check,
            schedule_idle_player_check,
            schedule_idle_game_check,
            schedule_obsolete_game_check,
        ]


class TestCoroutines:
    """
    Test Python coroutines.
    """

    pytestmark = pytest.mark.asyncio

    @patch("apologiesserver.scheduled.EventHandler")
    @patch("apologiesserver.scheduled.manager")
    async def test_execute_idle_websocket_check(self, manager, event_handler):
        handler = mock_handler()
        manager.return_value = handler.manager
        event_handler.return_value = handler
        await _execute_idle_websocket_check()
        event_handler.assert_called_once_with(manager.return_value)
        handler.manager.lock.assert_awaited()
        handler.handle_idle_websocket_check_task.assert_called_once()
        handler.execute_tasks.assert_awaited_once()

    @patch("apologiesserver.scheduled.EventHandler")
    @patch("apologiesserver.scheduled.manager")
    async def test_execute_idle_player_check(self, manager, event_handler):
        handler = mock_handler()
        manager.return_value = handler.manager
        event_handler.return_value = handler
        await _execute_idle_player_check()
        event_handler.assert_called_once_with(manager.return_value)
        handler.manager.lock.assert_awaited()
        handler.handle_idle_player_check_task.assert_called_once()
        handler.execute_tasks.assert_awaited_once()

    @patch("apologiesserver.scheduled.EventHandler")
    @patch("apologiesserver.scheduled.manager")
    async def test_execute_idle_game_check(self, manager, event_handler):
        handler = mock_handler()
        manager.return_value = handler.manager
        event_handler.return_value = handler
        await _execute_idle_game_check()
        event_handler.assert_called_once_with(manager.return_value)
        handler.manager.lock.assert_awaited()
        handler.handle_idle_game_check_task.assert_called_once()
        handler.execute_tasks.assert_awaited_once()

    @patch("apologiesserver.scheduled.EventHandler")
    @patch("apologiesserver.scheduled.manager")
    async def test_execute_obsolete_game_check(self, manager, event_handler):
        handler = mock_handler()
        manager.return_value = handler.manager
        event_handler.return_value = handler
        await _execute_obsolete_game_check()
        event_handler.assert_called_once_with(manager.return_value)
        handler.manager.lock.assert_awaited()
        handler.handle_obsolete_game_check_task.assert_called_once()
        handler.execute_tasks.assert_awaited_once()

    @patch("apologiesserver.scheduled.config")
    @patch("apologiesserver.scheduled.Periodic", autospec=True)
    async def test_schedule_idle_websocket_check(self, periodic, config):
        p = AsyncMock()
        p.start = CoroutineMock()
        periodic.return_value = p
        config.return_value = MagicMock(idle_websocket_check_period_sec=1, idle_websocket_check_delay_sec=2)
        await _schedule_idle_websocket_check()
        p.start.assert_awaited_once_with(delay=2)
        periodic.assert_called_once_with(1, _execute_idle_websocket_check)

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
