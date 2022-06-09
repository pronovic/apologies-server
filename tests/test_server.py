# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=redefined-outer-name

import asyncio
import os
import signal
import sys
from unittest.mock import MagicMock, call

import pytest
from asynctest import MagicMock as AsyncMock
from asynctest import patch
from websockets.exceptions import ConnectionClosed

from apologiesserver.event import EventHandler, RequestContext
from apologiesserver.interface import FailureReason, Message, MessageType, ProcessingError, RequestFailedContext
from apologiesserver.server import (
    _add_signal_handlers,
    _handle_connect,
    _handle_connection,
    _handle_data,
    _handle_disconnect,
    _handle_exception,
    _handle_message,
    _handle_shutdown,
    _lookup_method,
    _run_server,
    _schedule_tasks,
    _websocket_server,
    server,
)

from .util import mock_handler

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures/test_server")


@pytest.fixture
def data():
    data = {}
    for f in os.listdir(FIXTURE_DIR):
        p = os.path.join(FIXTURE_DIR, f)
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as r:
                data[f] = r.read()
    return data


class TestFunctions:
    """
    Test Python functions.
    """

    @patch("apologiesserver.server.signal.signal")
    def test_add_signal_handlers(self, signaler):
        stop = AsyncMock()
        set_result = AsyncMock()
        stop.set_result = set_result
        loop = AsyncMock()
        loop.create_future.return_value = stop
        assert _add_signal_handlers(loop) is stop
        if sys.platform == "win32":
            assert [signal.SIGTERM, signal.SIGINT] == [
                c.args[0] for c in signaler.call_args_list
            ]  # confirm all signals are handled
            signaler.call_args_list[0].args[1]("x", "y")  # execute the handler with dummy arguments (which are ignored)
            stop.set_result.assert_called_once_with(None)  # confirm that the handler sets the stop future result properly
        else:
            loop.add_signal_handler.assert_has_calls(
                [
                    call(signal.SIGHUP, set_result, None),  # pylint: disable=no-member
                    call(signal.SIGTERM, set_result, None),
                    call(signal.SIGINT, set_result, None),
                ]
            )

    # noinspection PyCallingNonCallable
    @patch("apologiesserver.server.scheduled_tasks")
    def test_schedule_tasks(self, scheduled_tasks):
        task = AsyncMock()
        scheduled_tasks.return_value = [task]
        loop = AsyncMock()
        _schedule_tasks(loop)
        loop.create_task.assert_called_with(task())

    @patch("apologiesserver.server.config")
    @patch("apologiesserver.server._websocket_server")
    def test_run_server(self, websocket_server, config):
        # I'm not entirely sure I'm testing this properly.
        # I can't find a good way to prove that _websocket_server(stop) was passed to run_until_complete
        # But, the function is so short that I can eyeball it, and it will either work or it won't when run by hand
        config.return_value = MagicMock(server_host="host", server_port=1234, close_timeout_sec=8)
        stop = asyncio.Future()
        stop.set_result(None)
        loop = AsyncMock()
        _run_server(loop, stop)
        loop.run_until_complete.assert_called_once()
        websocket_server.assert_called_once_with(stop=stop, host="host", port=1234, close_timeout_sec=2)
        loop.stop.assert_called_once()
        loop.close.assert_called_once()

    @patch("apologiesserver.server._run_server")
    @patch("apologiesserver.server._schedule_tasks")
    @patch("apologiesserver.server._add_signal_handlers")
    @patch("apologiesserver.server.asyncio.get_event_loop")
    @patch("apologiesserver.server.config")
    def test_server(self, config, get_event_loop, add_signal_handlers, schedule_tasks, run_server):
        stop = MagicMock()
        loop = MagicMock()
        system_config = MagicMock()
        config.return_value = system_config
        get_event_loop.return_value = loop
        add_signal_handlers.return_value = stop
        server()
        system_config.to_json.assert_called_once()
        add_signal_handlers.assert_called_once_with(loop)
        schedule_tasks.assert_called_once_with(loop)
        run_server.assert_called_once_with(loop, stop)

    def test_handle_message_register(self):
        handler = MagicMock()
        message = MagicMock(message=MessageType.REGISTER_PLAYER)
        websocket = MagicMock()
        _handle_message(handler, message, websocket)
        handler.handle_register_player_request.assert_called_once_with(message, websocket)

    @patch("apologiesserver.server._lookup_method")
    def test_handle_message(self, lookup_method):
        method = MagicMock()
        lookup_method.return_value = method
        handler = MagicMock()
        message = MagicMock(message=MessageType.LIST_PLAYERS, player_id="player_id")  # anything other than REGISTER_PLAYER
        websocket = MagicMock()
        player = MagicMock(game_id="game_id")
        game = MagicMock()
        request = RequestContext(message, websocket, player, game)
        handler.manager.lookup_player.return_value = player
        handler.manager.lookup_game.return_value = game
        _handle_message(handler, message, websocket)
        handler.manager.lookup_player.assert_called_once_with(player_id="player_id")
        handler.manager.mark_active.assert_called_once_with(player)
        handler.manager.lookup_game.assert_called_once_with(game_id="game_id")
        lookup_method.assert_called_once_with(handler, MessageType.LIST_PLAYERS)
        method.assert_called_once_with(request)

    @patch("apologiesserver.server._lookup_method")
    def test_handle_message_no_player(self, lookup_method):
        handler = MagicMock()
        message = MagicMock(message=MessageType.LIST_PLAYERS, player_id="player_id")  # anything other than REGISTER_PLAYER
        websocket = MagicMock()
        handler.manager.lookup_player.return_value = None
        with pytest.raises(ProcessingError, match=r"Unknown or invalid player"):
            _handle_message(handler, message, websocket)
        handler.manager.lookup_player.assert_called_once_with(player_id="player_id")
        handler.manager.lookup_game.assert_not_called()
        lookup_method.assert_not_called()

    @patch("apologiesserver.server._lookup_method")
    def test_handle_message_no_player_reregister(self, lookup_method):
        handler = MagicMock()
        message = MagicMock(message=MessageType.REREGISTER_PLAYER, player_id="player_id")  # special case
        websocket = MagicMock()
        handler.manager.lookup_player.return_value = None
        _handle_message(handler, message, websocket)
        handler.handle_register_player_request.assert_called_once_with(message, websocket)
        handler.manager.lookup_player.assert_called_once_with(player_id="player_id")
        handler.manager.lookup_game.assert_not_called()
        lookup_method.assert_not_called()

    def test_lookup_method_invalid(self):
        with pytest.raises(ProcessingError, match=r"Invalid request REGISTER_PLAYER"):
            _lookup_method(MagicMock(), MessageType.REGISTER_PLAYER)  # this is a special case
        with pytest.raises(ProcessingError, match=r"Invalid request SERVER_SHUTDOWN"):
            _lookup_method(MagicMock(), MessageType.SERVER_SHUTDOWN)  # this isn't a request

    # pylint: disable=comparison-with-callable
    def test_lookup_method_valid(self):
        handler = EventHandler(MagicMock())
        assert _lookup_method(handler, MessageType.REREGISTER_PLAYER) == handler.handle_reregister_player_request
        assert _lookup_method(handler, MessageType.UNREGISTER_PLAYER) == handler.handle_unregister_player_request
        assert _lookup_method(handler, MessageType.LIST_PLAYERS) == handler.handle_list_players_request
        assert _lookup_method(handler, MessageType.ADVERTISE_GAME) == handler.handle_advertise_game_request
        assert _lookup_method(handler, MessageType.LIST_AVAILABLE_GAMES) == handler.handle_list_available_games_request
        assert _lookup_method(handler, MessageType.JOIN_GAME) == handler.handle_join_game_request
        assert _lookup_method(handler, MessageType.QUIT_GAME) == handler.handle_quit_game_request
        assert _lookup_method(handler, MessageType.START_GAME) == handler.handle_start_game_request
        assert _lookup_method(handler, MessageType.CANCEL_GAME) == handler.handle_cancel_game_request
        assert _lookup_method(handler, MessageType.EXECUTE_MOVE) == handler.handle_execute_move_request
        assert _lookup_method(handler, MessageType.OPTIMAL_MOVE) == handler.handle_optimal_move_request
        assert _lookup_method(handler, MessageType.RETRIEVE_GAME_STATE) == handler.handle_retrieve_game_state_request
        assert _lookup_method(handler, MessageType.SEND_MESSAGE) == handler.handle_send_message_request


