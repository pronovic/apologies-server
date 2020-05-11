# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=redefined-outer-name,wildcard-import,too-many-lines

from unittest.mock import MagicMock, call

import pytest
from apologies.game import GameMode
from asynctest import CoroutineMock
from asynctest import MagicMock as AsyncMock
from asynctest import patch

from apologiesserver.event import EventHandler, RequestContext, TaskQueue
from apologiesserver.interface import *

from .util import to_date


class TestTaskQueue:
    """
    Test the TaskQueue class.
    """

    def test_disconnect(self):
        socket1 = MagicMock()
        socket2 = MagicMock()

        queue = TaskQueue()
        assert queue.is_empty() is True
        assert queue.disconnects == set()

        queue.disconnect(None)
        assert queue.is_empty() is True
        assert queue.disconnects == set()

        queue.disconnect(socket1)
        assert queue.is_empty() is False
        assert queue.disconnects == {socket1}

        queue.disconnect(socket2)
        assert queue.is_empty() is False
        assert queue.disconnects == {socket1, socket2}

        queue.disconnect(socket1)
        assert queue.is_empty() is False
        assert queue.disconnects == {socket1, socket2}

        queue.clear()
        assert queue.is_empty() is True
        assert queue.disconnects == set()

    def test_message(self):
        socket1 = MagicMock()
        socket2 = MagicMock()
        socket3 = MagicMock()

        message1 = MagicMock()
        message1.to_json.return_value = "json1"

        message2 = MagicMock()
        message2.to_json.return_value = "json2"

        message3 = MagicMock()
        message3.to_json.return_value = "json3"

        player = MagicMock(websocket=socket2)

        queue = TaskQueue()
        assert queue.is_empty() is True
        assert queue.messages == []

        queue.message(message1, websockets=None, players=None)
        assert queue.is_empty() is True
        assert queue.messages == []

        queue.message(message1, websockets=[], players=[])
        assert queue.is_empty() is True
        assert queue.messages == []

        queue.message(message1, websockets=[socket1])
        assert queue.is_empty() is False
        assert queue.messages == [("json1", socket1)]

        queue.message(message2, players=[player])
        assert queue.is_empty() is False
        assert queue.messages == [("json1", socket1), ("json2", socket2)]

        queue.message(message3, websockets=[socket1, socket3], players=[player])
        assert queue.is_empty() is False
        assert queue.messages == [
            ("json1", socket1),
            ("json2", socket2),
            ("json3", socket1),
            ("json3", socket3),
            ("json3", socket2),
        ]

        queue.clear()
        assert queue.is_empty() is True
        assert queue.messages == []

    @pytest.mark.asyncio
    @patch("apologiesserver.event.asyncio")
    async def test_execute_empty(self, stub):
        stub.wait = CoroutineMock()
        queue = TaskQueue()
        await queue.execute()
        stub.wait.assert_not_awaited()  # wait() doesn't accept an empty list, so we just don't call it

    @pytest.mark.asyncio
    @patch("apologiesserver.event.asyncio")
    async def test_execute(self, stub):
        stub.wait = CoroutineMock()

        socket1 = MagicMock()
        socket1.close = MagicMock()
        socket1.close.return_value = "1"

        socket2 = MagicMock()
        socket2.send = MagicMock()
        socket2.send.return_value = "2"

        socket3 = MagicMock()
        socket3.send = MagicMock()
        socket3.send.return_value = "3"

        message1 = MagicMock()
        message1.to_json.return_value = "json1"

        message2 = MagicMock()
        message2.to_json.return_value = "json2"

        queue = TaskQueue()
        queue.disconnect(socket1)
        queue.message(message1, websockets=[socket1])  # will be ignored because socket is disconnected
        queue.message(message2, websockets=[socket2, socket3])
        await queue.execute()

        expected = [
            "1",
            "2",
            "3",
        ]  # this is kind of hokey, since they're really coroutines, but it proves what we need
        stub.wait.assert_awaited_once_with(expected)
        socket1.close.assert_called_once()
        socket2.send.assert_called_once_with("json2")
        socket3.send.assert_called_once_with("json2")


class TestEventHandler:
    """
    Test the basic EventHandler functionality.
    """

    def test_context_manager(self):
        manager = MagicMock()
        queue = MagicMock()
        queue.clear = MagicMock()
        handler = EventHandler(manager, queue)
        with handler as result:
            assert handler is result  # proves that the right object is returned
            queue.clear.assert_called_once()  # proves that we clear the queue on entering
            queue.clear = MagicMock()  # clear it so we can easily check for 2nd call
        queue.clear.assert_called_once()  # proves that we clear the cache on exiting

    @pytest.mark.asyncio
    async def test_execute(self):
        manager = MagicMock()
        queue = AsyncMock()
        queue.execute = CoroutineMock()
        handler = EventHandler(manager, queue)
        await handler.execute_tasks()
        queue.execute.assert_awaited_once()


