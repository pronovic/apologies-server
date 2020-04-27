# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import,too-many-public-methods

import pytest
from apologies.game import GameMode, PlayerColor
from pendulum.datetime import DateTime
from pendulum.parser import parse

from apologiesserver.interface import *


# noinspection PyTypeChecker
def to_date(date: str) -> DateTime:
    # This function seems to have the wrong type hint
    return parse(date)  # type: ignore


def roundtrip(message: Message) -> None:
    """Round-trip a message to JSON and back, and confirm that it is equivalent."""
    data = message.to_json()
    copy = Message.from_json(data)
    assert message is not copy
    assert message == copy


class TestGeneral:

    """General test cases for the public interface functionality."""

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


class TestRequest:

    """Test cases for request messages."""

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
        roundtrip(message)

    def test_reregister_player_roundtrip(self) -> None:
        message = Message(MessageType.REREGISTER_PLAYER)
        roundtrip(message)

    def test_unregister_player_roundtrip(self) -> None:
        message = Message(MessageType.UNREGISTER_PLAYER)
        roundtrip(message)

    def test_list_players_roundtrip(self) -> None:
        message = Message(MessageType.LIST_PLAYERS)
        roundtrip(message)

    def test_advertise_game_roundtrip(self) -> None:
        context = AdvertiseGameContext("Leela's Game", GameMode.STANDARD, 3, Visibility.PRIVATE, ["fry", "bender"])
        message = Message(MessageType.ADVERTISE_GAME, context)
        roundtrip(message)

    def test_list_available_games_roundtrip(self) -> None:
        message = Message(MessageType.LIST_AVAILABLE_GAMES)
        roundtrip(message)

    def test_join_game_roundtrip(self) -> None:
        context = JoinGameContext("game")
        message = Message(MessageType.JOIN_GAME, context)
        roundtrip(message)

    def test_quit_game_roundtrip(self) -> None:
        message = Message(MessageType.QUIT_GAME)
        roundtrip(message)

    def test_start_game_roundtrip(self) -> None:
        message = Message(MessageType.START_GAME)
        roundtrip(message)

    def test_cancel_game_roundtrip(self) -> None:
        message = Message(MessageType.CANCEL_GAME)
        roundtrip(message)

    def test_execute_move_roundtrip(self) -> None:
        context = ExecuteMoveContext("move")
        message = Message(MessageType.EXECUTE_MOVE, context)
        roundtrip(message)

    def test_retrieve_game_state_roundtrip(self) -> None:
        message = Message(MessageType.RETRIEVE_GAME_STATE)
        roundtrip(message)

    def test_send_message_roundtrip(self) -> None:
        context = SendMessageContext("Hello", ["fry", "bender"])
        message = Message(MessageType.SEND_MESSAGE, context)
        roundtrip(message)


class TestEvent:
    def test_request_failed_roundtrip(self) -> None:
        context = RequestFailedContext(FailureReason.INTERNAL_ERROR, "it didn't work")
        message = Message(MessageType.REQUEST_FAILED, context)
        roundtrip(message)

    def test_registered_players_roundtrip(self) -> None:
        player = RegisteredPlayer(
            "handle",
            to_date("2020-04-27T09:02:14,334"),
            to_date("2020-04-27T13:19:23,992"),
            ConnectionState.CONNECTED,
            ActivityState.ACTIVE,
            PlayerState.JOINED,
            "game",
        )
        context = RegisteredPlayersContext(players=[player])
        message = Message(MessageType.REGISTERED_PLAYERS, context)
        roundtrip(message)

    def test_available_games_roundtrip(self) -> None:
        game = AvailableGame("game", "name", GameMode.STANDARD, "leela", 3, 2, Visibility.PUBLIC, True)
        context = AvailableGamesContext(games=[game])
        message = Message(MessageType.AVAILABLE_GAMES, context)
        roundtrip(message)

    def test_player_registered_roundtrip(self) -> None:
        context = PlayerRegisteredContext("player")
        message = Message(MessageType.PLAYER_REGISTERED, context)
        roundtrip(message)

    def test_player_disconnected_roundtrip(self) -> None:
        message = Message(MessageType.PLAYER_DISCONNECTED)
        roundtrip(message)

    def test_player_idle_roundtrip(self) -> None:
        message = Message(MessageType.PLAYER_IDLE)
        roundtrip(message)

    def test_player_inactive_roundtrip(self) -> None:
        message = Message(MessageType.PLAYER_INACTIVE)
        roundtrip(message)

    def test_player_message_received_roundtrip(self) -> None:
        context = PlayerMessageReceivedContext("leela", ["hermes", "bender"], "Hello")
        message = Message(MessageType.PLAYER_MESSAGE_RECEIVED, context)
        roundtrip(message)

    def test_game_advertised_roundtrip(self) -> None:
        context = GameAdvertisedContext("game", "name", GameMode.ADULT, "leela", 3, Visibility.PRIVATE, ["fry", "nibbler"])
        message = Message(MessageType.GAME_ADVERTISED, context)
        roundtrip(message)

    def test_game_invitation_roundtrip(self) -> None:
        context = GameInvitationContext("game", "name", GameMode.STANDARD, "leela", 3, Visibility.PUBLIC)
        message = Message(MessageType.GAME_INVITATION, context)
        roundtrip(message)

    def test_game_joined_roundtrip(self) -> None:
        context = GameJoinedContext("game")
        message = Message(MessageType.GAME_JOINED, context)
        roundtrip(message)

    def test_game_started_roundtrip(self) -> None:
        message = Message(MessageType.GAME_STARTED)
        roundtrip(message)

    def test_game_cancelled_roundtrip(self) -> None:
        context = GameCancelledContext(CancelledReason.CANCELLED, "YELLOW player (nibbler) quit")
        message = Message(MessageType.GAME_CANCELLED, context)
        roundtrip(message)

    def test_game_completed_roundtrip(self) -> None:
        context = GameCompletedContext("YELLOW player (nibbler) won after 46 turns")
        message = Message(MessageType.GAME_COMPLETED, context)
        roundtrip(message)

    def test_game_idle_roundtrip(self) -> None:
        message = Message(MessageType.GAME_IDLE)
        roundtrip(message)

    def test_game_inactive_roundtrip(self) -> None:
        message = Message(MessageType.GAME_INACTIVE)
        roundtrip(message)

    def test_game_obsolete_roundtrip(self) -> None:
        message = Message(MessageType.GAME_OBSOLETE)
        roundtrip(message)

    def test_game_player_change_roundtrip(self) -> None:
        red = GamePlayer("leela", PlayerType.HUMAN, PlayerState.QUIT)
        yellow = GamePlayer(None, PlayerType.PROGRAMMATIC, PlayerState.PLAYING)
        players = {PlayerColor.RED: red, PlayerColor.YELLOW: yellow}
        context = GamePlayerChangeContext("YELLOW player (leela) quit", players)
        message = Message(MessageType.GAME_PLAYER_CHANGE, context)
        roundtrip(message)

    def test_game_state_change_roundtrip(self) -> None:
        context = GameStateChangeContext("blech")  # TODO: change this once we know what this context looks like
        message = Message(MessageType.GAME_STATE_CHANGE, context)
        roundtrip(message)

    def test_game_player_turn_roundtrip(self) -> None:
        context = GamePlayerTurnContext("blech")  # TODO: change this once we know what this context looks like
        message = Message(MessageType.GAME_PLAYER_TURN, context)
        roundtrip(message)
