# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import,too-many-public-methods

from typing import List

import pytest
from apologies.game import Card, CardType, GameMode, Pawn, Player, PlayerColor, PlayerView, Position
from apologies.rules import Action, ActionType, Move
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
    copy = Message.for_json(data)
    assert message is not copy
    assert message == copy


def create_view() -> PlayerView:
    """Create a realistic-looking player view for testing."""
    player = Player(PlayerColor.RED)
    player.turns = 16
    player.hand = [Card("card1", CardType.CARD_APOLOGIES), Card("card2", CardType.CARD_1)]
    player.pawns[0].position.move_to_square(32)
    player.pawns[1].position.move_to_safe(3)
    player.pawns[2].position.move_to_square(45)

    opponent = Player(PlayerColor.GREEN)
    opponent.turns = 15
    opponent.hand = [Card("card3", CardType.CARD_5), Card("card4", CardType.CARD_11)]
    opponent.pawns[1].position.move_to_home()
    opponent.pawns[2].position.move_to_safe(4)
    opponent.pawns[3].position.move_to_square(19)

    opponents = {opponent.color: opponent}

    return PlayerView(player, opponents)


def create_moves_simple() -> List[Move]:
    """Create a complex move for testing."""
    pawn = Pawn(color=PlayerColor.RED, index=1, name="V", position=Position().move_to_safe(3))
    position = Position().move_to_square(10)

    move = Move(
        id="a9fff13fbe5e46feaeda87382bf4c3b8",
        card=Card("card1", CardType.CARD_APOLOGIES),
        actions=[Action(ActionType.MOVE_TO_POSITION, pawn, position)],
        side_effects=[],
    )

    return [move]


def create_moves_complex() -> List[Move]:
    """Create a complex move for testing."""
    pawn1 = Pawn(color=PlayerColor.RED, index=1, name="V", position=Position().move_to_safe(3))
    position1 = Position().move_to_square(10)

    pawn2 = Pawn(color=PlayerColor.YELLOW, index=3, name="W", position=Position().move_to_square(10))
    position2 = Position().move_to_square(11)

    pawn3 = Pawn(color=PlayerColor.BLUE, index=2, name="X", position=Position().move_to_square(32))

    pawn4 = Pawn(color=PlayerColor.RED, index=3, name="Z", position=Position().move_to_square(17))
    position4 = Position().move_to_square(27)

    move1 = Move(
        id="a9fff13fbe5e46feaeda87382bf4c3b8",
        card=Card("card1", CardType.CARD_APOLOGIES),
        actions=[Action(ActionType.MOVE_TO_POSITION, pawn1, position1), Action(ActionType.MOVE_TO_POSITION, pawn2, position2),],
        side_effects=[Action(ActionType.MOVE_TO_START, pawn3)],
    )

    move2 = Move(
        id="d05f9b511b6e439aa18c8b70cbbcc5d3",
        card=Card("card2", CardType.CARD_10),
        actions=[Action(ActionType.MOVE_TO_POSITION, pawn4, position4)],
        side_effects=[],
    )

    return [move1, move2]


class TestGameStateChangeContext:
    def test_for_view(self) -> None:
        view = create_view()
        context = GameStateChangeContext.for_view(view)

        player = context.player
        assert player.color == PlayerColor.RED
        assert player.turns == 16
        assert player.hand == [CardType.CARD_APOLOGIES, CardType.CARD_1]
        assert player.pawns[0] == GameStatePawn(color=PlayerColor.RED, id="0", start=False, home=False, safe=None, square=32)
        assert player.pawns[1] == GameStatePawn(color=PlayerColor.RED, id="1", start=False, home=False, safe=3, square=None)
        assert player.pawns[2] == GameStatePawn(color=PlayerColor.RED, id="2", start=False, home=False, safe=None, square=45)
        assert player.pawns[3] == GameStatePawn(color=PlayerColor.RED, id="3", start=True, home=False, safe=None, square=None)

        assert len(context.opponents) == 1
        opponent = context.opponents[0]
        assert opponent.color == PlayerColor.GREEN
        assert opponent.turns == 15
        assert opponent.hand == [CardType.CARD_5, CardType.CARD_11]
        assert opponent.pawns[0] == GameStatePawn(color=PlayerColor.GREEN, id="0", start=True, home=False, safe=None, square=None)
        assert opponent.pawns[1] == GameStatePawn(color=PlayerColor.GREEN, id="1", start=False, home=True, safe=None, square=None)
        assert opponent.pawns[2] == GameStatePawn(color=PlayerColor.GREEN, id="2", start=False, home=False, safe=4, square=None)
        assert opponent.pawns[3] == GameStatePawn(color=PlayerColor.GREEN, id="3", start=False, home=False, safe=None, square=19)