class TestTaskMethods:
    """
    Test the task-related methods on EventHandler.
    """

    # pylint: disable=too-many-locals,invalid-name
    @patch("apologiesserver.event.pendulum")
    @patch("apologiesserver.event.config")
    def test_handle_idle_player_check_task(self, config, pendulum):
        config.return_value = MagicMock(player_idle_thresh_min=10, player_inactive_thresh_min=20)
        pendulum.now.return_value = to_date("2020-05-11T10:22:00,000")

        p1 = MagicMock()
        p2 = MagicMock()
        p3 = MagicMock()
        p4 = MagicMock()
        p5 = MagicMock()
        p6 = MagicMock()
        p7 = MagicMock()
        p8 = MagicMock()

        # Results: 2 are active (a1, a5), 2 are idle (a2, a3) and 4 are inactive (a4, a6, a7, a8)
        # A disconnected player is either active or inactive, it can't be idle
        a1 = (p1, to_date("2020-05-11T10:12:00,001"), ConnectionState.CONNECTED)  # connected and active (9:59.999)
        a2 = (p2, to_date("2020-05-11T10:12:00,000"), ConnectionState.CONNECTED)  # connected and idle (10:00.000)
        a3 = (p3, to_date("2020-05-11T10:02:00,001"), ConnectionState.CONNECTED)  # connected and idle (19:59.999)
        a4 = (p4, to_date("2020-05-11T10:02:00,000"), ConnectionState.CONNECTED)  # connected and inactive (20:00.000)
        a5 = (p5, to_date("2020-05-11T10:12:00,001"), ConnectionState.DISCONNECTED)  # disconnected and active (9:59.999)
        a6 = (p6, to_date("2020-05-11T10:12:00,000"), ConnectionState.DISCONNECTED)  # disconnected and idle (10:00.000)
        a7 = (p7, to_date("2020-05-11T10:12:00,000"), ConnectionState.DISCONNECTED)  # disconnected and idle (19:59.999)
        a8 = (p8, to_date("2020-05-11T10:02:00,000"), ConnectionState.DISCONNECTED)  # disconnected and inactive (20:00.000)
        activity = [a1, a2, a3, a4, a5, a6, a7, a8]

        handler = EventHandler(MagicMock())
        handler.manager.lookup_player_activity.return_value = activity
        handler.handle_player_idle_event = MagicMock()
        handler.handle_player_inactive_event = MagicMock()

        assert handler.handle_idle_player_check_task() == (2, 4)

        idle_calls = [call(p2), call(p3)]
        inactive_calls = [call(p4), call(p6), call(p7), call(p8)]

        handler.handle_player_idle_event.assert_has_calls(idle_calls)
        handler.handle_player_inactive_event.assert_has_calls(inactive_calls)

    # pylint: disable=invalid-name
    @patch("apologiesserver.event.pendulum")
    @patch("apologiesserver.event.config")
    def test_handle_idle_game_check_task(self, config, pendulum):
        config.return_value = MagicMock(game_idle_thresh_min=10, game_inactive_thresh_min=20)
        pendulum.now.return_value = to_date("2020-05-11T10:22:00,000")

        g1 = MagicMock()
        g2 = MagicMock()
        g3 = MagicMock()
        g4 = MagicMock()

        # Results: 1 is active (a1), 2 are idle (a2, a3) and 1 is inactive (a4)
        a1 = (g1, to_date("2020-05-11T10:12:00,001"))  # active (9:59.999)
        a2 = (g2, to_date("2020-05-11T10:12:00,000"))  # idle (10:00.000)
        a3 = (g3, to_date("2020-05-11T10:02:00,001"))  # idle (19:59.999)
        a4 = (g4, to_date("2020-05-11T10:02:00,000"))  # inactive (20:00.000)
        activity = [a1, a2, a3, a4]

        handler = EventHandler(MagicMock())
        handler.manager.lookup_game_activity.return_value = activity
        handler.handle_game_idle_event = MagicMock()
        handler.handle_game_inactive_event = MagicMock()

        assert handler.handle_idle_game_check_task() == (2, 1)

        idle_calls = [call(g2), call(g3)]
        inactive_calls = [call(g4)]

        handler.handle_game_idle_event.assert_has_calls(idle_calls)
        handler.handle_game_inactive_event.assert_has_calls(inactive_calls)

    # pylint: disable=invalid-name
    @patch("apologiesserver.event.pendulum")
    @patch("apologiesserver.event.config")
    def test_handle_obsolete_game_check_task(self, config, pendulum):
        config.return_value = MagicMock(game_retention_thresh_min=10)
        pendulum.now.return_value = to_date("2020-05-11T10:22:00,000")

        g1 = MagicMock()
        g2 = MagicMock()
        g3 = MagicMock()

        # Results: 1 is in-progress (a1), 1 is young enough to keep (a2) and 1 is obsolete (a3)
        a1 = (g1, None)  # in-progress
        a2 = (g2, to_date("2020-05-11T10:12:00,001"))  # young enough to keep (9:59.999)
        a3 = (g3, to_date("2020-05-11T10:12:00,000"))  # obsolete (10:00.000)
        completion = [a1, a2, a3]

        handler = EventHandler(MagicMock())
        handler.manager.lookup_game_completion.return_value = completion
        handler.handle_game_obsolete_event = MagicMock()

        assert handler.handle_obsolete_game_check_task() == 1

        obsolete_calls = [call(g3)]

        handler.handle_game_obsolete_event.assert_has_calls(obsolete_calls)


