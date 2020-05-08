# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:

import asyncio
from unittest.mock import MagicMock

import pytest
from asynctest import CoroutineMock
from asynctest import MagicMock as AsyncMock
from asynctest import patch
from websockets.http import Headers

from apologiesserver.interface import FailureReason, MessageType, ProcessingError
from apologiesserver.request import RequestContext
from apologiesserver.server import _dispatch_register_player, _dispatch_request, _parse_authorization


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
        parse_authorization.called_once_with(websocket)
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
        parse_authorization.called_once_with(websocket)
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
        parse_authorization.called_once_with(websocket)
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
        parse_authorization.called_once_with(websocket)
        lookup_player.assert_called_with(player_id="player-id")
        lookup_game.assert_called_with(game_id=None)
        player.mark_active.called_once()
        handler.called_once_with(RequestContext(websocket, message, player, game))

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
        parse_authorization.called_once_with(websocket)
        lookup_player.assert_called_with(player_id="player-id")
        lookup_game.assert_called_with(game_id="game-id")
        player.mark_active.called_once()
        handler.called_once_with(RequestContext(websocket, message, player, game))

    # TODO: need unit tests for _handle_connection() and _websocket_server()
    #       Not really sure how I am going to handle the asynchronous loop for _handle_connection().
    #       Maybe it can just return an array of messages, and then it exits?
    #       See: https://github.com/Martiusweb/asynctest/issues/140
    #       I think that to test either of these, I have to override other functions (like override the dispatch)