class TestGamePlayerTurnContext:
    def test_for_moves_simple(self) -> None:
        moves = create_moves_simple()
        context = GamePlayerTurnContext.for_moves(moves)

        assert context.drawn_card == CardType.CARD_APOLOGIES  # because there is only one card among the moves
        assert len(context.moves) == 1

        move = context.moves["a9fff13fbe5e46feaeda87382bf4c3b8"]
        assert move.move_id == "a9fff13fbe5e46feaeda87382bf4c3b8"
        assert move.card == CardType.CARD_APOLOGIES
        assert len(move.actions) == 1
        assert len(move.side_effects) == 0
        assert move.actions[0].start == GameStatePawn(PlayerColor.RED, id="1", start=False, home=False, safe=3, square=None)
        assert move.actions[0].end == GameStatePawn(PlayerColor.RED, id="1", start=False, home=False, safe=None, square=10)

    def test_for_moves_complex(self) -> None:
        moves = create_moves_complex()
        context = GamePlayerTurnContext.for_moves(moves)

        assert context.drawn_card is None  # because there is more than one card among the legal moves
        assert len(context.moves) == 2

        move = context.moves["a9fff13fbe5e46feaeda87382bf4c3b8"]
        assert move.move_id == "a9fff13fbe5e46feaeda87382bf4c3b8"
        assert move.card == CardType.CARD_APOLOGIES
        assert len(move.actions) == 2
        assert len(move.side_effects) == 1
        assert move.actions[0].start == GameStatePawn(PlayerColor.RED, id="1", start=False, home=False, safe=3, square=None)
        assert move.actions[0].end == GameStatePawn(PlayerColor.RED, id="1", start=False, home=False, safe=None, square=10)
        assert move.actions[1].start == GameStatePawn(PlayerColor.YELLOW, id="3", start=False, home=False, safe=None, square=10)
        assert move.actions[1].end == GameStatePawn(PlayerColor.YELLOW, id="3", start=False, home=False, safe=None, square=11)
        assert move.side_effects[0].start == GameStatePawn(PlayerColor.BLUE, id="2", start=False, home=False, safe=None, square=32)
        assert move.side_effects[0].end == GameStatePawn(PlayerColor.BLUE, id="2", start=True, home=False, safe=None, square=None)

        move = context.moves["d05f9b511b6e439aa18c8b70cbbcc5d3"]
        assert move.move_id == "d05f9b511b6e439aa18c8b70cbbcc5d3"
        assert move.card == CardType.CARD_10
        assert len(move.actions) == 1
        assert len(move.side_effects) == 0
        assert move.actions[0].start == GameStatePawn(PlayerColor.RED, id="3", start=False, home=False, safe=None, square=17)
        assert move.actions[0].end == GameStatePawn(PlayerColor.RED, id="3", start=False, home=False, safe=None, square=27)


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
            Message.for_json(data)

    def test_from_json_missing_context(self) -> None:
        data = """
        {
          "message": "REGISTER_PLAYER"
        }
        """
        with pytest.raises(ValueError, match=r"Message type REGISTER_PLAYER requires a context"):
            Message.for_json(data)

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
            Message.for_json(data)

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
            Message.for_json(data)

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
            Message.for_json(data)


class TestRequest:

    """Test cases for request messages."""

    def test_register_player_valid(self) -> None:
        data = """
        {
          "message": "REGISTER_PLAYER",
          "context": {
            "handle": "1234567890123456789012345"
          }
        }
        """
        message = Message.for_json(data)
        assert message.message == MessageType.REGISTER_PLAYER
        assert message.context.handle == "1234567890123456789012345"

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
            Message.for_json(data)

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
            Message.for_json(data)

    def test_register_player_invalid_handle_length(self) -> None:
        data = """
        {
          "message": "REGISTER_PLAYER",
          "context": {
            "handle": "12345678901234567890123456"
          }
        }
        """
        with pytest.raises(ValueError, match=r"'handle' must not exceed length 25"):
            Message.for_json(data)

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
        message = Message.for_json(data)
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
        message = Message.for_json(data)
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
            Message.for_json(data)

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
            Message.for_json(data)

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
            Message.for_json(data)

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
            Message.for_json(data)

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
            Message.for_json(data)

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
            Message.for_json(data)

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
            Message.for_json(data)

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
            Message.for_json(data)

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
            Message.for_json(data)

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
            Message.for_json(data)

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
            Message.for_json(data)

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
            Message.for_json(data)

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
            Message.for_json(data)

    def test_join_game_valid(self) -> None:
        data = """
        {
          "message": "JOIN_GAME",
          "context": {
            "game_id": "f13b405e-36e5-45f3-a351-e45bf487acfe"
          }
        }
        """
        message = Message.for_json(data)
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
            Message.for_json(data)

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
            Message.for_json(data)

    def test_execute_move_valid(self) -> None:
        data = """
        {
          "message": "EXECUTE_MOVE",
          "context": {
            "move_id": "4"
          }
        }  
        """
        message = Message.for_json(data)
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
            Message.for_json(data)

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
            Message.for_json(data)

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
        message = Message.for_json(data)
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
            Message.for_json(data)

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
            Message.for_json(data)

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
            Message.for_json(data)

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
            Message.for_json(data)

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
            Message.for_json(data)

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
            Message.for_json(data)

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
        game = AvailableGame("game", "name", GameMode.STANDARD, "leela", 3, 2, Visibility.PUBLIC, ["fry", "bender"])
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
        game = AvailableGame("game", "name", GameMode.STANDARD, "leela", 3, 2, Visibility.PUBLIC, ["fry", "bender"])
        context = GameAdvertisedContext(game)
        message = Message(MessageType.GAME_ADVERTISED, context)
        roundtrip(message)

    def test_game_invitation_roundtrip(self) -> None:
        game = AvailableGame("game", "name", GameMode.STANDARD, "leela", 3, 2, Visibility.PUBLIC, ["fry", "bender"])
        context = GameInvitationContext(game)
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
        view = create_view()
        context = GameStateChangeContext.for_view(view)
        message = Message(MessageType.GAME_STATE_CHANGE, context)
        roundtrip(message)

    def test_game_player_turn_roundtrip(self) -> None:
        moves = create_moves_complex()
        context = GamePlayerTurnContext.for_moves(moves)
        message = Message(MessageType.GAME_PLAYER_TURN, context)
        roundtrip(message)
