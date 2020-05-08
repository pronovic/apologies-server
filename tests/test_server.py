# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=redefined-outer-name

import asyncio
import os
from unittest.mock import MagicMock

import pytest
from asynctest import CoroutineMock
from asynctest import MagicMock as AsyncMock
from asynctest import patch
from websockets.http import Headers

from apologiesserver.interface import FailureReason, Message, MessageType, ProcessingError
from apologiesserver.request import RequestContext
from apologiesserver.server import (
    _dispatch_register_player,
    _dispatch_request,
    _handle_connection,
    _handle_message,
    _parse_authorization,
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


class TestCoroutines:
    """
    Test Python coroutines.
    """

    pytestmark = pytest.mark.asyncio

    @patch("apologiesserver.server.handle_register_player_request")
    async def test_dispatch_register_player(self, handle_register_player_request):
        websocket = MagicMock()
        message = MagicMock()
        await _dispatch_register_player(websocket, message)
        handle_register_player_request.assert_called_once_with(websocket, message)

    @patch("apologiesserver.server.lookup_handler")
    async def test_dispatch_request_invalid_message(self, lookup_handler):
        lookup_handler.side_effect = ProcessingError(FailureReason.INTERNAL_ERROR)
        websocket = MagicMock()
        message = MagicMock(message=MessageType.GAME_JOINED)
        with pytest.raises(ProcessingError, match=r"Internal error"):
            await _dispatch_request(websocket, message)

    @patch("apologiesserver.server.lookup_handler")
    @patch("apologiesserver.server._parse_authorization")
    async def test_dispatch_request_invalid_auth(self, parse_authorization, lookup_handler):
        handler = MagicMock()
        parse_authorization.side_effect = ProcessingError(FailureReason.INVALID_AUTH)
        lookup_handler.return_value = handler
        websocket = MagicMock()
        message = MagicMock(message=MessageType.GAME_JOINED)
        with pytest.raises(ProcessingError, match=r"Missing or invalid authorization header"):
            await _dispatch_request(websocket, message)
        parse_authorization.assert_called_once_with(websocket)
        handler.assert_not_called()

    @patch("apologiesserver.server.lookup_player")
    @patch("apologiesserver.server.lookup_handler")
    @patch("apologiesserver.server._parse_authorization")
    async def test_dispatch_request_invalid_player(self, parse_authorization, lookup_handler, lookup_player):
        handler = MagicMock()
        player = None
        parse_authorization.return_value = "player-id"
        lookup_handler.return_value = handler
        lookup_player.return_value = player
        websocket = MagicMock()
        message = MagicMock(message=MessageType.GAME_JOINED)
        with pytest.raises(ProcessingError, match=r"Unknown or invalid player"):
            await _dispatch_request(websocket, message)
        parse_authorization.assert_called_once_with(websocket)
        lookup_player.assert_called_with(player_id="player-id")
        handler.assert_not_called()

    @patch("apologiesserver.server.lookup_game")
    @patch("apologiesserver.server.lookup_player")
    @patch("apologiesserver.server.lookup_handler")
    @patch("apologiesserver.server._parse_authorization")
    async def test_dispatch_request_invalid_game(self, parse_authorization, lookup_handler, lookup_player, lookup_game):
        handler = MagicMock()
        player = AsyncMock(game_id="game-id", lock=asyncio.Lock())
        parse_authorization.return_value = "player-id"
        lookup_handler.return_value = handler
        lookup_player.return_value = player
        lookup_game.side_effect = ProcessingError(FailureReason.UNKNOWN_GAME)
        websocket = MagicMock()
        message = MagicMock(message=MessageType.GAME_JOINED)
        with pytest.raises(ProcessingError, match=r"Unknown or invalid game"):
            await _dispatch_request(websocket, message)
        parse_authorization.assert_called_once_with(websocket)
        lookup_player.assert_called_with(player_id="player-id")
        lookup_game.assert_called_with(game_id="game-id")
        handler.assert_not_called()

    @patch("apologiesserver.server.lookup_game")
    @patch("apologiesserver.server.lookup_player")
    @patch("apologiesserver.server.lookup_handler")
    @patch("apologiesserver.server._parse_authorization")
    async def test_dispatch_request_valid_no_game(self, parse_authorization, lookup_handler, lookup_player, lookup_game):
        handler = CoroutineMock()
        player = AsyncMock(game_id=None, lock=asyncio.Lock())
        player.mark_active = CoroutineMock()
        game = None
        parse_authorization.return_value = "player-id"
        lookup_handler.return_value = handler
        lookup_player.return_value = player
        lookup_game.return_value = game
        websocket = MagicMock()
        message = MagicMock(message=MessageType.GAME_JOINED)
        await _dispatch_request(websocket, message)
        parse_authorization.assert_called_once_with(websocket)
        lookup_player.assert_called_with(player_id="player-id")
        lookup_game.assert_called_with(game_id=None)
        player.mark_active.assert_called_once()
        handler.assert_called_once_with(RequestContext(websocket, message, player, game))

    @patch("apologiesserver.server.lookup_game")
    @patch("apologiesserver.server.lookup_player")
    @patch("apologiesserver.server.lookup_handler")
    @patch("apologiesserver.server._parse_authorization")
    async def test_dispatch_request_valid_with_game(self, parse_authorization, lookup_handler, lookup_player, lookup_game):
        handler = CoroutineMock()
        player = AsyncMock(game_id="game-id", lock=asyncio.Lock())
        player.mark_active = CoroutineMock()
        game = AsyncMock()
        parse_authorization.return_value = "player-id"
        lookup_handler.return_value = handler
        lookup_player.return_value = player
        lookup_game.return_value = game
        websocket = MagicMock()
        message = MagicMock(message=MessageType.GAME_JOINED)
        await _dispatch_request(websocket, message)
        parse_authorization.assert_called_once_with(websocket)
        lookup_player.assert_called_with(player_id="player-id")
        lookup_game.assert_called_with(game_id="game-id")
        player.mark_active.assert_called_once()
        handler.assert_called_once_with(RequestContext(websocket, message, player, game))

    @patch("apologiesserver.server.handle_request_failed_event")
    @patch("apologiesserver.server._dispatch_register_player")
    @patch("apologiesserver.server._dispatch_request")
    async def test_handle_message_exception(self, dispatch_request, dispatch_register_player, handle_request_failed_event, data):
        exception = ProcessingError(FailureReason.UNKNOWN_PLAYER)
        dispatch_register_player.side_effect = exception
        websocket = AsyncMock()
        data = data["register.json"]
        message = Message.for_json(data)
        await _handle_message(websocket, data)
        dispatch_register_player.assert_called_once_with(websocket, message)
        dispatch_request.assert_not_called()
        handle_request_failed_event.assert_called_with(websocket, exception)

    @patch("apologiesserver.server.handle_request_failed_event")
    @patch("apologiesserver.server._dispatch_register_player")
    @patch("apologiesserver.server._dispatch_request")
    async def test_handle_message_register(self, dispatch_request, dispatch_register_player, handle_request_failed_event, data):
        websocket = AsyncMock()
        data = data["register.json"]
        message = Message.for_json(data)
        await _handle_message(websocket, data)
        dispatch_register_player.assert_called_once_with(websocket, message)
        dispatch_request.assert_not_called()
        handle_request_failed_event.assert_not_called()

    @patch("apologiesserver.server.handle_request_failed_event")
    @patch("apologiesserver.server._dispatch_register_player")
    @patch("apologiesserver.server._dispatch_request")
    async def test_handle_message_request(self, dispatch_request, dispatch_register_player, handle_request_failed_event, data):
        websocket = AsyncMock()
        data = data["list.json"]
        message = Message.for_json(data)
        await _handle_message(websocket, data)
        dispatch_register_player.assert_not_called()
        dispatch_request.assert_called_once_with(websocket, message)
        handle_request_failed_event.assert_not_called()

    @patch("apologiesserver.server.handle_player_disconnected_event")
    @patch("apologiesserver.server._handle_message")
    async def test_handle_connection(self, handle_message, handle_player_disconnected_event):
        data = b"test data"
        websocket = AsyncMock()
        websocket.__aiter__.return_value = [data]
        await _handle_connection(websocket, "path")
        handle_message.assert_called_once_with(websocket, data)
        handle_player_disconnected_event.assert_called_once_with(websocket)
