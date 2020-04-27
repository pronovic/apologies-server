# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import,too-many-public-methods

import pytest
from apologies.game import GameMode

from apologiesserver.interface import *


class TestMessage:
    def test_message_invalid_type(self) -> None:
        with pytest.raises(ValueError, match=r"'message' must be a MessageType"):
            Message(None, "Hello")  # type: ignore
        with pytest.raises(ValueError, match=r"'message' must be a MessageType"):
            Message("", "Hello")  # type: ignore
        with pytest.raises(ValueError, match=r"'message' must be a MessageType"):
            Message(PlayerType.HUMAN, "Hello")  # type: ignore

    def test_message_invalid_context(self) -> None:
        with pytest.raises(ValueError, match=r"Message type REGISTER_PLAYER requires a context"):
            Message(MessageType.REGISTER_PLAYER, None)
        with pytest.raises(ValueError, match=r"Message type GAME_JOINED does not support this context"):
            Message(MessageType.GAME_JOINED, "Hello")
        with pytest.raises(ValueError, match=r"Message type PLAYER_IDLE does not allow a context"):
            Message(MessageType.PLAYER_IDLE, "Hello")

    def test_from_json_missing_message(self) -> None:
        data = """
        {
          "wrong": "REGISTER_PLAYER",
          "context": {
            "handle": "leela"
          }
        }
        """
        with pytest.raises(ValueError, match=r"Message type is required"):
            Message.from_json(data)

    def test_from_json_missing_context(self) -> None:
        data = """
        {
          "message": "REGISTER_PLAYER"
        }
        """
        with pytest.raises(ValueError, match=r"Message type REGISTER_PLAYER requires a context"):
            Message.from_json(data)

    def test_from_json_extra_context(self) -> None:
        data = """
        {
          "message": "REREGISTER_PLAYER",
          "context": {
            "handle": "leela"
          }
        }
        """
        with pytest.raises(ValueError, match=r"Message type REREGISTER_PLAYER does not allow a context"):
            Message.from_json(data)

    def test_from_json_wrong_context(self) -> None:
        data = """
        {
          "message": "ADVERTISE_GAME",
          "context": {
            "handle": "leela"
          }
        }
        """
        with pytest.raises(ValueError, match=r"Message type ADVERTISE_GAME does not support this context"):
            Message.from_json(data)

    def test_from_json_unknown_message(self) -> None:
        data = """
        {
          "message": "BOGUS",
          "context": {
            "handle": "leela"
          }
        }
        """
        with pytest.raises(ValueError, match=r"Unknown message type: BOGUS"):
            Message.from_json(data)

    def test_register_player_valid(self) -> None:
        data = """
        {
          "message": "REGISTER_PLAYER",
          "context": {
            "handle": "leela"
          }
        }
        """
        message = Message.from_json(data)
        assert message.message == MessageType.REGISTER_PLAYER
        assert message.context.handle == "leela"

    def test_register_player_invalid_handle_none(self) -> None:
        data = """
        {
          "message": "REGISTER_PLAYER",
          "context": {
            "handle": null
          }
        }
        """
        with pytest.raises(ValueError, match=r"'handle' must be a non-empty string"):
            Message.from_json(data)

    def test_register_player_invalid_handle_empty(self) -> None:
        data = """
        {
          "message": "REGISTER_PLAYER",
          "context": {
            "handle": ""
          }
        }
        """
        with pytest.raises(ValueError, match=r"'handle' must be a non-empty string"):
            Message.from_json(data)

    def test_advertise_game_valid_handles(self) -> None:
        data = """
        {
          "message": "ADVERTISE_GAME",
          "context": {
            "name": "Leela's Game",
            "mode": "STANDARD",
            "players": 3,
            "visibility": "PRIVATE",
            "invited_handles": [ "bender", "hermes" ]
          }
        } 
        """
        message = Message.from_json(data)
        assert message.message == MessageType.ADVERTISE_GAME
        assert message.context.name == "Leela's Game"
        assert message.context.mode == GameMode.STANDARD
        assert message.context.players == 3
        assert message.context.visibility == Visibility.PRIVATE
        assert message.context.invited_handles == ["bender", "hermes"]

    def test_advertise_game_valid_no_handles(self) -> None:
        data = """
        {
          "message": "ADVERTISE_GAME",
          "context": {
            "name": "Leela's Game",
            "mode": "STANDARD",
            "players": 3,
            "visibility": "PUBLIC",
            "invited_handles": []
          }
        } 
        """
        message = Message.from_json(data)
        assert message.message == MessageType.ADVERTISE_GAME
        assert message.context.name == "Leela's Game"
        assert message.context.mode == GameMode.STANDARD
        assert message.context.players == 3
        assert message.context.visibility == Visibility.PUBLIC
        assert message.context.invited_handles == []

    def test_advertise_game_invalid_name_none(self) -> None:
        data = """
        {
          "message": "ADVERTISE_GAME",
          "context": {
            "name": null,
            "mode": "STANDARD",
            "players": 3,
            "visibility": "PUBLIC",
            "invited_handles": [ "bender", "hermes" ]
          }
        } 
        """
        with pytest.raises(ValueError, match=r"'name' must be a non-empty string"):
            Message.from_json(data)

    def test_advertise_game_invalid_name_empty(self) -> None:
        data = """
        {
          "message": "ADVERTISE_GAME",
          "context": {
            "name": "",
            "mode": "STANDARD",
            "players": 3,
            "visibility": "PUBLIC",
            "invited_handles": [ "bender", "hermes" ]
          }
        } 
        """
        with pytest.raises(ValueError, match=r"'name' must be a non-empty string"):
            Message.from_json(data)

    def test_advertise_game_invalid_mode_none(self) -> None:
        data = """
        {
          "message": "ADVERTISE_GAME",
          "context": {
            "name": "Leela's Game",
            "mode": null,
            "players": 3,
            "visibility": "PUBLIC",
            "invited_handles": [ "bender", "hermes" ]
          }
        } 
        """
        with pytest.raises(ValueError, match=r"'mode' must be one of \[ADULT, STANDARD\]"):
            Message.from_json(data)

    def test_advertise_game_invalid_mode_empty(self) -> None:
        data = """
        {
          "message": "ADVERTISE_GAME",
          "context": {
            "name": "Leela's Game",
            "mode": "",
            "players": 3,
            "visibility": "PUBLIC",
            "invited_handles": [ "bender", "hermes" ]
          }
        } 
        """
        with pytest.raises(ValueError, match=r"'mode' must be one of \[ADULT, STANDARD\]"):
            Message.from_json(data)

    def test_advertise_game_invalid_mode_bad(self) -> None:
        data = """
        {
          "message": "ADVERTISE_GAME",
          "context": {
            "name": "Leela's Game",
            "mode": "BOGUS",
            "players": 3,
            "visibility": "PUBLIC",
            "invited_handles": [ "bender", "hermes" ]
          }
        } 
        """
        with pytest.raises(ValueError, match=r"Invalid value 'BOGUS'"):
            Message.from_json(data)

    def test_advertise_game_invalid_player_small(self) -> None:
        data = """
        {
          "message": "ADVERTISE_GAME",
          "context": {
            "name": "Leela's Game",
            "mode": "STANDARD",
            "players": 1,
            "visibility": "PUBLIC",
            "invited_handles": [ "bender", "hermes" ]
          }
        } 
        """
        with pytest.raises(ValueError, match=r"'players' must be in \[2, 3, 4\] \(got 1\)"):
            Message.from_json(data)

    def test_advertise_game_invalid_player_large(self) -> None:
        data = """
        {
          "message": "ADVERTISE_GAME",
          "context": {
            "name": "Leela's Game",
            "mode": "STANDARD",
            "players": 5,
            "visibility": "PUBLIC",
            "invited_handles": [ "bender", "hermes" ]
          }
        } 
        """
        with pytest.raises(ValueError, match=r"'players' must be in \[2, 3, 4\] \(got 5\)"):
            Message.from_json(data)

    def test_advertise_game_invalid_visibility_none(self) -> None:
        data = """
        {
          "message": "ADVERTISE_GAME",
          "context": {
            "name": "Leela's Game",
            "mode": "STANDARD",
            "players": 3,
            "visibility": null,
            "invited_handles": [ "bender", "hermes" ]
          }
        } 
        """
        with pytest.raises(ValueError, match=r"'visibility' must be one of \[PRIVATE, PUBLIC\]"):
            Message.from_json(data)

    def test_advertise_game_invalid_visibility_empty(self) -> None:
        data = """
        {
          "message": "ADVERTISE_GAME",
          "context": {
            "name": "Leela's Game",
            "mode": "STANDARD",
            "players": 3,
            "visibility": "",
            "invited_handles": [ "bender", "hermes" ]
          }
        } 
        """
        with pytest.raises(ValueError, match=r"'visibility' must be one of \[PRIVATE, PUBLIC\]"):
            Message.from_json(data)

    def test_advertise_game_invalid_visibility_bad(self) -> None:
        data = """
        {
          "message": "ADVERTISE_GAME",
          "context": {
            "name": "Leela's Game",
            "mode": "STANDARD",
            "players": 3,
            "visibility": "BOGUS",
            "invited_handles": [ "bender", "hermes" ]
          }
        } 
        """
        with pytest.raises(ValueError, match=r"Invalid value 'BOGUS'"):
            Message.from_json(data)

    def test_advertise_game_invalid_handle_none(self) -> None:
        data = """
        {
          "message": "ADVERTISE_GAME",
          "context": {
            "name": "Leela's Game",
            "mode": "STANDARD",
            "players": 3,
            "visibility": "PUBLIC",
            "invited_handles": null
          }
        } 
        """
        with pytest.raises(ValueError, match=r"Message type ADVERTISE_GAME does not support this context"):
            Message.from_json(data)

    def test_advertise_game_invalid_handle_none_value(self) -> None:
        data = """
        {
          "message": "ADVERTISE_GAME",
          "context": {
            "name": "Leela's Game",
            "mode": "STANDARD",
            "players": 3,
            "visibility": "PUBLIC",
            "invited_handles": [ "bender", null ]
          }
        } 
        """
        with pytest.raises(ValueError, match=r"'invited_handles' elements must be non-empty strings"):
            Message.from_json(data)

    def test_advertise_game_invalid_handle_empty_value(self) -> None:
        data = """
        {
          "message": "ADVERTISE_GAME",
          "context": {
            "name": "Leela's Game",
            "mode": "STANDARD",
            "players": 3,
            "visibility": "PUBLIC",
            "invited_handles": [ "bender", "" ]
          }
        } 
        """
        with pytest.raises(ValueError, match=r"'invited_handles' elements must be non-empty strings"):
            Message.from_json(data)

    def test_join_game_valid(self) -> None:
        data = """
        {
          "message": "JOIN_GAME",
          "context": {
            "game_id": "f13b405e-36e5-45f3-a351-e45bf487acfe"
          }
        }
        """
        message = Message.from_json(data)
        assert message.message == MessageType.JOIN_GAME
        assert message.context.game_id == "f13b405e-36e5-45f3-a351-e45bf487acfe"

    def test_join_game_invalid_game_id_none(self) -> None:
        data = """
        {
          "message": "JOIN_GAME",
          "context": {
            "game_id": null
          }
        }
        """
        with pytest.raises(ValueError, match=r"'game_id' must be a non-empty string"):
            Message.from_json(data)

    def test_join_game_invalid_game_id_empty(self) -> None:
        data = """
        {
          "message": "JOIN_GAME",
          "context": {
            "game_id": ""
          }
        }
        """
        with pytest.raises(ValueError, match=r"'game_id' must be a non-empty string"):
            Message.from_json(data)

    def test_execute_move_valid(self) -> None:
        data = """
        {
          "message": "EXECUTE_MOVE",
          "context": {
            "move_id": "4"
          }
        }  
        """
        message = Message.from_json(data)
        assert message.message == MessageType.EXECUTE_MOVE
        assert message.context.move_id == "4"

    def test_execute_move_invalid_move_id_none(self) -> None:
        data = """
        {
          "message": "EXECUTE_MOVE",
          "context": {
            "move_id": null
          }
        }  
        """
        with pytest.raises(ValueError, match=r"'move_id' must be a non-empty string"):
            Message.from_json(data)

    def test_execute_move_invalid_move_id_empty(self) -> None:
        data = """
        {
          "message": "EXECUTE_MOVE",
          "context": {
            "move_id": ""
          }
        }  
        """
        with pytest.raises(ValueError, match=r"'move_id' must be a non-empty string"):
            Message.from_json(data)

    def test_send_message_valid(self) -> None:
        data = """
        {
          "message": "SEND_MESSAGE",
          "context": {
            "message": "Hello!",
            "recipient_handles": [ "hermes", "nibbler" ]
          }
        }  
        """
        message = Message.from_json(data)
        assert message.message == MessageType.SEND_MESSAGE
        assert message.context.message == "Hello!"
        assert message.context.recipient_handles == ["hermes", "nibbler"]

    def test_send_message_invalid_message_none(self) -> None:
        data = """
        {
          "message": "SEND_MESSAGE",
          "context": {
            "message": null,
            "recipient_handles": [ "hermes", "nibbler" ]
          }
        }  
        """
        with pytest.raises(ValueError, match=r"'message' must be a non-empty string"):
            Message.from_json(data)

    def test_send_message_invalid_message_empty(self) -> None:
        data = """
        {
          "message": "SEND_MESSAGE",
          "context": {
            "message": "",
            "recipient_handles": [ "hermes", "nibbler" ]
          }
        }  
        """
        with pytest.raises(ValueError, match=r"'message' must be a non-empty string"):
            Message.from_json(data)

    def test_send_message_invalid_recipients_none(self) -> None:
        data = """
        {
          "message": "SEND_MESSAGE",
          "context": {
            "message": "Hello!",
            "recipient_handles": null
          }
        }  
        """
        with pytest.raises(ValueError, match=r"Message type SEND_MESSAGE does not support this context"):
            Message.from_json(data)

    def test_send_message_invalid_recipients_empty(self) -> None:
        data = """
        {
          "message": "SEND_MESSAGE",
          "context": {
            "message": "Hello!",
            "recipient_handles": []
          }
        }  
        """
        with pytest.raises(ValueError, match=r"'recipient_handles' may not be empty"):
            Message.from_json(data)

    def test_send_message_invalid_recipients_none_value(self) -> None:
        data = """
        {
          "message": "SEND_MESSAGE",
          "context": {
            "message": "Hello!",
            "recipient_handles": [ "hermes", null ]
          }
        }  
        """
        with pytest.raises(ValueError, match=r"'recipient_handles' elements must be non-empty strings"):
            Message.from_json(data)

    def test_send_message_invalid_recipients_empty_value(self) -> None:
        data = """
        {
          "message": "SEND_MESSAGE",
          "context": {
            "message": "Hello!",
            "recipient_handles": [ "hermes", "" ]
          }
        }  
        """
        with pytest.raises(ValueError, match=r"'recipient_handles' elements must be non-empty strings"):
            Message.from_json(data)

    def test_register_player_roundtrip(self) -> None:
        context = RegisterPlayerContext(handle="leela")
        message = Message(MessageType.REGISTER_PLAYER, context)
        self.roundtrip(message)

    def test_reregister_player_roundtrip(self) -> None:
        message = Message(MessageType.REREGISTER_PLAYER)
        self.roundtrip(message)

    def test_unregister_player_roundtrip(self) -> None:
        message = Message(MessageType.UNREGISTER_PLAYER)
        self.roundtrip(message)

    def test_list_players_roundtrip(self) -> None:
        message = Message(MessageType.LIST_PLAYERS)
        self.roundtrip(message)

    def test_advertise_game_roundtrip(self) -> None:
        context = AdvertiseGameContext("Leela's Game", GameMode.STANDARD, 3, Visibility.PRIVATE, ["fry", "bender"])
        message = Message(MessageType.ADVERTISE_GAME, context)
        self.roundtrip(message)

    def test_list_available_games_roundtrip(self) -> None:
        message = Message(MessageType.LIST_AVAILABLE_GAMES)
        self.roundtrip(message)

    def test_join_game_roundtrip(self) -> None:
        context = JoinGameContext("game")
        message = Message(MessageType.JOIN_GAME, context)
        self.roundtrip(message)

    def test_quit_game_roundtrip(self) -> None:
        message = Message(MessageType.QUIT_GAME)
        self.roundtrip(message)

    def test_start_game_roundtrip(self) -> None:
        message = Message(MessageType.START_GAME)
        self.roundtrip(message)

    def test_cancel_game_roundtrip(self) -> None:
        message = Message(MessageType.CANCEL_GAME)
        self.roundtrip(message)

    def test_execute_move_roundtrip(self) -> None:
        context = ExecuteMoveContext("move")
        message = Message(MessageType.EXECUTE_MOVE, context)
        self.roundtrip(message)

    def test_retrieve_game_state_roundtrip(self) -> None:
        message = Message(MessageType.RETRIEVE_GAME_STATE)
        self.roundtrip(message)

    def test_send_message_roundtrip(self) -> None:
        context = SendMessageContext("Hello", ["fry", "bender"])
        message = Message(MessageType.SEND_MESSAGE, context)
        self.roundtrip(message)

    # noinspection PyMethodMayBeStatic
    def roundtrip(self, message: Message) -> None:
        data = message.to_json()
        copy = Message.from_json(data)
        assert message is not copy and message == copy