class TestCoroutines:
    """
    Test Python coroutines.
    """

    pytestmark = pytest.mark.asyncio

    @patch("apologiesserver.server.close")
    @patch("apologiesserver.server.send")
    async def test_handle_exception_processing_error(self, send, close):
        exception = ProcessingError(FailureReason.INVALID_PLAYER)
        websocket = AsyncMock()
        context = RequestFailedContext(FailureReason.INVALID_PLAYER, FailureReason.INVALID_PLAYER.value)
        message = Message(MessageType.REQUEST_FAILED, context=context)
        json = message.to_json()
        await _handle_exception(exception, websocket)
        send.assert_awaited_once_with(websocket, json)
        close.assert_not_awaited()

    @patch("apologiesserver.server.close")
    @patch("apologiesserver.server.send")
    async def test_handle_exception_processing_error_websocket_limit(self, send, close):
        exception = ProcessingError(FailureReason.WEBSOCKET_LIMIT)
        websocket = AsyncMock()
        context = RequestFailedContext(FailureReason.WEBSOCKET_LIMIT, FailureReason.WEBSOCKET_LIMIT.value)
        message = Message(MessageType.REQUEST_FAILED, context=context)
        json = message.to_json()
        await _handle_exception(exception, websocket)
        send.assert_awaited_once_with(websocket, json)
        close.assert_awaited_once_with(websocket)

    @patch("apologiesserver.server.close")
    @patch("apologiesserver.server.send")
    async def test_handle_exception_processing_error_comment(self, send, close):
        exception = ProcessingError(FailureReason.INVALID_PLAYER, "comment")
        websocket = AsyncMock()
        context = RequestFailedContext(FailureReason.INVALID_PLAYER, "comment")
        message = Message(MessageType.REQUEST_FAILED, context=context)
        json = message.to_json()
        await _handle_exception(exception, websocket)
        send.assert_awaited_once_with(websocket, json)
        close.assert_not_awaited()

    @patch("apologiesserver.server.close")
    @patch("apologiesserver.server.send")
    async def test_handle_exception_value_error(self, send, close):
        exception = ValueError("Hello!")
        websocket = AsyncMock()
        context = RequestFailedContext(FailureReason.INVALID_REQUEST, "Hello!")
        message = Message(MessageType.REQUEST_FAILED, context=context)
        json = message.to_json()
        await _handle_exception(exception, websocket)
        send.assert_awaited_once_with(websocket, json)
        close.assert_not_awaited()

    @patch("apologiesserver.server.close")
    @patch("apologiesserver.server.send")
    async def test_handle_exception_exception(self, send, close):
        exception = Exception("Hello!")
        websocket = AsyncMock()
        context = RequestFailedContext(FailureReason.INTERNAL_ERROR, FailureReason.INTERNAL_ERROR.value)
        message = Message(MessageType.REQUEST_FAILED, context=context)
        json = message.to_json()
        await _handle_exception(exception, websocket)
        send.assert_awaited_once_with(websocket, json)
        close.assert_not_awaited()

    @patch("apologiesserver.server.close")
    @patch("apologiesserver.server.send")
    async def test_handle_exception_fail(self, send, close):
        # this just confirms that send failures aren't propogated to the caller (we intentionally ignore them)
        exception = ProcessingError(FailureReason.INVALID_PLAYER)
        websocket = AsyncMock()
        send.side_effect = Exception("Send failed!")
        context = RequestFailedContext(FailureReason.INVALID_PLAYER, FailureReason.INVALID_PLAYER.value)
        message = Message(MessageType.REQUEST_FAILED, context=context)
        json = message.to_json()
        await _handle_exception(exception, websocket)
        send.assert_awaited_once_with(websocket, json)
        close.assert_not_awaited()

    @patch("apologiesserver.server._handle_message")
    @patch("apologiesserver.server.EventHandler")
    @patch("apologiesserver.server.manager")
    async def test_handle_data(self, manager, event_handler, handle_message, data):
        handler = mock_handler()
        manager.return_value = handler.manager
        event_handler.return_value = handler
        websocket = AsyncMock()
        json = data["list.json"]
        message = Message.for_json(json)
        await _handle_data(json, websocket)
        event_handler.assert_called_once_with(manager.return_value)
        handler.manager.lock.assert_awaited()
        handle_message.assert_called_once_with(handler, message, websocket)
        handler.execute_tasks.assert_awaited_once()

    @patch("apologiesserver.server.EventHandler")
    @patch("apologiesserver.server.manager")
    async def test_handle_connect(self, manager, event_handler):
        handler = mock_handler()
        manager.return_value = handler.manager
        event_handler.return_value = handler
        websocket = AsyncMock()
        await _handle_connect(websocket)
        event_handler.assert_called_once_with(manager.return_value)
        handler.manager.lock.assert_awaited()
        handler.handle_websocket_connected_event.assert_called_once_with(websocket)
        handler.execute_tasks.assert_awaited_once()

    @patch("apologiesserver.server.EventHandler")
    @patch("apologiesserver.server.manager")
    async def test_handle_disconnect(self, manager, event_handler):
        handler = mock_handler()
        manager.return_value = handler.manager
        event_handler.return_value = handler
        websocket = AsyncMock()
        await _handle_disconnect(websocket)
        event_handler.assert_called_once_with(manager.return_value)
        handler.manager.lock.assert_awaited()
        handler.handle_websocket_disconnected_event.assert_called_once_with(websocket)
        handler.execute_tasks.assert_awaited_once()

    @patch("apologiesserver.server._handle_disconnect")
    @patch("apologiesserver.server._handle_connect")
    @patch("apologiesserver.server._handle_exception")
    @patch("apologiesserver.server._handle_data")
    async def test_handle_connection(self, handle_data, handle_exception, handle_connect, handle_disconnect):
        data = b"test data"
        websocket = AsyncMock()
        websocket.__aiter__.return_value = [data]
        await _handle_connection(websocket, "path")  # path is unused
        handle_data.assert_called_once_with(data, websocket)
        handle_connect.assert_called_once_with(websocket)
        handle_disconnect.assert_called_once_with(websocket)
        handle_exception.assert_not_called()

    @patch("apologiesserver.server._handle_disconnect")
    @patch("apologiesserver.server._handle_connect")
    @patch("apologiesserver.server._handle_exception")
    @patch("apologiesserver.server._handle_data")
    async def test_handle_connection_exception(self, handle_data, handle_exception, handle_connect, handle_disconnect):
        data = b"test data"
        websocket = AsyncMock()
        websocket.__aiter__.return_value = [data]
        exception = ProcessingError(FailureReason.INTERNAL_ERROR)
        handle_data.side_effect = exception
        await _handle_connection(websocket, "path")  # path is unused
        handle_data.assert_called_once_with(data, websocket)
        handle_connect.assert_called_once_with(websocket)
        handle_disconnect.assert_called_once_with(websocket)
        handle_exception.assert_called_once_with(exception, websocket)

    @patch("apologiesserver.server._handle_disconnect")
    @patch("apologiesserver.server._handle_connect")
    @patch("apologiesserver.server._handle_exception")
    @patch("apologiesserver.server._handle_data")
    async def test_handle_connection_shutdown(self, handle_data, handle_exception, handle_connect, handle_disconnect):
        websocket = AsyncMock()
        exception = ConnectionClosed(None, None)
        websocket.__aiter__.side_effect = exception  # the wait on the websocket is what throws the connection closed
        handle_data.side_effect = exception
        await _handle_connection(websocket, "path")  # path is unused
        handle_data.assert_not_called()
        handle_connect.assert_called_once_with(websocket)
        handle_disconnect.assert_called_once_with(websocket)
        handle_exception.assert_not_called()

    @patch("apologiesserver.server.EventHandler")
    @patch("apologiesserver.server.manager")
    async def test_handle_shutdown(self, manager, event_handler):
        handler = mock_handler()
        manager.return_value = handler.manager
        event_handler.return_value = handler
        await _handle_shutdown()
        event_handler.assert_called_once_with(manager.return_value)
        handler.manager.lock.assert_awaited()
        handler.handle_server_shutdown_event.assert_called_once()
        handler.execute_tasks.assert_awaited_once()

    @patch("apologiesserver.server._handle_shutdown")
    @patch("apologiesserver.server._handle_connection")
    @patch("apologiesserver.server.serve")
    async def test_websocket_server(self, serve, handle_connection, handle_shutdown):
        stop = asyncio.Future()
        stop.set_result(None)
        await _websocket_server(stop, "host", 1234, 4)
        serve.assert_called_with(handle_connection, host="host", port=1234, close_timeout=4)
        handle_shutdown.assert_awaited()
        # unfortunately, we can't prove that stop() was awaited, but in this case it's easy to eyeball in the code
