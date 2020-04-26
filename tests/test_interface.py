# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import,too-many-public-methods

import pytest
from apologies.game import GameMode

from apologiesserver.interface import *


class TestRequest:
    def test_from_json_missing_context(self) -> None:
        data = """
        {
          "request": "REGISTER_PLAYER"
        }
        """
        with pytest.raises(AssertionError):
            Request.from_json(data)

    def test_from_json_extra_context(self) -> None:
        data = """
        {
          "request": "REREGISTER_PLAYER",
          "context": {
            "handle": "leela"
          }
        }
        """
        with pytest.raises(AssertionError):
            Request.from_json(data)

    def test_from_json_wrong_context(self) -> None:
        data = """
        {
          "request": "BOGUS",
          "context": {
            "handle": "leela"
          }
        }
        """
        with pytest.raises(KeyError):
            Request.from_json(data)

    def test_from_json_unknown_request(self) -> None:
        data = """
        {
          "request": "BOGUS",
          "context": {
            "handle": "leela"
          }
        }
        """
        with pytest.raises(KeyError):
            Request.from_json(data)

    def test_register_player_valid(self) -> None:
        data = """
        {
          "request": "REGISTER_PLAYER",
          "context": {
            "handle": "leela"
          }
        }
        """
        request = Request.from_json(data)
        assert request.request == RequestType.REGISTER_PLAYER
        assert request.context.handle == "leela"

    def test_register_player_invalid_handle_none(self) -> None:
        data = """
        {
          "request": "REGISTER_PLAYER",
          "context": {
            "handle": null
          }
        }
        """
        with pytest.raises(ValueError):
            Request.from_json(data)

    def test_register_player_invalid_handle_empty(self) -> None:
        data = """
        {
          "request": "REGISTER_PLAYER",
          "context": {
            "handle": ""
          }
        }
        """
        with pytest.raises(ValueError):
            Request.from_json(data)

    def test_advertise_game_valid_handles(self) -> None:
        data = """
        {
          "request": "ADVERTISE_GAME",
          "context": {
            "name": "Leela's Game",
            "mode": "STANDARD",
            "players": 3,
            "visibility": "PRIVATE",
            "invited_handles": [ "bender", "hermes" ]
          }
        } 
        """
        request = Request.from_json(data)
        assert request.request == RequestType.ADVERTISE_GAME
        assert request.context.name == "Leela's Game"
        assert request.context.mode == GameMode.STANDARD
        assert request.context.players == 3
        assert request.context.visibility == Visibility.PRIVATE
        assert request.context.invited_handles == ["bender", "hermes"]

    def test_advertise_game_valid_no_handles(self) -> None:
        data = """
        {
          "request": "ADVERTISE_GAME",
          "context": {
            "name": "Leela's Game",
            "mode": "STANDARD",
            "players": 3,
            "visibility": "PUBLIC",
            "invited_handles": []
          }
        } 
        """
        request = Request.from_json(data)
        assert request.request == RequestType.ADVERTISE_GAME
        assert request.context.name == "Leela's Game"
        assert request.context.mode == GameMode.STANDARD
        assert request.context.players == 3
        assert request.context.visibility == Visibility.PUBLIC
        assert request.context.invited_handles == []

    def test_advertise_game_invalid_name_none(self) -> None:
        data = """
        {
          "request": "ADVERTISE_GAME",
          "context": {
            "name": null,
            "mode": "STANDARD",
            "players": 3,
            "visibility": "PUBLIC",
            "invited_handles": [ "bender", "hermes" ]
          }
        } 
        """
        with pytest.raises(ValueError):
            Request.from_json(data)

    def test_advertise_game_invalid_name_empty(self) -> None:
        data = """
        {
          "request": "ADVERTISE_GAME",
          "context": {
            "name": "",
            "mode": "STANDARD",
            "players": 3,
            "visibility": "PUBLIC",
            "invited_handles": [ "bender", "hermes" ]
          }
        } 
        """
        with pytest.raises(ValueError):
            Request.from_json(data)

    def test_advertise_game_invalid_mode_none(self) -> None:
        data = """
        {
          "request": "ADVERTISE_GAME",
          "context": {
            "name": "Leela's Game",
            "mode": null,
            "players": 3,
            "visibility": "PUBLIC",
            "invited_handles": [ "bender", "hermes" ]
          }
        } 
        """
        with pytest.raises(ValueError):
            Request.from_json(data)

    def test_advertise_game_invalid_mode_empty(self) -> None:
        data = """
        {
          "request": "ADVERTISE_GAME",
          "context": {
            "name": "Leela's Game",
            "mode": "",
            "players": 3,
            "visibility": "PUBLIC",
            "invited_handles": [ "bender", "hermes" ]
          }
        } 
        """
        with pytest.raises(ValueError):
            Request.from_json(data)

    def test_advertise_game_invalid_mode_bad(self) -> None:
        data = """
        {
          "request": "ADVERTISE_GAME",
          "context": {
            "name": "Leela's Game",
            "mode": "BOGUS",
            "players": 3,
            "visibility": "PUBLIC",
            "invited_handles": [ "bender", "hermes" ]
          }
        } 
        """
        with pytest.raises(KeyError):
            Request.from_json(data)

    def test_advertise_game_invalid_player_small(self) -> None:
        data = """
        {
          "request": "ADVERTISE_GAME",
          "context": {
            "name": "Leela's Game",
            "mode": "STANDARD",
            "players": 1,
            "visibility": "PUBLIC",
            "invited_handles": [ "bender", "hermes" ]
          }
        } 
        """
        with pytest.raises(ValueError):
            Request.from_json(data)

    def test_advertise_game_invalid_player_large(self) -> None:
        data = """
        {
          "request": "ADVERTISE_GAME",
          "context": {
            "name": "Leela's Game",
            "mode": "STANDARD",
            "players": 5,
            "visibility": "PUBLIC",
            "invited_handles": [ "bender", "hermes" ]
          }
        } 
        """
        with pytest.raises(ValueError):
            Request.from_json(data)

    def test_advertise_game_invalid_visibility_none(self) -> None:
        data = """
        {
          "request": "ADVERTISE_GAME",
          "context": {
            "name": "Leela's Game",
            "mode": "STANDARD",
            "players": 3,
            "visibility": null,
            "invited_handles": [ "bender", "hermes" ]
          }
        } 
        """
        with pytest.raises(ValueError):
            Request.from_json(data)

    def test_advertise_game_invalid_visibility_empty(self) -> None:
        data = """
        {
          "request": "ADVERTISE_GAME",
          "context": {
            "name": "Leela's Game",
            "mode": "STANDARD",
            "players": 3,
            "visibility": "",
            "invited_handles": [ "bender", "hermes" ]
          }
        } 
        """
        with pytest.raises(ValueError):
            Request.from_json(data)

    def test_advertise_game_invalid_visibility_bad(self) -> None:
        data = """
        {
          "request": "ADVERTISE_GAME",
          "context": {
            "name": "Leela's Game",
            "mode": "STANDARD",
            "players": 3,
            "visibility": "BOGUS",
            "invited_handles": [ "bender", "hermes" ]
          }
        } 
        """
        with pytest.raises(KeyError):
            Request.from_json(data)

    def test_advertise_game_invalid_handle_none(self) -> None:
        data = """
        {
          "request": "ADVERTISE_GAME",
          "context": {
            "name": "Leela's Game",
            "mode": "STANDARD",
            "players": 3,
            "visibility": "PUBLIC",
            "invited_handles": null
          }
        } 
        """
        with pytest.raises(TypeError):
            Request.from_json(data)

    def test_advertise_game_invalid_handle_none_value(self) -> None:
        data = """
        {
          "request": "ADVERTISE_GAME",
          "context": {
            "name": "Leela's Game",
            "mode": "STANDARD",
            "players": 3,
            "visibility": "PUBLIC",
            "invited_handles": [ "bender", null ]
          }
        } 
        """
        with pytest.raises(ValueError):
            Request.from_json(data)

    def test_advertise_game_invalid_handle_empty_value(self) -> None:
        data = """
        {
          "request": "ADVERTISE_GAME",
          "context": {
            "name": "Leela's Game",
            "mode": "STANDARD",
            "players": 3,
            "visibility": "PUBLIC",
            "invited_handles": [ "bender", "" ]
          }
        } 
        """
        with pytest.raises(ValueError):
            Request.from_json(data)

    def test_join_game_valid(self) -> None:
        data = """
        {
          "request": "JOIN_GAME",
          "context": {
            "game_id": "f13b405e-36e5-45f3-a351-e45bf487acfe"
          }
        }
        """
        request = Request.from_json(data)
        assert request.request == RequestType.JOIN_GAME
        assert request.context.game_id == "f13b405e-36e5-45f3-a351-e45bf487acfe"

    def test_join_game_invalid_game_id_none(self) -> None:
        data = """
        {
          "request": "JOIN_GAME",
          "context": {
            "game_id": null
          }
        }
        """
        with pytest.raises(ValueError):
            Request.from_json(data)

    def test_join_game_invalid_game_id_empty(self) -> None:
        data = """
        {
          "request": "JOIN_GAME",
          "context": {
            "game_id": ""
          }
        }
        """
        with pytest.raises(ValueError):
            Request.from_json(data)

    def test_execute_move_valid(self) -> None:
        data = """
        {
          "request": "EXECUTE_MOVE",
          "context": {
            "move_id": "4"
          }
        }  
        """
        request = Request.from_json(data)
        assert request.request == RequestType.EXECUTE_MOVE
        assert request.context.move_id == "4"

    def test_execute_move_invalid_move_id_none(self) -> None:
        data = """
        {
          "request": "EXECUTE_MOVE",
          "context": {
            "move_id": null
          }
        }  
        """
        with pytest.raises(ValueError):
            Request.from_json(data)

    def test_execute_move_invalid_move_id_empty(self) -> None:
        data = """
        {
          "request": "EXECUTE_MOVE",
          "context": {
            "move_id": ""
          }
        }  
        """
        with pytest.raises(ValueError):
            Request.from_json(data)

    def test_send_message_valid(self) -> None:
        data = """
        {
          "request": "SEND_MESSAGE",
          "context": {
            "message": "Hello!",
            "recipient_handles": [ "hermes", "nibbler" ]
          }
        }  
        """
        request = Request.from_json(data)
        assert request.request == RequestType.SEND_MESSAGE
        assert request.context.message == "Hello!"
        assert request.context.recipient_handles == ["hermes", "nibbler"]

    def test_send_message_invalid_message_none(self) -> None:
        data = """
        {
          "request": "SEND_MESSAGE",
          "context": {
            "message": none,
            "recipient_handles": [ "hermes", "nibbler" ]
          }
        }  
        """
        with pytest.raises(ValueError):
            Request.from_json(data)

    def test_send_message_invalid_message_empty(self) -> None:
        data = """
        {
          "request": "SEND_MESSAGE",
          "context": {
            "message": "",
            "recipient_handles": [ "hermes", "nibbler" ]
          }
        }  
        """
        with pytest.raises(ValueError):
            Request.from_json(data)

    def test_send_message_invalid_recipients_none(self) -> None:
        data = """
        {
          "request": "SEND_MESSAGE",
          "context": {
            "message": "Hello!",
            "recipient_handles": null
          }
        }  
        """
        with pytest.raises(TypeError):
            Request.from_json(data)

    def test_send_message_invalid_recipients_empty(self) -> None:
        data = """
        {
          "request": "SEND_MESSAGE",
          "context": {
            "message": "Hello!",
            "recipient_handles": []
          }
        }  
        """
        with pytest.raises(ValueError):
            Request.from_json(data)

    def test_send_message_invalid_recipients_none_value(self) -> None:
        data = """
        {
          "request": "SEND_MESSAGE",
          "context": {
            "message": "Hello!",
            "recipient_handles": [ "hermes", null ]
          }
        }  
        """
        with pytest.raises(ValueError):
            Request.from_json(data)

    def test_send_message_invalid_recipients_empty_value(self) -> None:
        data = """
        {
          "request": "SEND_MESSAGE",
          "context": {
            "message": "Hello!",
            "recipient_handles": [ "hermes", "" ]
          }
        }  
        """
        with pytest.raises(ValueError):
            Request.from_json(data)

    def test_register_player_roundtrip(self) -> None:
        context = RegisterPlayerContext(handle="leela")
        request = Request(RequestType.REGISTER_PLAYER, context)
        self.roundtrip(request)

    def test_reregister_player_roundtrip(self) -> None:
        request = Request(RequestType.REREGISTER_PLAYER)
        self.roundtrip(request)

    def test_unregister_player_roundtrip(self) -> None:
        request = Request(RequestType.UNREGISTER_PLAYER)
        self.roundtrip(request)

    def test_list_players_roundtrip(self) -> None:
        request = Request(RequestType.LIST_PLAYERS)
        self.roundtrip(request)

    def test_advertise_game_roundtrip(self) -> None:
        context = AdvertiseGameContext("Leela's Game", GameMode.STANDARD, 3, Visibility.PRIVATE, ["fry", "bender"])
        request = Request(RequestType.ADVERTISE_GAME, context)
        self.roundtrip(request)

    def test_list_available_games_roundtrip(self) -> None:
        request = Request(RequestType.LIST_AVAILABLE_GAMES)
        self.roundtrip(request)

    def test_join_game_roundtrip(self) -> None:
        context = JoinGameContext("game")
        request = Request(RequestType.JOIN_GAME, context)
        self.roundtrip(request)

    def test_quit_game_roundtrip(self) -> None:
        request = Request(RequestType.QUIT_GAME)
        self.roundtrip(request)

    def test_start_game_roundtrip(self) -> None:
        request = Request(RequestType.START_GAME)
        self.roundtrip(request)

    def test_cancel_game_roundtrip(self) -> None:
        request = Request(RequestType.CANCEL_GAME)
        self.roundtrip(request)

    def test_execute_move_roundtrip(self) -> None:
        context = ExecuteMoveContext("move")
        request = Request(RequestType.EXECUTE_MOVE, context)
        self.roundtrip(request)

    def test_retrieve_game_state_roundtrip(self) -> None:
        request = Request(RequestType.RETRIEVE_GAME_STATE)
        self.roundtrip(request)

    def test_send_message_roundtrip(self) -> None:
        context = SendMessageContext("Hello", ["fry", "bender"])
        request = Request(RequestType.SEND_MESSAGE, context)
        self.roundtrip(request)

    # noinspection PyMethodMayBeStatic
    def roundtrip(self, request: Request) -> None:
        data = request.to_json()
        copy = Request.from_json(data)
        assert request is not copy and request == copy