# pylint: disable=too-many-public-methods
class TestRequestMethods:
    """
    Test the request-related methods on EventHandler.
    """

    @patch("apologiesserver.event.config")
    def test_handle_register_player_request_below_limit(self, config):
        config.return_value = MagicMock(registered_player_limit=5)
        handler = EventHandler(MagicMock())
        handler.manager.registered_player_count.return_value = 4
        handler.handle_player_registered_event = MagicMock()
        websocket = MagicMock()
        context = RegisterPlayerContext(handle="leela")
        message = Message(MessageType.REGISTER_PLAYER, context=context)
        handler.handle_register_player_request(message, websocket)
        assert handler.queue.is_empty()
        handler.handle_player_registered_event.assert_called_once_with(websocket, "leela")

    @patch("apologiesserver.event.config")
    def test_handle_register_player_request_at_limit(self, config):
        config.return_value = MagicMock(registered_player_limit=5)
        handler = EventHandler(MagicMock())
        handler.manager.registered_player_count.return_value = 5
        handler.handle_player_registered_event = MagicMock()
        websocket = MagicMock()
        context = RegisterPlayerContext(handle="leela")
        message = Message(MessageType.REGISTER_PLAYER, context=context)
        with pytest.raises(ProcessingError, match=r"System user limit reached"):
            handler.handle_register_player_request(message, websocket)
        assert handler.queue.is_empty()
        handler.handle_player_registered_event.assert_not_called()

    def test_handle_reregister_player_request(self):
        handler = EventHandler(MagicMock())
        handler.handle_player_reregistered_event = MagicMock()
        message = Message(MessageType.REREGISTER_PLAYER)
        websocket = MagicMock()
        player = MagicMock()
        game = MagicMock()
        request = RequestContext(message, websocket, player, game)
        handler.handle_reregister_player_request(request)
        handler.handle_player_reregistered_event.assert_called_once_with(player, websocket)

    def test_handle_unregister_player_request(self):
        handler = EventHandler(MagicMock())
        handler.handle_player_unregistered_event = MagicMock()
        message = Message(MessageType.UNREGISTER_PLAYER)
        websocket = MagicMock()
        player = MagicMock()
        game = MagicMock()
        request = RequestContext(message, websocket, player, game)
        handler.handle_unregister_player_request(request)
        handler.handle_player_unregistered_event.assert_called_once_with(player, game)

    def test_handle_list_players_request(self):
        handler = EventHandler(MagicMock())
        handler.handle_registered_players_event = MagicMock()
        message = Message(MessageType.LIST_PLAYERS)
        websocket = MagicMock()
        player = MagicMock()
        game = MagicMock()
        request = RequestContext(message, websocket, player, game)
        handler.handle_list_players_request(request)
        handler.handle_registered_players_event.assert_called_once_with(player)

    def test_handle_advertise_game_request_already_playing(self):
        handler = EventHandler(MagicMock())
        handler.handle_game_advertised_event = MagicMock()
        context = AdvertiseGameContext("name", GameMode.STANDARD, 3, Visibility.PUBLIC, ["fry", "bender"])
        message = Message(MessageType.ADVERTISE_GAME, context=context)
        websocket = MagicMock()
        player = MagicMock()
        game = MagicMock()
        request = RequestContext(message, websocket, player, game)
        with pytest.raises(ProcessingError, match=r"Player is already playing a game"):
            handler.handle_advertise_game_request(request)
        handler.handle_game_advertised_event.assert_not_called()

    @patch("apologiesserver.event.config")
    def test_handle_advertise_game_request_below_limit(self, config):
        config.return_value = MagicMock(total_game_limit=5)
        handler = EventHandler(MagicMock())
        handler.manager.total_game_count.return_value = 4
        handler.handle_game_advertised_event = MagicMock()
        context = AdvertiseGameContext("name", GameMode.STANDARD, 3, Visibility.PUBLIC, ["fry", "bender"])
        message = Message(MessageType.ADVERTISE_GAME, context=context)
        websocket = MagicMock()
        player = MagicMock()
        game = None
        request = RequestContext(message, websocket, player, game)
        handler.handle_advertise_game_request(request)
        handler.handle_game_advertised_event.assert_called_once_with(player, context)

    @patch("apologiesserver.event.config")
    def test_handle_advertise_game_request_at_limit(self, config):
        config.return_value = MagicMock(total_game_limit=5)
        handler = EventHandler(MagicMock())
        handler.manager.total_game_count.return_value = 5
        handler.handle_game_advertised_event = MagicMock()
        context = AdvertiseGameContext("name", GameMode.STANDARD, 3, Visibility.PUBLIC, ["fry", "bender"])
        message = Message(MessageType.ADVERTISE_GAME, context=context)
        websocket = MagicMock()
        player = MagicMock()
        game = None
        request = RequestContext(message, websocket, player, game)
        with pytest.raises(ProcessingError, match=r"System game limit reached"):
            handler.handle_advertise_game_request(request)
        handler.handle_game_advertised_event.assert_not_called()

    def test_handle_list_available_games_request(self):
        handler = EventHandler(MagicMock())
        handler.handle_available_games_event = MagicMock()
        message = Message(MessageType.LIST_AVAILABLE_GAMES)
        websocket = MagicMock()
        player = MagicMock()
        game = MagicMock()
        request = RequestContext(message, websocket, player, game)
        handler.handle_list_available_games_request(request)
        handler.handle_available_games_event.assert_called_once_with(player)

    def test_handle_join_game_request_already_playing(self):
        handler = EventHandler(MagicMock())
        handler.handle_game_joined_event = MagicMock()
        context = JoinGameContext(game_id="game")
        message = Message(MessageType.JOIN_GAME, context=context)
        websocket = MagicMock()
        player = MagicMock()
        game = MagicMock()
        request = RequestContext(message, websocket, player, game)
        with pytest.raises(ProcessingError, match=r"Player is already playing a game"):
            handler.handle_join_game_request(request)
        handler.handle_game_joined_event.assert_not_called()

    def test_handle_join_game_request(self):
        handler = EventHandler(MagicMock())
        handler.handle_game_joined_event = MagicMock()
        context = JoinGameContext(game_id="game")
        message = Message(MessageType.JOIN_GAME, context=context)
        websocket = MagicMock()
        player = MagicMock()
        game = None
        request = RequestContext(message, websocket, player, game)
        handler.handle_join_game_request(request)
        handler.handle_game_joined_event.assert_called_once_with(player, game_id="game")

    def test_handle_quit_game_request_not_playing(self):
        handler = EventHandler(MagicMock())
        handler.handle_game_player_quit_event = MagicMock()
        message = Message(MessageType.QUIT_GAME)
        websocket = MagicMock()
        player = MagicMock()
        game = None
        request = RequestContext(message, websocket, player, game)
        with pytest.raises(ProcessingError, match=r"Player is not playing a game"):
            handler.handle_quit_game_request(request)
        handler.handle_game_player_quit_event.assert_not_called()

    def test_handle_quit_game_request_not_in_progress(self):
        handler = EventHandler(MagicMock())
        handler.handle_game_player_quit_event = MagicMock()
        message = Message(MessageType.QUIT_GAME)
        websocket = MagicMock()
        player = MagicMock()
        game = MagicMock()
        game.is_in_progress.return_value = False
        request = RequestContext(message, websocket, player, game)
        with pytest.raises(ProcessingError, match=r"Game is not in progress"):
            handler.handle_quit_game_request(request)
        handler.handle_game_player_quit_event.assert_not_called()

    def test_handle_quit_game_request_advertiser(self):
        handler = EventHandler(MagicMock())
        handler.handle_game_player_quit_event = MagicMock()
        message = Message(MessageType.QUIT_GAME)
        websocket = MagicMock()
        player = MagicMock(handle="leela")
        game = MagicMock(advertiser_handle="leela")
        request = RequestContext(message, websocket, player, game)
        with pytest.raises(ProcessingError, match=r"Advertiser may not quit a game"):
            handler.handle_quit_game_request(request)
        handler.handle_game_player_quit_event.assert_not_called()

    def test_handle_quit_game_request(self):
        handler = EventHandler(MagicMock())
        handler.handle_game_player_quit_event = MagicMock()
        message = Message(MessageType.QUIT_GAME)
        websocket = MagicMock()
        player = MagicMock()
        game = MagicMock()
        request = RequestContext(message, websocket, player, game)
        handler.handle_quit_game_request(request)
        handler.handle_game_player_quit_event.assert_called_once_with(player, game)

    def test_handle_start_game_request_not_playing(self):
        handler = EventHandler(MagicMock())
        handler.handle_game_started_event = MagicMock()
        message = Message(MessageType.START_GAME)
        websocket = MagicMock()
        player = MagicMock()
        game = None
        request = RequestContext(message, websocket, player, game)
        with pytest.raises(ProcessingError, match=r"Player is not playing a game"):
            handler.handle_start_game_request(request)
        handler.handle_game_started_event.assert_not_called()

    def test_handle_start_game_request_already_played(self):
        handler = EventHandler(MagicMock())
        handler.handle_game_started_event = MagicMock()
        message = Message(MessageType.START_GAME)
        websocket = MagicMock()
        player = MagicMock()
        game = MagicMock()
        game.is_playing.return_value = True
        request = RequestContext(message, websocket, player, game)
        with pytest.raises(ProcessingError, match=r"Game is already being played"):
            handler.handle_start_game_request(request)
        handler.handle_game_started_event.assert_not_called()

    def test_handle_start_game_request_not_advertiser(self):
        handler = EventHandler(MagicMock())
        handler.handle_game_started_event = MagicMock()
        message = Message(MessageType.START_GAME)
        websocket = MagicMock()
        player = MagicMock(handle="leela")
        game = MagicMock(advertiser_handle="bender")
        game.is_playing.return_value = False
        request = RequestContext(message, websocket, player, game)
        with pytest.raises(ProcessingError, match=r"Player did not advertise this game"):
            handler.handle_start_game_request(request)
        handler.handle_game_started_event.assert_not_called()

    @patch("apologiesserver.event.config")
    def test_handle_start_game_request_below_limit(self, config):
        config.return_value = MagicMock(in_progress_game_limit=5)
        handler = EventHandler(MagicMock())
        handler.manager.in_progress_game_count.return_value = 4
        handler.handle_game_started_event = MagicMock()
        message = Message(MessageType.START_GAME)
        websocket = MagicMock()
        player = MagicMock(handle="leela")
        game = MagicMock(advertiser_handle="leela")
        game.is_playing.return_value = False
        request = RequestContext(message, websocket, player, game)
        handler.handle_start_game_request(request)
        handler.handle_game_started_event.assert_called_once_with(game)

    @patch("apologiesserver.event.config")
    def test_handle_start_game_request_at_limit(self, config):
        config.return_value = MagicMock(in_progress_game_limit=5)
        handler = EventHandler(MagicMock())
        handler.manager.in_progress_game_count.return_value = 5
        handler.handle_game_started_event = MagicMock()
        message = Message(MessageType.START_GAME)
        websocket = MagicMock()
        player = MagicMock(handle="leela")
        game = MagicMock(advertiser_handle="leela")
        game.is_playing.return_value = False
        request = RequestContext(message, websocket, player, game)
        with pytest.raises(ProcessingError, match=r"System game limit reached"):
            handler.handle_start_game_request(request)
        handler.handle_game_started_event.assert_not_called()

    def test_handle_cancel_game_request_not_playing(self):
        handler = EventHandler(MagicMock())
        handler.handle_game_cancelled_event = MagicMock()
        message = Message(MessageType.CANCEL_GAME)
        websocket = MagicMock()
        player = MagicMock()
        game = None
        request = RequestContext(message, websocket, player, game)
        with pytest.raises(ProcessingError, match=r"Player is not playing a game"):
            handler.handle_cancel_game_request(request)
        handler.handle_game_cancelled_event.assert_not_called()

    def test_handle_cancel_game_request_not_in_progress(self):
        handler = EventHandler(MagicMock())
        handler.handle_game_cancelled_event = MagicMock()
        message = Message(MessageType.CANCEL_GAME)
        websocket = MagicMock()
        player = MagicMock()
        game = MagicMock()
        game.is_in_progress.return_value = False
        request = RequestContext(message, websocket, player, game)
        with pytest.raises(ProcessingError, match=r"Game is not in progress"):
            handler.handle_cancel_game_request(request)
        handler.handle_game_cancelled_event.assert_not_called()

    def test_handle_cancel_game_request_not_advertiser(self):
        handler = EventHandler(MagicMock())
        handler.handle_game_cancelled_event = MagicMock()
        message = Message(MessageType.CANCEL_GAME)
        websocket = MagicMock()
        player = MagicMock(handle="leela")
        game = MagicMock(advertiser_handle="bender")
        request = RequestContext(message, websocket, player, game)
        with pytest.raises(ProcessingError, match=r"Player did not advertise this game"):
            handler.handle_cancel_game_request(request)
        handler.handle_game_cancelled_event.assert_not_called()

    def test_handle_cancel_game_request(self):
        handler = EventHandler(MagicMock())
        handler.handle_game_cancelled_event = MagicMock()
        message = Message(MessageType.CANCEL_GAME)
        websocket = MagicMock()
        player = MagicMock(handle="leela")
        game = MagicMock(advertiser_handle="leela")
        request = RequestContext(message, websocket, player, game)
        handler.handle_cancel_game_request(request)
        handler.handle_game_cancelled_event.assert_called_once_with(game, CancelledReason.CANCELLED)

    def test_handle_execute_move_request_not_playing(self):
        handler = EventHandler(MagicMock())
        handler.handle_game_execute_move_event = MagicMock()
        context = ExecuteMoveContext(move_id="move")
        message = Message(MessageType.EXECUTE_MOVE, context=context)
        websocket = MagicMock()
        player = MagicMock()
        game = None
        request = RequestContext(message, websocket, player, game)
        with pytest.raises(ProcessingError, match=r"Player is not playing a game"):
            handler.handle_execute_move_request(request)
        handler.handle_game_execute_move_event.assert_not_called()

    def test_handle_execute_move_request_not_being_played(self):
        handler = EventHandler(MagicMock())
        handler.handle_game_execute_move_event = MagicMock()
        context = ExecuteMoveContext(move_id="move")
        message = Message(MessageType.EXECUTE_MOVE, context=context)
        websocket = MagicMock()
        player = MagicMock()
        game = MagicMock()
        game.is_playing.return_value = False
        request = RequestContext(message, websocket, player, game)
        with pytest.raises(ProcessingError, match=r"Game is not being played"):
            handler.handle_execute_move_request(request)
        handler.handle_game_execute_move_event.assert_not_called()

    def test_handle_execute_move_request_no_move_pending(self):
        handler = EventHandler(MagicMock())
        handler.handle_game_execute_move_event = MagicMock()
        context = ExecuteMoveContext(move_id="move")
        message = Message(MessageType.EXECUTE_MOVE, context=context)
        websocket = MagicMock()
        player = MagicMock(handle="leela")
        game = MagicMock()
        game.is_move_pending.return_value = False
        request = RequestContext(message, websocket, player, game)
        with pytest.raises(ProcessingError, match=r"No move is pending for this player"):
            handler.handle_execute_move_request(request)
        game.is_move_pending.assert_called_once_with("leela")
        game.is_legal_move.assert_not_called()
        handler.handle_game_execute_move_event.assert_not_called()

    def test_handle_execute_move_request_illegal_move(self):
        handler = EventHandler(MagicMock())
        handler.handle_game_execute_move_event = MagicMock()
        context = ExecuteMoveContext(move_id="move")
        message = Message(MessageType.EXECUTE_MOVE, context=context)
        websocket = MagicMock()
        player = MagicMock(handle="leela")
        game = MagicMock()
        game.is_move_pending.return_value = True
        game.is_legal_move.return_value = False
        request = RequestContext(message, websocket, player, game)
        with pytest.raises(ProcessingError, match=r"The chosen move is not legal"):
            handler.handle_execute_move_request(request)
        game.is_move_pending.assert_called_once_with("leela")
        game.is_legal_move.assert_called_once_with("leela", "move")
        handler.handle_game_execute_move_event.assert_not_called()

    def test_handle_execute_move_request(self):
        handler = EventHandler(MagicMock())
        handler.handle_game_execute_move_event = MagicMock()
        context = ExecuteMoveContext(move_id="move")
        message = Message(MessageType.EXECUTE_MOVE, context=context)
        websocket = MagicMock()
        player = MagicMock(handle="leela")
        game = MagicMock()
        game.is_move_pending.return_value = True
        request = RequestContext(message, websocket, player, game)
        handler.handle_execute_move_request(request)
        game.is_move_pending.assert_called_once_with("leela")
        handler.handle_game_execute_move_event.assert_called_once_with(player, game, "move")

    def test_handle_retrieve_game_state_request_not_playing(self):
        handler = EventHandler(MagicMock())
        handler.handle_game_state_change_event = MagicMock()
        message = Message(MessageType.RETRIEVE_GAME_STATE)
        websocket = MagicMock()
        player = MagicMock()
        game = None
        request = RequestContext(message, websocket, player, game)
        with pytest.raises(ProcessingError, match=r"Player is not playing a game"):
            handler.handle_retrieve_game_state_request(request)
        handler.handle_game_state_change_event.assert_not_called()

    def test_handle_retrieve_game_state_request_not_being_played(self):
        handler = EventHandler(MagicMock())
        handler.handle_game_state_change_event = MagicMock()
        message = Message(MessageType.RETRIEVE_GAME_STATE)
        websocket = MagicMock()
        player = MagicMock()
        game = MagicMock()
        game.is_playing.return_value = False
        request = RequestContext(message, websocket, player, game)
        with pytest.raises(ProcessingError, match=r"Game is not being played"):
            handler.handle_retrieve_game_state_request(request)
        handler.handle_game_state_change_event.called_once_with(game, player)

    def test_handle_retrieve_game_state_request(self):
        handler = EventHandler(MagicMock())
        handler.handle_game_state_change_event = MagicMock()
        message = Message(MessageType.RETRIEVE_GAME_STATE)
        websocket = MagicMock()
        player = MagicMock()
        game = MagicMock()
        game.is_playing.return_value = True
        request = RequestContext(message, websocket, player, game)
        handler.handle_retrieve_game_state_request(request)
        handler.handle_game_state_change_event.called_once_with(game, player)

    def test_handle_send_message_request(self):
        handler = EventHandler(MagicMock())
        handler.handle_player_message_received_event = MagicMock()
        context = SendMessageContext(message="hello", recipient_handles=["fry", "bender"])
        message = Message(MessageType.SEND_MESSAGE, context=context)
        websocket = MagicMock()
        player = MagicMock()
        game = MagicMock()
        request = RequestContext(message, websocket, player, game)
        handler.handle_send_message_request(request)
        handler.handle_player_message_received_event.called_once_with("handle", ["fry", "bender"], "hello")


