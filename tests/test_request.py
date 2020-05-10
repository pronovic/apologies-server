# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import

# TODO: remove this once requests.py is removed (it's obsolete)

from unittest.mock import MagicMock

import pytest
from apologies.game import GameMode
from asynctest import patch

from apologiesserver.interface import *
from apologiesserver.request import (
    RequestContext,
    handle_advertise_game_request,
    handle_cancel_game_request,
    handle_execute_move_request,
    handle_join_game_request,
    handle_list_available_games_request,
    handle_list_players_request,
    handle_quit_game_request,
    handle_register_player_request,
    handle_reregister_player_request,
    handle_retrieve_game_state_request,
    handle_send_message_request,
    handle_start_game_request,
    handle_unregister_player_request,
    lookup_handler,
)


class TestFunctions:
    """
    Test Python functions.
    """

    def test_lookup_handler_register(self):
        with pytest.raises(ProcessingError, match=r"Internal error"):
            lookup_handler(MessageType.REGISTER_PLAYER)  # this is handled as a special case

    def test_lookup_handler_invalid(self):
        with pytest.raises(ProcessingError, match=r"Internal error"):
            lookup_handler(MessageType.SERVER_SHUTDOWN)  # this isn't a request

    def test_lookup_handler_valid(self):
        assert lookup_handler(MessageType.REREGISTER_PLAYER) is handle_reregister_player_request
        assert lookup_handler(MessageType.LIST_PLAYERS) is handle_list_players_request
        assert lookup_handler(MessageType.ADVERTISE_GAME) is handle_advertise_game_request
        assert lookup_handler(MessageType.LIST_AVAILABLE_GAMES) is handle_list_available_games_request
        assert lookup_handler(MessageType.JOIN_GAME) is handle_join_game_request
        assert lookup_handler(MessageType.QUIT_GAME) is handle_quit_game_request
        assert lookup_handler(MessageType.START_GAME) is handle_start_game_request
        assert lookup_handler(MessageType.CANCEL_GAME) is handle_cancel_game_request
        assert lookup_handler(MessageType.EXECUTE_MOVE) is handle_execute_move_request
        assert lookup_handler(MessageType.RETRIEVE_GAME_STATE) is handle_retrieve_game_state_request
        assert lookup_handler(MessageType.SEND_MESSAGE) is handle_send_message_request


