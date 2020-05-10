# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=redefined-outer-name

import asyncio
import os
import signal
from unittest.mock import MagicMock, call

import pytest
from asynctest import CoroutineMock
from asynctest import MagicMock as AsyncMock
from asynctest import patch
from websockets.http import Headers

from apologiesserver.interface import FailureReason, Message, ProcessingError
from apologiesserver.server import (
    _add_signal_handlers,
    _handle_connection,
    _handle_message,
    _parse_authorization,
    _run_server,
    _schedule_tasks,
    _websocket_server,
    server,
)

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

    def test_parse_authorization_empty(self):
        headers = Headers()
        headers["Authorization"] = "bogus"
        websocket = MagicMock(request_headers=headers)
        with pytest.raises(ProcessingError, match=r"Missing or invalid authorization header"):
            _parse_authorization(websocket)

    def test_parse_authorization_invalid(self):
        headers = Headers()
        headers["Authorization"] = "bogus"
        websocket = MagicMock(request_headers=headers)
        with pytest.raises(ProcessingError, match=r"Missing or invalid authorization header"):
            _parse_authorization(websocket)

    def test_parse_authorization_valid_upper(self):
        headers = Headers()
        headers["AUTHORIZATION"] = "PLAYER abcde"
        websocket = MagicMock(request_headers=headers)
        assert _parse_authorization(websocket) == "abcde"

    def test_parse_authorization_valid_lower(self):
        headers = Headers()
        headers["authorization"] = "player abcde"
        websocket = MagicMock(request_headers=headers)
        assert _parse_authorization(websocket) == "abcde"

    def test_parse_authorization_mixed(self):
        headers = Headers()
        headers["Authorization"] = "Player abcde"
        websocket = MagicMock(request_headers=headers)
        assert _parse_authorization(websocket) == "abcde"

    def test_parse_authorization_whitespace(self):
        headers = Headers()
        headers["authorization"] = "  Player    abcde    "
        websocket = MagicMock(request_headers=headers)
        assert _parse_authorization(websocket) == "abcde"

    def test_add_signal_handlers(self):
        stop = AsyncMock()
        set_result = AsyncMock()
        stop.set_result = set_result
        loop = AsyncMock()
        loop.create_future.return_value = stop
        assert _add_signal_handlers(loop) is stop
        loop.add_signal_handler.assert_has_calls(
            [call(signal.SIGHUP, set_result, None), call(signal.SIGTERM, set_result, None), call(signal.SIGINT, set_result, None),]
        )

    # noinspection PyCallingNonCallable
    @patch("apologiesserver.server.scheduled_tasks")
    def test_schedule_tasks(self, scheduled_tasks):
        task = AsyncMock()
        scheduled_tasks.return_value = [task]
        loop = AsyncMock()
        _schedule_tasks(loop)
        loop.create_task.assert_called_with(task())

    @patch("apologiesserver.server._websocket_server")
    def test_run_server(self, websocket_server):
        # I'm not entirely sure I'm testing this properly.
        # I can't find a good way to prove that _websocket_server(stop) was passed to run_until_complete
        # But, the function is so short that I can eyeball it, and it will either work or it won't when run by hand
        stop = asyncio.Future()
        stop.set_result(None)
        loop = AsyncMock()
        _run_server(loop, stop)
        loop.run_until_complete.assert_called_once()
        websocket_server.assert_called_once_with(stop)
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


class TestCoroutines:
    """
    Test Python coroutines.
    """

    pytestmark = pytest.mark.asyncio

    @patch("apologiesserver.server.handle_exception")
    @patch("apologiesserver.server.handle_message")
    @patch("apologiesserver.server.Message")
    async def test_handle_message_invalid_message(self, message, handle_message, handle_exception, data):
        exception = ValueError("Invalid message")
        message.for_json.side_effect = exception
        websocket = AsyncMock()
        data = data["register.json"]
        await _handle_message(data, websocket)
        handle_message.assert_not_called()
        handle_exception.assert_called_with(exception, websocket)

    @patch("apologiesserver.server.handle_exception")
    @patch("apologiesserver.server.handle_message")
    @patch("apologiesserver.server.handle_register")
    async def test_handle_message_exception(self, handle_register, handle_message, handle_exception, data):
        exception = ProcessingError(FailureReason.INVALID_PLAYER)
        handle_register.side_effect = exception
        websocket = AsyncMock()
        data = data["register.json"]
        message = Message.for_json(data)
        await _handle_message(data, websocket)
        handle_register.assert_called_once_with(message, websocket)
        handle_message.assert_not_called()
        handle_exception.assert_called_with(exception, websocket)

    @patch("apologiesserver.server._parse_authorization")
    @patch("apologiesserver.server.handle_exception")
    @patch("apologiesserver.server.handle_message")
    @patch("apologiesserver.server.handle_register")
    async def test_handle_message_register(self, handle_register, handle_message, handle_exception, parse_authorization, data):
        queue = AsyncMock()
        queue.send = CoroutineMock()
        handle_register.return_value = queue
        websocket = AsyncMock()
        data = data["register.json"]
        message = Message.for_json(data)
        await _handle_message(data, websocket)
        queue.send.assert_awaited_once()
        handle_register.assert_called_once_with(message, websocket)
        handle_message.assert_not_called()
        handle_exception.assert_not_called()
        parse_authorization.assert_not_called()

    @patch("apologiesserver.server._parse_authorization")
    @patch("apologiesserver.server.handle_exception")
    @patch("apologiesserver.server.handle_message")
    @patch("apologiesserver.server.handle_register")
    async def test_handle_message_request(self, handle_register, handle_message, handle_exception, parse_authorization, data):
        queue = AsyncMock()
        queue.send = CoroutineMock()
        handle_message.return_value = queue
        parse_authorization.return_value = "player_id"
        websocket = AsyncMock()
        data = data["list.json"]
        message = Message.for_json(data)
        await _handle_message(data, websocket)
        queue.send.assert_awaited_once()
        handle_register.assert_not_called()
        handle_message.assert_called_once_with("player_id", message, websocket)
        handle_exception.assert_not_called()
        parse_authorization.assert_called_once_with(websocket)

    @patch("apologiesserver.server.handle_disconnect")
    @patch("apologiesserver.server._handle_message")
    async def test_handle_connection(self, handle_message, handle_disconnect):
        queue = AsyncMock()
        queue.send = CoroutineMock()
        handle_disconnect.return_value = queue
        data = b"test data"
        websocket = AsyncMock()
        websocket.__aiter__.return_value = [data]
        await _handle_connection(websocket, "path")
        queue.send.assert_awaited_once()
        handle_message.assert_called_once_with(data, websocket)
        handle_disconnect.assert_called_once_with(websocket)

    @patch("apologiesserver.server.handle_shutdown")
    @patch("apologiesserver.server._handle_connection")
    @patch("apologiesserver.server.websockets.serve")
    async def test_websocket_server(self, serve, handle_connection, handle_shutdown):
        queue = AsyncMock()
        queue.send = CoroutineMock()
        handle_shutdown.return_value = queue
        stop = asyncio.Future()
        stop.set_result(None)
        await _websocket_server(stop, "host", 1234)
        queue.send.assert_awaited_once()
        serve.assert_called_with(handle_connection, "host", 1234)
        handle_shutdown.assert_awaited()
        # unfortunately, we can't prove that stop() was awaited, but in this case it's easy to eyeball in the code