class TestEventMethods:
    """
    Test the event-related methods on EventHandler.
    """

    def test_handle_server_shutdown_event(self):
        websocket = MagicMock()
        game = MagicMock()
        message = Message(MessageType.SERVER_SHUTDOWN)
        handler = EventHandler(MagicMock())
        handler.queue.message = MagicMock()
        handler.manager.lookup_all_websockets.return_value = [websocket]
        handler.manager.lookup_in_progress_games.return_value = [game]
        handler.handle_game_cancelled_event = MagicMock()
        handler.handle_server_shutdown_event()
        handler.queue.message.assert_called_once_with(message, websockets=[websocket])
        handler.handle_game_cancelled_event.assert_called_once_with(game, CancelledReason.SHUTDOWN, notify=False)

    def test_handle_registered_players_event(self):
        player = MagicMock()
        result = MagicMock()
        registered = MagicMock()
        result.to_registered_player.return_value = registered
        context = RegisteredPlayersContext(players=[registered])
        message = Message(MessageType.REGISTERED_PLAYERS, context=context)
        handler = EventHandler(MagicMock())
        handler.queue.message = MagicMock()
        handler.manager.lookup_all_players.return_value = [result]
        handler.handle_registered_players_event(player)
        handler.queue.message.assert_called_once_with(message, players=[player])

    def test_handle_available_games_event(self):
        player = MagicMock()
        advertised = MagicMock()
        game = MagicMock()
        game.to_advertised_game.return_value = advertised
        context = AvailableGamesContext(games=[advertised])
        message = Message(MessageType.AVAILABLE_GAMES, context=context)
        handler = EventHandler(MagicMock())
        handler.queue.message = MagicMock()
        handler.manager.lookup_available_games.return_value = [game]
        handler.handle_available_games_event(player)
        handler.manager.lookup_available_games.assert_called_once_with(player)
        handler.queue.message.assert_called_once_with(message, players=[player])

    def test_handle_player_registered_event(self):
        websocket = MagicMock()
        player = MagicMock(player_id="player_id")
        context = PlayerRegisteredContext(player_id="player_id")
        message = Message(MessageType.PLAYER_REGISTERED, context=context)
        handler = EventHandler(MagicMock())
        handler.queue.message = MagicMock()
        handler.manager.track_player.return_value = player
        handler.handle_player_registered_event(websocket, "leela")
        handler.manager.track_player.assert_called_once_with(websocket, "leela")
        handler.queue.message.assert_called_once_with(message, websockets=[websocket])

    def test_handle_player_reregistered_event(self):
        websocket = MagicMock()
        player = MagicMock(player_id="player_id")
        context = PlayerRegisteredContext(player_id="player_id")
        message = Message(MessageType.PLAYER_REGISTERED, context=context)
        handler = EventHandler(MagicMock())
        handler.queue.message = MagicMock()
        handler.handle_player_reregistered_event(player, websocket)
        assert player.websocket is websocket
        handler.queue.message.assert_called_once_with(message, players=[player])

    def test_handle_player_unregistered_event_no_game(self):
        player = MagicMock()
        handler = EventHandler(MagicMock())
        handler.handle_game_player_change_event = MagicMock()
        handler.handle_game_cancelled_event = MagicMock()
        handler.handle_player_unregistered_event(player)
        player.mark_quit.assert_called_once()
        handler.handle_game_player_change_event.assert_not_called()
        handler.handle_game_cancelled_event.assert_not_called()
        handler.manager.delete_player.assert_called_once_with(player)

    def test_handle_player_unregistered_event_with_game(self):
        comment = "Player leela unregistered"
        player = MagicMock(handle="leela")
        game = MagicMock()
        game.is_viable.return_value = True
        handler = EventHandler(MagicMock())
        handler.handle_game_player_change_event = MagicMock()
        handler.handle_game_cancelled_event = MagicMock()
        handler.handle_player_unregistered_event(player, game)
        player.mark_quit.assert_called_once()
        game.mark_quit.assert_called_once_with(player)
        handler.handle_game_player_change_event.assert_called_once_with(game, comment)
        handler.handle_game_cancelled_event.assert_not_called()
        handler.manager.delete_player.assert_called_once_with(player)

    def test_handle_player_unregistered_event_not_viable(self):
        comment = "Player leela unregistered"
        player = MagicMock(handle="leela")
        game = MagicMock()
        game.is_viable.return_value = False
        handler = EventHandler(MagicMock())
        handler.handle_game_player_change_event = MagicMock()
        handler.handle_game_cancelled_event = MagicMock()
        handler.handle_player_unregistered_event(player, game)
        player.mark_quit.assert_called_once()
        game.mark_quit.assert_called_once_with(player)
        handler.handle_game_player_change_event.assert_called_once_with(game, comment)
        handler.handle_game_cancelled_event.assert_called_once_with(game, CancelledReason.NOT_VIABLE, comment)
        handler.manager.delete_player.assert_called_once_with(player)

    def test_handle_player_disconnected_event_unknown(self):
        websocket = MagicMock()
        handler = EventHandler(MagicMock())
        handler.handle_game_player_change_event = MagicMock()
        handler.handle_game_cancelled_event = MagicMock()
        handler.manager.lookup_player_for_websocket.return_value = None  # no player, no-op
        handler.handle_player_disconnected_event(websocket)
        handler.manager.lookup_player_for_websocket.assert_called_once_with(websocket)
        handler.manager.lookup_game.assert_not_called()
        handler.handle_game_player_change_event.assert_not_called()
        handler.handle_game_cancelled_event.assert_not_called()

    def test_handle_player_disconnected_event_no_game(self):
        player = MagicMock()
        websocket = MagicMock()
        handler = EventHandler(MagicMock())
        handler.handle_game_player_change_event = MagicMock()
        handler.handle_game_cancelled_event = MagicMock()
        handler.manager.lookup_player_for_websocket.return_value = player
        handler.manager.lookup_game.return_value = None
        handler.handle_player_disconnected_event(websocket)
        handler.manager.lookup_player_for_websocket.assert_called_once_with(websocket)
        handler.manager.lookup_game.assert_called_once_with(player=player)
        player.mark_disconnected.assert_called_once()
        handler.handle_game_player_change_event.assert_not_called()
        handler.handle_game_cancelled_event.assert_not_called()

    def test_handle_player_disconnected_event_with_game(self):
        comment = "Player leela disconnected"
        player = MagicMock(handle="leela")
        game = MagicMock()
        game.is_viable.return_value = True
        websocket = MagicMock()
        handler = EventHandler(MagicMock())
        handler.handle_game_player_change_event = MagicMock()
        handler.handle_game_cancelled_event = MagicMock()
        handler.manager.lookup_player_for_websocket.return_value = player
        handler.manager.lookup_game.return_value = game
        handler.handle_player_disconnected_event(websocket)
        handler.manager.lookup_player_for_websocket.assert_called_once_with(websocket)
        handler.manager.lookup_game.assert_called_once_with(player=player)
        player.mark_disconnected.assert_called_once()
        handler.handle_game_player_change_event.assert_called_once_with(game, comment)
        handler.handle_game_cancelled_event.assert_not_called()

    def test_handle_player_disconnected_event_not_viable(self):
        comment = "Player leela disconnected"
        player = MagicMock(handle="leela")
        game = MagicMock()
        game.is_viable.return_value = False
        websocket = MagicMock()
        handler = EventHandler(MagicMock())
        handler.handle_game_player_change_event = MagicMock()
        handler.handle_game_cancelled_event = MagicMock()
        handler.manager.lookup_player_for_websocket.return_value = player
        handler.manager.lookup_game.return_value = game
        handler.handle_player_disconnected_event(websocket)
        handler.manager.lookup_player_for_websocket.assert_called_once_with(websocket)
        handler.manager.lookup_game.assert_called_once_with(player=player)
        player.mark_disconnected.assert_called_once()
        handler.handle_game_player_change_event.assert_called_once_with(game, comment)
        handler.handle_game_cancelled_event.assert_called_once_with(game, CancelledReason.NOT_VIABLE, comment)

    def test_handle_player_idle_event(self):
        player = MagicMock()
        message = Message(MessageType.PLAYER_IDLE)
        handler = EventHandler(MagicMock())
        handler.queue.message = MagicMock()
        handler.handle_player_idle_event(player)
        handler.queue.message.assert_called_once_with(message, players=[player])
        player.mark_idle.assert_called_once()

    def test_handle_player_inactive_event(self):
        websocket = MagicMock()
        player = MagicMock(websocket=websocket)
        game = MagicMock()
        message = Message(MessageType.PLAYER_INACTIVE)
        handler = EventHandler(MagicMock())
        handler.handle_player_unregistered_event = MagicMock()
        handler.queue.message = MagicMock()
        handler.queue.disconnect = MagicMock()
        handler.manager.lookup_game.return_value = game
        handler.handle_player_inactive_event(player)
        player.mark_inactive.assert_called_once()
        handler.manager.lookup_game.assert_called_once_with(player=player)
        handler.queue.message.assert_called_once_with(message, players=[player])
        handler.queue.disconnect(websocket)
        handler.handle_player_unregistered_event.assert_called_once_with(player, game)

    def test_handle_player_message_received_event(self):
        fry = MagicMock()
        bender = MagicMock()
        context = PlayerMessageReceivedContext("leela", ["fry", "bender"], "hello")
        message = Message(MessageType.PLAYER_MESSAGE_RECEIVED, context=context)
        handler = EventHandler(MagicMock())
        handler.queue.message = MagicMock()
        handler.manager.lookup_player.side_effect = [fry, bender]
        handler.handle_player_message_received_event("leela", ["fry", "bender"], "hello")
        handler.manager.lookup_player.assert_has_calls([call(handle="fry"), call(handle="bender")])
        handler.queue.message.assert_called_once_with(message, players=[fry, bender])

    def test_handle_game_advertised_event(self):
        player = MagicMock()
        advertised = MagicMock()
        game = MagicMock()
        result = MagicMock()
        game.to_advertised_game.return_value = result
        context = GameAdvertisedContext(game=result)
        message = Message(MessageType.GAME_ADVERTISED, context=context)
        handler = EventHandler(MagicMock())
        handler.manager.track_game.return_value = game
        handler.handle_game_invitation_event = MagicMock()
        handler.handle_game_joined_event = MagicMock()
        handler.queue.message = MagicMock()
        handler.handle_game_advertised_event(player, advertised)
        handler.manager.track_game.assert_called_once_with(player, advertised)
        handler.handle_game_joined_event.assert_called_once_with(player, game=game)
        handler.handle_game_invitation_event.assert_called_once_with(game)
        handler.queue.message.assert_called_once_with(message, players=[player])

    def test_handle_game_invitation_event_none_invited(self):
        game = MagicMock(invited_handles=[])
        handler = EventHandler(MagicMock())
        handler.queue.message = MagicMock()
        handler.handle_game_invitation_event(game)
        handler.manager.lookup_player.assert_not_called()
        handler.queue.message.assert_not_called()

    def test_handle_game_invitation_event_with_invited(self):
        fry = MagicMock()
        bender = MagicMock()
        game = MagicMock(invited_handles=["fry", "bender"])
        advertised = MagicMock()
        game.to_advertised_game.return_value = advertised
        context = GameInvitationContext(advertised)
        message = Message(MessageType.GAME_INVITATION, context=context)
        handler = EventHandler(MagicMock())
        handler.queue.message = MagicMock()
        handler.manager.lookup_player.side_effect = [fry, bender]
        handler.handle_game_invitation_event(game)
        handler.manager.lookup_player.assert_has_calls([call(handle="fry"), call(handle="bender")])
        handler.queue.message.assert_called_once_with(message, players=[fry, bender])

    def test_handle_game_joined_event_bad_call(self):
        player = MagicMock()
        handler = EventHandler(MagicMock())
        with pytest.raises(ProcessingError, match=r"Invalid arguments"):
            handler.handle_game_joined_event(player, game_id=None, game=None)  # need to pass either id or game

    def test_handle_game_joined_event_not_found(self):
        player = MagicMock()
        handler = EventHandler(MagicMock())
        handler.manager.lookup_game.return_value = None
        with pytest.raises(ProcessingError, match=r"Unknown or invalid game"):
            handler.handle_game_joined_event(player, game_id="game_id")
        handler.manager.lookup_game.assert_called_once_with(game_id="game_id")

    def test_handle_game_joined_event_not_available(self):
        player = MagicMock()
        game = MagicMock()
        game.is_available.return_value = False
        handler = EventHandler(MagicMock())
        handler.manager.lookup_game.return_value = game
        with pytest.raises(ProcessingError, match=r"Unknown or invalid game"):
            handler.handle_game_joined_event(player, game_id="game_id")
        handler.manager.lookup_game.assert_called_once_with(game_id="game_id")
        game.is_available.assert_called_once_with(player)

    def test_handle_game_joined_event_pending_by_id(self):
        player = MagicMock()
        game = MagicMock(game_id="id")
        game.is_available.return_value = True
        game.is_fully_joined.return_value = False
        context = GameJoinedContext("id")
        message = Message(MessageType.GAME_JOINED, context=context)
        handler = EventHandler(MagicMock())
        handler.queue.message = MagicMock()
        handler.manager.lookup_game.return_value = game
        handler.handle_game_started_event = MagicMock()
        handler.handle_game_joined_event(player, game_id="game_id")
        handler.manager.lookup_game.assert_called_once_with(game_id="game_id")
        game.is_available.assert_called_once_with(player)
        game.mark_active.assert_called_once()
        player.mark_joined.assert_called_once_with(game)
        game.mark_joined.assert_called_once_with(player)
        handler.queue.message.assert_called_once_with(message, players=[player])
        handler.handle_game_started_event.assert_not_called()

    def test_handle_game_joined_event_pending_for_game(self):
        player = MagicMock()
        game = MagicMock(game_id="id")
        game.is_available.return_value = True
        game.is_fully_joined.return_value = False
        context = GameJoinedContext("id")
        message = Message(MessageType.GAME_JOINED, context=context)
        handler = EventHandler(MagicMock())
        handler.queue.message = MagicMock()
        handler.manager.lookup_game.return_value = game
        handler.handle_game_started_event = MagicMock()
        handler.handle_game_joined_event(player, game=game)
        handler.manager.lookup_game.assert_not_called()
        game.is_available.assert_not_called()
        game.mark_active.assert_called_once()
        player.mark_joined.assert_called_once_with(game)
        game.mark_joined.assert_called_once_with(player)
        handler.queue.message.assert_called_once_with(message, players=[player])
        handler.handle_game_started_event.assert_not_called()

    @patch("apologiesserver.event.config")
    def test_handle_game_joined_event_fully_joined(self, config):
        config.return_value = MagicMock(in_progress_game_limit=5)
        player = MagicMock()
        game = MagicMock(game_id="id")
        game.is_available.return_value = True
        game.is_fully_joined.return_value = True
        context = GameJoinedContext("id")
        message = Message(MessageType.GAME_JOINED, context=context)
        handler = EventHandler(MagicMock())
        handler.queue.message = MagicMock()
        handler.manager.in_progress_game_count.return_value = 4
        handler.manager.lookup_game.return_value = game
        handler.handle_game_started_event = MagicMock()
        handler.handle_game_joined_event(player, game=game)
        handler.manager.lookup_game.assert_not_called()
        game.is_available.assert_not_called()
        game.mark_active.assert_called_once()
        player.mark_joined.assert_called_once_with(game)
        game.mark_joined.assert_called_once_with(player)
        handler.queue.message.assert_called_once_with(message, players=[player])
        handler.handle_game_started_event.assert_called_once_with(game)

    @patch("apologiesserver.event.config")
    def test_handle_game_joined_event_game_limit(self, config):
        config.return_value = MagicMock(in_progress_game_limit=5)
        player = MagicMock()
        game = MagicMock(game_id="id")
        game.is_available.return_value = True
        game.is_fully_joined.return_value = True
        context = GameJoinedContext("id")
        message = Message(MessageType.GAME_JOINED, context=context)
        handler = EventHandler(MagicMock())
        handler.queue.message = MagicMock()
        handler.manager.in_progress_game_count.return_value = 5
        handler.manager.lookup_game.return_value = game
        handler.handle_game_started_event = MagicMock()
        handler.handle_game_joined_event(player, game=game)
        handler.manager.lookup_game.assert_not_called()
        game.is_available.assert_not_called()
        game.mark_active.assert_called_once()
        player.mark_joined.assert_called_once_with(game)
        game.mark_joined.assert_called_once_with(player)
        handler.queue.message.assert_called_once_with(message, players=[player])
        handler.handle_game_started_event.assert_not_called()  # because in-progress limit was reached

    def test_handle_game_started_event(self):
        player = MagicMock()
        game = MagicMock()
        message = Message(MessageType.GAME_STARTED)
        handler = EventHandler(MagicMock())
        handler.queue.message = MagicMock()
        handler.handle_game_player_change_event = MagicMock()
        handler.handle_game_state_change_event = MagicMock()
        handler.manager.lookup_game_players.return_value = [player]
        handler.handle_game_started_event(game)
        game.mark_active.assert_called_once()
        game.mark_started.assert_called_once()
        player.mark_playing.assert_called_once()
        handler.manager.lookup_game_players.assert_called_once_with(game)
        handler.queue.message.assert_called_once_with(message, players=[player])
        handler.handle_game_player_change_event.assert_called_once_with(game, "Game started")
        handler.handle_game_state_change_event.assert_called_once_with(game)

    def test_handle_game_cancelled_event_notify(self):
        player = MagicMock()
        game = MagicMock()
        context = GameCancelledContext(CancelledReason.SHUTDOWN, "comment")
        message = Message(MessageType.GAME_CANCELLED, context=context)
        handler = EventHandler(MagicMock())
        handler.queue.message = MagicMock()
        handler.handle_game_player_change_event = MagicMock()
        handler.handle_game_state_change_event = MagicMock()
        handler.manager.lookup_game_players.return_value = [player]
        handler.handle_game_cancelled_event(game, CancelledReason.SHUTDOWN, "comment", notify=True)
        player.mark_quit.assert_called_once()
        game.mark_cancelled.assert_called_once()
        handler.manager.lookup_game_players.assert_called_once_with(game)
        handler.queue.message.assert_called_once_with(message, players=[player])
        handler.handle_game_state_change_event.assert_called_once_with(game)

    def test_handle_game_cancelled_event_no_notify(self):
        player = MagicMock()
        game = MagicMock()
        handler = EventHandler(MagicMock())
        handler.queue.message = MagicMock()
        handler.handle_game_player_change_event = MagicMock()
        handler.handle_game_state_change_event = MagicMock()
        handler.manager.lookup_game_players.return_value = [player]
        handler.handle_game_cancelled_event(game, CancelledReason.SHUTDOWN, "comment", notify=False)
        player.mark_quit.assert_called_once()
        game.mark_cancelled.assert_called_once()
        handler.manager.lookup_game_players.assert_called_once_with(game)
        handler.queue.message.assert_not_called()  # notification disabled
        handler.handle_game_state_change_event.assert_not_called()  # notification disabled

    def test_handle_game_completed_event(self):
        player = MagicMock()
        game = MagicMock()
        context = GameCompletedContext("comment")
        message = Message(MessageType.GAME_COMPLETED, context=context)
        handler = EventHandler(MagicMock())
        handler.queue.message = MagicMock()
        handler.handle_game_player_change_event = MagicMock()
        handler.handle_game_state_change_event = MagicMock()
        handler.manager.lookup_game_players.return_value = [player]
        handler.handle_game_completed_event(game, "comment")
        player.mark_quit.assert_called_once()
        game.mark_completed.assert_called_once()
        handler.manager.lookup_game_players.assert_called_once_with(game)
        handler.queue.message.assert_called_once_with(message, players=[player])
        handler.handle_game_state_change_event.assert_called_once_with(game)

    def test_handle_game_idle_event(self):
        player = MagicMock()
        game = MagicMock()
        message = Message(MessageType.GAME_IDLE)
        handler = EventHandler(MagicMock())
        handler.queue.message = MagicMock()
        handler.manager.lookup_game_players.return_value = [player]
        handler.handle_game_idle_event(game)
        handler.queue.message.assert_called_once_with(message, players=[player])

    def test_handle_game_inactive_event(self):
        game = MagicMock()
        handler = EventHandler(MagicMock())
        handler.handle_game_cancelled_event = MagicMock()
        handler.handle_game_inactive_event(game)
        game.mark_inactive.assert_called_once()
        handler.handle_game_cancelled_event.assert_called_once_with(game, CancelledReason.INACTIVE)

    def test_handle_game_obsolete_event(self):
        game = MagicMock()
        handler = EventHandler(MagicMock())
        handler.handle_game_obsolete_event(game)
        handler.manager.delete_game.assert_called_once_with(game)

    def test_handle_game_player_quit_event_viable(self):
        comment = "Player leela quit"
        player = MagicMock(handle="leela")
        game = MagicMock()
        game.is_viable.return_value = True
        handler = EventHandler(MagicMock())
        handler.handle_game_player_change_event = MagicMock()
        handler.handle_game_cancelled_event = MagicMock()
        handler.handle_game_player_quit_event(player, game)
        game.mark_active.assert_called_once()
        player.mark_quit.assert_called_once()
        handler.handle_game_player_change_event.assert_called_once_with(game, comment)
        handler.handle_game_cancelled_event.assert_not_called()

    def test_handle_game_player_quit_event_not_viable(self):
        comment = "Player leela quit"
        player = MagicMock(handle="leela")
        game = MagicMock()
        game.is_viable.return_value = False
        handler = EventHandler(MagicMock())
        handler.handle_game_player_change_event = MagicMock()
        handler.handle_game_cancelled_event = MagicMock()
        handler.handle_game_player_quit_event(player, game)
        game.mark_active.assert_called_once()
        player.mark_quit.assert_called_once()
        handler.handle_game_player_change_event.assert_called_once_with(game, comment)
        handler.handle_game_cancelled_event.assert_called_once_with(game, CancelledReason.NOT_VIABLE, comment)

    def test_handle_game_execute_move_event_completed(self):
        player = MagicMock()
        game = MagicMock()
        game.execute_move.return_value = (True, "comment")
        handler = EventHandler(MagicMock())
        handler.handle_game_completed_event = MagicMock()
        handler.handle_game_player_turn_event = MagicMock()
        handler.handle_game_state_change_event = MagicMock()
        handler.handle_game_execute_move_event(player, game, "move_id")
        game.mark_active.assert_called_once()
        game.execute_move.assert_called_once_with(player, "move_id")
        handler.handle_game_completed_event.assert_called_once_with(game, "comment")
        game.get_next_turn.assert_not_called()
        handler.handle_game_player_turn_event.assert_not_called()
        handler.handle_game_state_change_event.assert_not_called()

    def test_handle_game_execute_move_event_not_completed(self):
        player = MagicMock()
        game = MagicMock()
        moves = [MagicMock()]
        game.execute_move.return_value = (False, "comment")
        game.get_next_turn.return_value = (player, moves)
        handler = EventHandler(MagicMock())
        handler.handle_game_completed_event = MagicMock()
        handler.handle_game_player_turn_event = MagicMock()
        handler.handle_game_state_change_event = MagicMock()
        handler.handle_game_execute_move_event(player, game, "move_id")
        game.mark_active.assert_called_once()
        game.execute_move.assert_called_once_with(player, "move_id")
        handler.handle_game_completed_event.assert_not_called()
        game.get_next_turn.assert_called_once()
        handler.handle_game_player_turn_event.assert_called_once_with(player, moves)
        handler.handle_game_state_change_event.assert_called_once_with(game)

    def test_handle_game_player_change_event(self):
        game_player = MagicMock()
        player = MagicMock()
        game = MagicMock()
        game.get_game_players.return_value = [game_player]
        context = GamePlayerChangeContext(comment="comment", players=[game_player])
        message = Message(MessageType.GAME_PLAYER_CHANGE, context=context)
        handler = EventHandler(MagicMock())
        handler.queue.message = MagicMock()
        handler.manager.lookup_game_players.return_value = [player]
        handler.handle_game_player_change_event(game, "comment")
        handler.queue.message.assert_called_once_with(message, players=[player])

    @patch("apologiesserver.event.GameStateChangeContext")
    def test_handle_game_state_change_event_specific_player(self, game_state_change_context):
        context = GameStateChangeContext(player=None, opponents=None)
        player = MagicMock()
        view = MagicMock()
        game = MagicMock()
        game.get_player_view.return_value = view
        game_state_change_context.for_view.return_value = context
        message = Message(MessageType.GAME_STATE_CHANGE, context=context)
        handler = EventHandler(MagicMock())
        handler.queue.message = MagicMock()
        handler.handle_game_state_change_event(game, player)
        game.mark_active.assert_called_once()
        handler.queue.message.assert_called_once_with(message, players=[player])
        handler.manager.lookup_game_players.assert_not_called()

    @patch("apologiesserver.event.GameStateChangeContext")
    def test_handle_game_state_change_event_game_players(self, game_state_change_context):
        context = GameStateChangeContext(player=None, opponents=None)
        player = MagicMock()
        view = MagicMock()
        game = MagicMock()
        game.get_player_view.return_value = view
        game_state_change_context.for_view.return_value = context
        message = Message(MessageType.GAME_STATE_CHANGE, context=context)
        handler = EventHandler(MagicMock())
        handler.manager.lookup_game_players.return_value = [player]
        handler.queue.message = MagicMock()
        handler.handle_game_state_change_event(game)
        game.mark_active.assert_called_once()
        handler.queue.message.assert_called_once_with(message, players=[player])
        handler.manager.lookup_game_players.assert_called_once_with(game)

    @patch("apologiesserver.event.GamePlayerTurnContext")
    def test_handle_game_player_turn_event(self, game_player_turn_context):
        context = GamePlayerTurnContext(None, None)
        player = MagicMock()
        moves = [MagicMock()]
        game_player_turn_context.for_moves.return_value = context
        message = Message(MessageType.GAME_PLAYER_TURN, context=context)
        handler = EventHandler(MagicMock())
        handler.queue.message = MagicMock()
        handler.handle_game_player_turn_event(player, moves)
        handler.queue.message.assert_called_once_with(message, players=[player])