# pylint: disable=too-many-public-methods
class TestCoroutines:
    """
    Test Python coroutines.
    """

    pytestmark = pytest.mark.asyncio

    @patch("apologiesserver.request.handle_player_registered_event")
    async def test_handle_register_player_request(self, handle_player_registered_event):
        websocket = MagicMock()
        context = RegisterPlayerContext(handle="leela")
        message = Message(MessageType.REGISTER_PLAYER, context=context)
        await handle_register_player_request(websocket, message)
        handle_player_registered_event.assert_called_once_with(websocket, "leela")

    @patch("apologiesserver.request.handle_player_reregistered_event")
    async def test_handle_reregister_player_request(self, handle_player_reregistered_event):
        websocket = MagicMock()
        player = MagicMock()
        message = Message(MessageType.REREGISTER_PLAYER)
        game = MagicMock()
        request = RequestContext(websocket, message, player, game)
        await handle_reregister_player_request(request)
        handle_player_reregistered_event.assert_called_once_with(player, websocket)

    @patch("apologiesserver.request.handle_player_unregistered_event")
    async def test_handle_unregister_player_request(self, handle_player_unregistered_event):
        websocket = MagicMock()
        player = MagicMock()
        message = Message(MessageType.UNREGISTER_PLAYER)
        game = MagicMock()
        request = RequestContext(websocket, message, player, game)
        await handle_unregister_player_request(request)
        handle_player_unregistered_event.assert_called_once_with(player, game)

    @patch("apologiesserver.request.handle_registered_players_event")
    async def test_handle_list_players_request(self, handle_registered_players_event):
        websocket = MagicMock()
        player = MagicMock()
        message = Message(MessageType.LIST_PLAYERS)
        game = MagicMock()
        request = RequestContext(websocket, message, player, game)
        await handle_list_players_request(request)
        handle_registered_players_event.assert_called_once_with(player)

    @patch("apologiesserver.request.handle_game_advertised_event")
    async def test_handle_advertise_game_request_already_playing(self, handle_game_advertised_event):
        websocket = MagicMock()
        player = MagicMock()
        context = AdvertiseGameContext("name", GameMode.STANDARD, 3, Visibility.PUBLIC, ["fry", "bender"])
        message = Message(MessageType.ADVERTISE_GAME, context=context)
        game = MagicMock()
        request = RequestContext(websocket, message, player, game)
        with pytest.raises(ProcessingError, match=r"Player is already playing a game"):
            await handle_advertise_game_request(request)
        handle_game_advertised_event.assert_not_called()

    @patch("apologiesserver.request.handle_game_advertised_event")
    async def test_handle_advertise_game_request(self, handle_game_advertised_event):
        websocket = MagicMock()
        player = MagicMock()
        context = AdvertiseGameContext("name", GameMode.STANDARD, 3, Visibility.PUBLIC, ["fry", "bender"])
        message = Message(MessageType.ADVERTISE_GAME, context=context)
        game = None
        request = RequestContext(websocket, message, player, game)
        await handle_advertise_game_request(request)
        handle_game_advertised_event.assert_called_once_with(player, context)

    @patch("apologiesserver.request.handle_available_games_event")
    async def test_handle_list_available_games_request(self, handle_available_games_event):
        websocket = MagicMock()
        player = MagicMock()
        message = Message(MessageType.LIST_AVAILABLE_GAMES)
        game = MagicMock()
        request = RequestContext(websocket, message, player, game)
        await handle_list_available_games_request(request)
        handle_available_games_event.assert_called_once_with(player)

    @patch("apologiesserver.request.handle_game_joined_event")
    async def test_handle_join_game_request_already_playing(self, handle_game_joined_event):
        websocket = MagicMock()
        player = MagicMock()
        context = JoinGameContext(game_id="game")
        message = Message(MessageType.JOIN_GAME, context=context)
        game = MagicMock()
        request = RequestContext(websocket, message, player, game)
        with pytest.raises(ProcessingError, match=r"Player is already playing a game"):
            await handle_join_game_request(request)
        handle_game_joined_event.assert_not_called()

    @patch("apologiesserver.request.handle_game_joined_event")
    async def test_handle_join_game_request(self, handle_game_joined_event):
        websocket = MagicMock()
        player = MagicMock()
        context = JoinGameContext(game_id="game")
        message = Message(MessageType.JOIN_GAME, context=context)
        game = None
        request = RequestContext(websocket, message, player, game)
        await handle_join_game_request(request)
        handle_game_joined_event.assert_called_once_with(player, "game")

    @patch("apologiesserver.request.handle_game_player_quit_event")
    async def test_handle_quit_game_request_not_playing(self, handle_game_player_quit_event):
        websocket = MagicMock()
        player = MagicMock()
        message = Message(MessageType.QUIT_GAME)
        game = None
        request = RequestContext(websocket, message, player, game)
        with pytest.raises(ProcessingError, match=r"Player is not playing a game"):
            await handle_quit_game_request(request)
        handle_game_player_quit_event.assert_not_called()

    @patch("apologiesserver.request.handle_game_player_quit_event")
    async def test_handle_quit_game_request_not_in_progress(self, handle_game_player_quit_event):
        websocket = MagicMock()
        player = MagicMock()
        message = Message(MessageType.QUIT_GAME)
        game = MagicMock()
        game.is_in_progress.return_value = False
        request = RequestContext(websocket, message, player, game)
        with pytest.raises(ProcessingError, match=r"Game is not in progress"):
            await handle_quit_game_request(request)
        handle_game_player_quit_event.assert_not_called()

    @patch("apologiesserver.request.handle_game_player_quit_event")
    async def test_handle_quit_game_request_advertiser(self, handle_game_player_quit_event):
        websocket = MagicMock()
        player = MagicMock(handle="leela")
        message = Message(MessageType.QUIT_GAME)
        game = MagicMock(advertiser_handle="leela")
        request = RequestContext(websocket, message, player, game)
        with pytest.raises(ProcessingError, match=r"Advertiser may not quit a game"):
            await handle_quit_game_request(request)
        handle_game_player_quit_event.assert_not_called()

    @patch("apologiesserver.request.handle_game_player_quit_event")
    async def test_handle_quit_game_request(self, handle_game_player_quit_event):
        websocket = MagicMock()
        player = MagicMock()
        message = Message(MessageType.QUIT_GAME)
        game = MagicMock()
        request = RequestContext(websocket, message, player, game)
        await handle_quit_game_request(request)
        handle_game_player_quit_event.assert_called_once_with(player, game)

    @patch("apologiesserver.request.handle_game_started_event")
    async def test_handle_start_game_request_not_playing(self, handle_game_started_event):
        websocket = MagicMock()
        player = MagicMock()
        message = Message(MessageType.START_GAME)
        game = None
        request = RequestContext(websocket, message, player, game)
        with pytest.raises(ProcessingError, match=r"Player is not playing a game"):
            await handle_start_game_request(request)
        handle_game_started_event.assert_not_called()

    @patch("apologiesserver.request.handle_game_started_event")
    async def test_handle_start_game_request_already_played(self, handle_game_started_event):
        websocket = MagicMock()
        player = MagicMock()
        message = Message(MessageType.START_GAME)
        game = MagicMock()
        game.is_playing.return_value = True
        request = RequestContext(websocket, message, player, game)
        with pytest.raises(ProcessingError, match=r"Game is already being played"):
            await handle_start_game_request(request)
        handle_game_started_event.assert_not_called()

    @patch("apologiesserver.request.handle_game_started_event")
    async def test_handle_start_game_request_not_advertiser(self, handle_game_started_event):
        websocket = MagicMock()
        player = MagicMock(handle="leela")
        message = Message(MessageType.START_GAME)
        game = MagicMock(advertiser_handle="bender")
        game.is_playing.return_value = False
        request = RequestContext(websocket, message, player, game)
        with pytest.raises(ProcessingError, match=r"Player did not advertise this game"):
            await handle_start_game_request(request)
        handle_game_started_event.assert_not_called()

    @patch("apologiesserver.request.handle_game_started_event")
    async def test_handle_start_game_request(self, handle_game_started_event):
        websocket = MagicMock()
        player = MagicMock(handle="leela")
        message = Message(MessageType.START_GAME)
        game = MagicMock(advertiser_handle="leela")
        game.is_playing.return_value = False
        request = RequestContext(websocket, message, player, game)
        await handle_start_game_request(request)
        handle_game_started_event.assert_called_once_with(game)

    @patch("apologiesserver.request.handle_game_cancelled_event")
    async def test_handle_cancel_game_request_not_playing(self, handle_game_cancelled_event):
        websocket = MagicMock()
        player = MagicMock()
        message = Message(MessageType.CANCEL_GAME)
        game = None
        request = RequestContext(websocket, message, player, game)
        with pytest.raises(ProcessingError, match=r"Player is not playing a game"):
            await handle_cancel_game_request(request)
        handle_game_cancelled_event.assert_not_called()

    @patch("apologiesserver.request.handle_game_cancelled_event")
    async def test_handle_cancel_game_request_not_in_progress(self, handle_game_cancelled_event):
        websocket = MagicMock()
        player = MagicMock()
        message = Message(MessageType.CANCEL_GAME)
        game = MagicMock()
        game.is_in_progress.return_value = False
        request = RequestContext(websocket, message, player, game)
        with pytest.raises(ProcessingError, match=r"Game is not in progress"):
            await handle_cancel_game_request(request)
        handle_game_cancelled_event.assert_not_called()

    @patch("apologiesserver.request.handle_game_cancelled_event")
    async def test_handle_cancel_game_request_not_advertiser(self, handle_game_cancelled_event):
        websocket = MagicMock()
        player = MagicMock(handle="leela")
        message = Message(MessageType.CANCEL_GAME)
        game = MagicMock(advertiser_handle="bender")
        request = RequestContext(websocket, message, player, game)
        with pytest.raises(ProcessingError, match=r"Player did not advertise this game"):
            await handle_cancel_game_request(request)
        handle_game_cancelled_event.assert_not_called()

    @patch("apologiesserver.request.handle_game_cancelled_event")
    async def test_handle_cancel_game_request(self, handle_game_cancelled_event):
        websocket = MagicMock()
        player = MagicMock(handle="leela")
        message = Message(MessageType.CANCEL_GAME)
        game = MagicMock(advertiser_handle="leela")
        request = RequestContext(websocket, message, player, game)
        await handle_cancel_game_request(request)
        handle_game_cancelled_event.assert_called_once_with(game, CancelledReason.CANCELLED)

    @patch("apologiesserver.request.handle_game_execute_move_event")
    async def test_handle_execute_move_request_not_playing(self, handle_game_execute_move_event):
        websocket = MagicMock()
        player = MagicMock()
        context = ExecuteMoveContext(move_id="move")
        message = Message(MessageType.EXECUTE_MOVE, context=context)
        game = None
        request = RequestContext(websocket, message, player, game)
        with pytest.raises(ProcessingError, match=r"Player is not playing a game"):
            await handle_execute_move_request(request)
        handle_game_execute_move_event.assert_not_called()

    @patch("apologiesserver.request.handle_game_execute_move_event")
    async def test_handle_execute_move_request_not_being_played(self, handle_game_execute_move_event):
        websocket = MagicMock()
        player = MagicMock()
        context = ExecuteMoveContext(move_id="move")
        message = Message(MessageType.EXECUTE_MOVE, context=context)
        game = MagicMock()
        game.is_playing.return_value = False
        request = RequestContext(websocket, message, player, game)
        with pytest.raises(ProcessingError, match=r"Game is not being played"):
            await handle_execute_move_request(request)
        handle_game_execute_move_event.assert_not_called()

    @patch("apologiesserver.request.handle_game_execute_move_event")
    async def test_handle_execute_move_request_no_move_pending(self, handle_game_execute_move_event):
        websocket = MagicMock()
        player = MagicMock(handle="leela")
        context = ExecuteMoveContext(move_id="move")
        message = Message(MessageType.EXECUTE_MOVE, context=context)
        game = MagicMock()
        game.is_move_pending.return_value = False
        request = RequestContext(websocket, message, player, game)
        with pytest.raises(ProcessingError, match=r"No move is pending for this player"):
            await handle_execute_move_request(request)
        game.is_move_pending.assert_called_once_with("leela")
        game.is_legal_move.assert_not_called()
        handle_game_execute_move_event.assert_not_called()

    @patch("apologiesserver.request.handle_game_execute_move_event")
    async def test_handle_execute_move_request_illegal_move(self, handle_game_execute_move_event):
        websocket = MagicMock()
        player = MagicMock(handle="leela")
        context = ExecuteMoveContext(move_id="move")
        message = Message(MessageType.EXECUTE_MOVE, context=context)
        game = MagicMock()
        game.is_move_pending.return_value = True
        game.is_legal_move.return_value = False
        request = RequestContext(websocket, message, player, game)
        with pytest.raises(ProcessingError, match=r"The chosen move is not legal"):
            await handle_execute_move_request(request)
        game.is_move_pending.assert_called_once_with("leela")
        game.is_legal_move.assert_called_once_with("leela", "move")
        handle_game_execute_move_event.assert_not_called()

    @patch("apologiesserver.request.handle_game_execute_move_event")
    async def test_handle_execute_move_request(self, handle_game_execute_move_event):
        websocket = MagicMock()
        player = MagicMock(handle="leela")
        context = ExecuteMoveContext(move_id="move")
        message = Message(MessageType.EXECUTE_MOVE, context=context)
        game = MagicMock()
        game.is_move_pending.return_value = True
        request = RequestContext(websocket, message, player, game)
        await handle_execute_move_request(request)
        game.is_move_pending.assert_called_once_with("leela")
        handle_game_execute_move_event.assert_called_once_with(player, game, "move")

    @patch("apologiesserver.request.handle_game_state_change_event")
    async def test_handle_retrieve_game_state_request_not_playing(self, handle_game_state_change_event):
        websocket = MagicMock()
        player = MagicMock()
        message = Message(MessageType.RETRIEVE_GAME_STATE)
        game = None
        request = RequestContext(websocket, message, player, game)
        with pytest.raises(ProcessingError, match=r"Player is not playing a game"):
            await handle_retrieve_game_state_request(request)
        handle_game_state_change_event.assert_not_called()

    @patch("apologiesserver.request.handle_game_state_change_event")
    async def test_handle_retrieve_game_state_request_not_being_played(self, handle_game_state_change_event):
        websocket = MagicMock()
        player = MagicMock()
        message = Message(MessageType.RETRIEVE_GAME_STATE)
        game = MagicMock()
        game.is_playing.return_value = False
        request = RequestContext(websocket, message, player, game)
        with pytest.raises(ProcessingError, match=r"Game is not being played"):
            await handle_retrieve_game_state_request(request)
        handle_game_state_change_event.called_once_with(game, player)

    @patch("apologiesserver.request.handle_game_state_change_event")
    async def test_handle_retrieve_game_state_request(self, handle_game_state_change_event):
        websocket = MagicMock()
        player = MagicMock()
        message = Message(MessageType.RETRIEVE_GAME_STATE)
        game = MagicMock()
        game.is_playing.return_value = True
        request = RequestContext(websocket, message, player, game)
        await handle_retrieve_game_state_request(request)
        handle_game_state_change_event.called_once_with(game, player)

    @patch("apologiesserver.request.handle_player_message_received_event")
    async def test_handle_send_message_request(self, handle_player_message_received_event):
        websocket = MagicMock()
        player = MagicMock()
        context = SendMessageContext(message="hello", recipient_handles=["fry", "bender"])
        message = Message(MessageType.SEND_MESSAGE, context=context)
        game = MagicMock()
        request = RequestContext(websocket, message, player, game)
        await handle_send_message_request(request)
        handle_player_message_received_event.called_once_with("handle", ["fry", "bender"], "hello")
