# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=redefined-outer-name,wildcard-import

# TODO: double-check that all validations (especially game/user limits) are tested completely

from unittest.mock import MagicMock

import pytest
from apologies.game import GameMode
from asynctest import CoroutineMock
from asynctest import MagicMock as AsyncMock
from asynctest import patch

from apologiesserver.event import EventHandler, RequestContext, TaskQueue
from apologiesserver.interface import *


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
        handler.handle_game_joined_event.assert_called_once_with(player, "game")

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
