# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=redefined-outer-name,wildcard-import,protected-access,too-many-lines

import random
from typing import Dict, List
from unittest.mock import MagicMock, patch

import pendulum
import pytest
from apologies.engine import Character
from apologies.game import GameMode, PlayerColor
from apologies.rules import Rules
from apologies.source import NoOpInputSource, RewardV1InputSource
from ordered_set import OrderedSet

from apologiesserver.interface import *
from apologiesserver.manager import (
    _MANAGER,
    _NAMES,
    CurrentTurn,
    StateManager,
    TrackedEngine,
    TrackedGame,
    TrackedPlayer,
    TrackedWebsocket,
    manager,
)

from .util import random_string, to_date


def create_test_player(player_id="id", handle="handle"):
    return TrackedPlayer(player_id=player_id, websocket=MagicMock(), handle=handle)


def create_test_game():
    engine = MagicMock()
    return TrackedGame("game_id", "handle", "name", GameMode.STANDARD, 3, Visibility.PRIVATE, [], engine=engine)


def check_fully_joined(players: int, game_players: int) -> bool:
    game = TrackedGame("game_id", "handle", "name", GameMode.STANDARD, 3, Visibility.PRIVATE, [])
    game.players = players
    game.game_players = {random_string(): MagicMock() for _ in range(game_players)}
    return game.is_fully_joined()


def check_is_in_progress(advertised: bool, playing: bool) -> bool:
    game = TrackedGame("game_id", "handle", "name", GameMode.STANDARD, 3, Visibility.PRIVATE, ["bender", "fry"])
    game.is_advertised = MagicMock()  # type: ignore
    game.is_playing = MagicMock()  # type: ignore
    game.is_advertised.return_value = advertised
    game.is_playing.return_value = playing
    return game.is_in_progress()


def check_is_viable(advertised: bool, available: int) -> bool:
    game = TrackedGame("game_id", "handle", "name", GameMode.STANDARD, 3, Visibility.PRIVATE, [])
    game.is_advertised = MagicMock()  # type: ignore
    game.get_available_player_count = MagicMock()  # type: ignore
    game.is_advertised.return_value = advertised
    game.get_available_player_count.return_value = available
    return game.is_viable()


class TestFunctions:
    """
    Test Python functions.
    """

    def test_manager(self):
        assert _MANAGER is not None
        assert manager() is _MANAGER


class TestTrackedWebsocket:
    """
    Test the TrackedWebsocket class.
    """

    # noinspection PyTypeChecker
    def test_mark_active(self):
        now = pendulum.now()
        tracked = TrackedWebsocket(MagicMock())
        tracked.last_active_date = None
        tracked.activity_state = None
        tracked.mark_active()
        assert tracked.last_active_date >= now
        assert tracked.activity_state == ActivityState.ACTIVE

    def test_mark_idle(self):
        tracked = TrackedWebsocket(MagicMock())
        tracked.activity_state = None
        tracked.mark_idle()
        assert tracked.activity_state == ActivityState.IDLE

    def test_mark_inactive(self):
        tracked = TrackedWebsocket(MagicMock())
        tracked.activity_state = None
        tracked.mark_inactive()
        assert tracked.activity_state == ActivityState.INACTIVE


class TestTrackedPlayer:
    """
    Test the TrackedPlayer class.
    """

    def test_for_context(self):
        now = pendulum.now()
        websocket = MagicMock()
        player = TrackedPlayer.for_context("id", websocket, "handle")
        assert player.player_id == "id"
        assert player.handle == "handle"
        assert player.websocket is websocket
        assert player.registration_date >= now
        assert player.last_active_date >= now
        assert player.activity_state == ActivityState.ACTIVE
        assert player.connection_state == ConnectionState.CONNECTED
        assert player.player_state == PlayerState.WAITING
        assert player.game_id is None

    def test_to_registered_player(self):
        websocket = MagicMock()
        player = TrackedPlayer(player_id="id", websocket=websocket, handle="handle", game_id="game_id")
        registered = player.to_registered_player()
        assert registered.handle == "handle"
        assert registered.registration_date == player.registration_date
        assert registered.last_active_date == player.last_active_date
        assert registered.connection_state == player.connection_state
        assert registered.activity_state == player.activity_state
        assert registered.player_state == player.player_state
        assert registered.game_id == player.game_id

    # noinspection PyTypeChecker
    def test_mark_active(self):
        now = pendulum.now()
        player = create_test_player()
        player.last_active_date = None
        player.activity_state = None
        player.connection_state = None
        player.mark_active()
        assert player.last_active_date >= now
        assert player.activity_state == ActivityState.ACTIVE
        assert player.connection_state == ConnectionState.CONNECTED

    def test_mark_idle(self):
        player = create_test_player()
        player.activity_state = None
        player.mark_idle()
        assert player.activity_state == ActivityState.IDLE

    def test_mark_inactive(self):
        player = create_test_player()
        player.activity_state = None
        player.mark_inactive()
        assert player.activity_state == ActivityState.INACTIVE

    def test_mark_joined(self):
        game = MagicMock(game_id="game_id")
        player = create_test_player()
        player.game_id = None
        player.player_state = None
        player.mark_joined(game)
        assert player.game_id == "game_id"
        assert player.player_state == PlayerState.JOINED

    def test_mark_playing(self):
        player = create_test_player()
        player.player_state = None
        player.mark_playing()
        assert player.player_state == PlayerState.PLAYING

    def test_mark_quit(self):
        player = create_test_player()
        player.game_id = "game_id"
        player.player_state = None
        player.mark_quit()
        assert player.game_id is None
        assert player.player_state == PlayerState.WAITING  # they move through QUIT and back to WAITING

    def test_mark_disconnected(self):
        player = create_test_player()
        player.game_id = "game_id"
        player.activity_state = None
        player.connection_state = None
        player.player_state = None
        player.mark_disconnected()
        assert player.game_id is None
        assert player.websocket is None
        assert player.activity_state == ActivityState.IDLE
        assert player.connection_state == ConnectionState.DISCONNECTED
        assert player.player_state == PlayerState.WAITING  # they move through QUIT and back to WAITING


class TestCurrentTurn:
    """
    Test the CurrentTurn class.
    """

    def test_draw_again(self):
        current = CurrentTurn(handle="handle", color=PlayerColor.RED, view=None, movelist=None, movedict=None)
        move = MagicMock(id="move_id")
        view = MagicMock()
        engine = MagicMock()
        engine.game.create_player_view.return_value = view
        engine.construct_legal_moves.return_value = (None, [move])
        turn = current.draw_again(engine)
        engine.game.create_player_view.assert_called_once_with(PlayerColor.RED)
        engine.construct_legal_moves.assert_called_once_with(view)
        assert turn.handle == "handle"
        assert turn.color == PlayerColor.RED
        assert turn.view is view
        assert turn.movelist == [move]
        assert turn.movedict == {"move_id": move}

    def test_next_player(self):
        move = MagicMock(id="move_id")
        character = MagicMock()
        character.configure_mock(name="handle")  # the "name" attribute means something special in the constructor
        view = MagicMock()
        engine = MagicMock()
        engine.next_turn.return_value = (PlayerColor.RED, character)
        engine.game.create_player_view.return_value = view
        engine.construct_legal_moves.return_value = (None, [move])
        turn = CurrentTurn.next_player(engine)
        engine.next_turn.assert_called_once()
        engine.game.create_player_view.assert_called_once_with(PlayerColor.RED)
        engine.construct_legal_moves.assert_called_once_with(view)
        assert turn.handle == "handle"
        assert turn.color == PlayerColor.RED
        assert turn.view is view
        assert turn.movelist == [move]
        assert turn.movedict == {"move_id": move}


class TestTrackedEngine:
    """
    Test the TrackedEngine class.
    """

    # noinspection PyTypeChecker
    @patch("apologiesserver.manager.CurrentTurn")
    def test_start_game(self, current_turn):
        replacement = MagicMock()
        current_turn.next_player.return_value = replacement
        mode = GameMode.STANDARD
        handles = ["leela", "bender"]
        engine = TrackedEngine()
        engine._engine = MagicMock()
        with pytest.raises(ProcessingError, match=r"Illegal state for operation"):
            engine.start_game(mode, handles=handles)  # there's already an engine
        engine._engine = None
        engine._colors = {}
        engine._current = None
        colors = engine.start_game(mode, handles)
        assert colors == engine._colors and colors is not engine._colors  # it's a copy
        assert engine._engine.mode == mode
        assert engine._engine.characters == [
            Character(name="leela", source=NoOpInputSource()),
            Character(name="bender", source=NoOpInputSource()),
        ]
        assert engine._engine.started is True
        assert "leela" in engine._colors and "bender" in engine._colors and engine._colors["leela"] != engine._colors["bender"]
        assert engine._current is replacement
        current_turn.next_player.assert_called_with(engine._engine)

    def test_stop_game(self):
        engine = TrackedEngine()
        engine._engine = MagicMock()
        engine._colors = {"a": "b"}
        engine._current = MagicMock()
        engine.stop_game()
        assert engine._engine is None
        assert engine._colors == {}
        assert engine._current is None

    def test_get_next_turn(self):
        engine = TrackedEngine()
        engine._current = None
        with pytest.raises(ProcessingError, match=r"Illegal state for operation"):
            engine.get_next_turn()
        engine._current = MagicMock(handle="handle")
        assert engine.get_next_turn() == "handle"

    def test_get_legal_moves(self):
        move = MagicMock()
        engine = TrackedEngine()
        engine._current = None
        with pytest.raises(ProcessingError, match=r"Illegal state for operation"):
            engine.get_legal_moves("handle")  # no current turn
        engine._current = MagicMock(handle="handle")
        engine._current.movelist = [move]
        with pytest.raises(ProcessingError, match=r"Illegal state for operation"):
            engine.get_legal_moves("bogus")  # unknown handle
        assert engine.get_legal_moves("handle") == [move]

    def test_get_player_view(self):
        view = MagicMock()
        engine = TrackedEngine()
        engine._engine = None
        with pytest.raises(ProcessingError, match=r"Illegal state for operation"):
            engine.get_player_view("handle")  # no engine
        engine._engine = MagicMock()
        engine._engine.game.create_player_view.return_value = view
        engine._colors = {"handle": PlayerColor.RED}
        with pytest.raises(ProcessingError, match=r"Illegal state for operation"):
            engine.get_player_view("bogus")  # unknown handle
        assert engine.get_player_view("handle") is view
        engine._engine.game.create_player_view.assert_called_once_with(PlayerColor.RED)

    def test_get_recent_history(self):
        engine = TrackedEngine()
        engine._engine = None
        with pytest.raises(ProcessingError, match=r"Illegal state for operation"):
            engine.get_recent_history(10)  # no engine
        engine._engine = MagicMock()
        engine._engine.game = None
        with pytest.raises(ProcessingError, match=r"Illegal state for operation"):
            engine.get_recent_history(10)  # no game
        engine._engine.game = MagicMock(history=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11])
        assert engine.get_recent_history(10) == [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]

    def test_is_move_pending(self):
        engine = TrackedEngine()
        engine._current = None
        with pytest.raises(ProcessingError, match=r"Illegal state for operation"):
            engine.is_move_pending("handle")  # no current turn
        engine._current = MagicMock(handle="handle")
        assert engine.is_move_pending("bogus") is False
        assert engine.is_move_pending("handle") is True

    def test_is_legal_move(self):
        move = MagicMock()
        engine = TrackedEngine()
        engine._current = None
        with pytest.raises(ProcessingError, match=r"Illegal state for operation"):
            engine.is_legal_move("handle", "move_id")  # no current turn
        engine._current = MagicMock(handle="handle")
        engine._current.movedict = {"move_id": move}
        assert engine.is_legal_move("bogus", "move_id") is False  # handle doesn't match current turn
        assert engine.is_legal_move("handle", "bogus") is False  # move isn't in the current turn's list
        assert engine.is_legal_move("handle", "move_id") is True

    def test_execute_move_validations(self):
        move = MagicMock()
        engine = TrackedEngine()
        engine._engine = None
        engine._current = None
        with pytest.raises(ProcessingError, match=r"Illegal state for operation"):
            engine.execute_move("handle", "move_id")  # no engine
        engine._engine = MagicMock()
        with pytest.raises(ProcessingError, match=r"Illegal state for operation"):
            engine.execute_move("handle", "move_id")  # no current turn
        engine._current = MagicMock(handle="handle")
        engine._current.movedict = {"move_id": move}
        with pytest.raises(ProcessingError, match=r"Illegal state for operation"):
            engine.execute_move("bogus", "move_id")  # handle doesn't match current turn
        with pytest.raises(ProcessingError, match=r"Illegal state for operation"):
            engine.execute_move("handle", "move_id")  # can't find color mapping for handle
        engine._colors = {"handle": PlayerColor.RED}
        with pytest.raises(ProcessingError, match=r"Illegal state for operation"):
            engine.execute_move("handle", "bogus")  # unknown move

    def test_execute_move_completed(self):
        character = MagicMock()
        character.configure_mock(name="handle")  # the "name" attribute means something special in the constructor
        player = MagicMock(color=PlayerColor.YELLOW, turns=42)
        move = MagicMock()
        current = MagicMock(handle="handle")
        engine = TrackedEngine()
        engine._engine = MagicMock(completed=True)
        engine._current = current
        engine._current.movedict = {"move_id": move}
        engine._colors = {"handle": PlayerColor.RED}
        engine._engine.winner.return_value = (character, player)  # only set if the game is completed
        engine._engine.execute_move.return_value = True  # turn is always true if the game is completed
        assert engine.execute_move("handle", "move_id") == (True, "handle", "Player handle won after 42 turns")
        assert engine._current is None
        engine._engine.execute_move.assert_called_once_with(PlayerColor.RED, move)

    def test_execute_move_not_done(self):
        character = MagicMock()
        character.configure_mock(name="handle")  # the "name" attribute means something special in the constructor
        move = MagicMock()
        current = MagicMock(handle="handle")
        again = MagicMock()
        engine = TrackedEngine()
        engine._engine = MagicMock(completed=False)
        engine._current = current
        engine._current.draw_again.return_value = again
        engine._current.movedict = {"move_id": move}
        engine._colors = {"handle": PlayerColor.RED}
        engine._engine.winner.return_value = None  # only set if the game is completed
        engine._engine.execute_move.return_value = False  # player's turn is not done yet, so current does not change
        assert engine.execute_move("handle", "move_id") == (False, None, None)
        assert engine._current is again
        current.draw_again.assert_called_once_with(engine._engine)
        engine._engine.execute_move.assert_called_once_with(PlayerColor.RED, move)

    @patch("apologiesserver.manager.CurrentTurn")
    def test_execute_move_done(self, current_turn):
        character = MagicMock()
        character.configure_mock(name="handle")  # the "name" attribute means something special in the constructor
        move = MagicMock()
        current = MagicMock(handle="handle")
        replacement = MagicMock()
        current_turn.next_player.return_value = replacement
        engine = TrackedEngine()
        engine._engine = MagicMock(completed=False)
        engine._current = current
        engine._current.movedict = {"move_id": move}
        engine._colors = {"handle": PlayerColor.RED}
        engine._engine.winner.return_value = None  # only set if the game is completed
        engine._engine.execute_move.return_value = True  # player's turn is now done, so current will change
        assert engine.execute_move("handle", "move_id") == (False, None, None)
        assert engine._current is replacement
        engine._engine.execute_move.assert_called_once_with(PlayerColor.RED, move)


# pylint: disable=too-many-public-methods
class TestTrackedGame:
    """
    Test the TrackedGame class.
    """

    def test_for_context(self):
        now = pendulum.now()
        context = AdvertiseGameContext("name", GameMode.STANDARD, 3, Visibility.PUBLIC, ["a", "b"])
        game = TrackedGame.for_context("handle", "game_id", context)
        assert game.game_id == "game_id"
        assert game.advertiser_handle == "handle"
        assert game.name == "name"
        assert game.mode == GameMode.STANDARD
        assert game.players == 3
        assert game.visibility == Visibility.PUBLIC
        assert game.invited_handles == ["a", "b"]
        assert game.advertised_date >= now
        assert game.last_active_date >= now
        assert game.started_date is None
        assert game.completed_date is None
        assert game.game_state == GameState.ADVERTISED
        assert game.activity_state == ActivityState.ACTIVE
        assert game.cancelled_reason is None
        assert game.completed_comment is None
        assert game.game_players == {}

    def test_to_advertised_game(self):
        game = TrackedGame("game_id", "handle", "name", GameMode.STANDARD, 3, Visibility.PUBLIC, ["a", "b"])
        advertised = game.to_advertised_game()
        assert advertised.game_id == "game_id"
        assert advertised.name == "name"
        assert advertised.mode == GameMode.STANDARD
        assert advertised.advertiser_handle == "handle"
        assert advertised.players == 3
        assert advertised.available == 3
        assert advertised.visibility == Visibility.PUBLIC
        assert advertised.invited_handles == ["a", "b"]

    def test_get_game_players(self):
        game = TrackedGame("game_id", "handle", "name", GameMode.STANDARD, 3, Visibility.PUBLIC, ["a", "b"])
        gp1 = MagicMock()
        gp2 = MagicMock()
        game.game_players = {"gp1": gp1, "gp2": gp2}
        assert game.get_game_players() == [gp1, gp2]

    def test_get_available_players(self):
        game = TrackedGame("game_id", "handle", "name", GameMode.STANDARD, 3, Visibility.PUBLIC, ["a", "b"])
        gp1 = MagicMock(player_state=PlayerState.WAITING)
        gp2 = MagicMock(player_state=PlayerState.JOINED)
        gp3 = MagicMock(player_state=PlayerState.PLAYING)
        gp4 = MagicMock(player_state=PlayerState.FINISHED)
        gp5 = MagicMock(player_state=PlayerState.QUIT)
        gp6 = MagicMock(player_state=PlayerState.DISCONNECTED)
        game.game_players = {
            "gp1": gp1,
            "gp2": gp2,
            "gp3": gp3,
            "gp4": gp4,
            "gp5": gp5,
            "gp6": gp6,
        }  # obviously not realistic
        assert game.get_available_players() == [
            gp1,
            gp2,
            gp3,
            gp4,
        ]
        assert game.get_available_player_count() == 4

    def test_get_next_turn(self):
        player = MagicMock(player_type=PlayerType.PROGRAMMATIC)
        game = create_test_game()
        game.game_players["handle"] = player
        game._engine.get_next_turn.return_value = "handle"
        assert game.get_next_turn() == ("handle", PlayerType.PROGRAMMATIC)

    def test_get_legal_moves(self):
        move = MagicMock()
        game = create_test_game()
        game._engine.get_legal_moves.return_value = [move]
        assert game.get_legal_moves("handle") == [move]
        game._engine.get_legal_moves.assert_called_once_with("handle")

    def test_get_player_view(self):
        view = MagicMock()
        game = create_test_game()
        game._engine.get_player_view.return_value = view
        assert game.get_player_view("handle") == view
        game._engine.get_player_view.assert_called_once_with("handle")

    def test_get_recent_history(self):
        history = MagicMock()
        game = create_test_game()
        game._engine.get_recent_history.return_value = [history]
        assert game.get_recent_history(10) == [history]
        game._engine.get_recent_history.assert_called_once_with(10)

    def test_is_available_public(self):
        game = TrackedGame("game_id", "handle", "name", GameMode.STANDARD, 3, Visibility.PUBLIC, ["bender", "fry"])

        # If a public game is advertised, then it is available anyone (regardless of whether they are invited)
        game.game_state = GameState.ADVERTISED
        assert game.is_available("leela") is True
        assert game.is_available("bender") is True
        assert game.is_available("fry") is True

        # If any game is not advertised, then it is not available to anyone
        for state in [state for state in GameState if state != GameState.ADVERTISED]:
            game.game_state = state
            assert game.is_available("leela") is False
            assert game.is_available("bender") is False
            assert game.is_available("fry") is False

    def test_is_available_private(self):
        game = TrackedGame("game_id", "handle", "name", GameMode.STANDARD, 3, Visibility.PRIVATE, ["bender", "fry"])

        # If a private game is advertised, then it is available only for an invited handle
        game.game_state = GameState.ADVERTISED
        assert game.is_available("leela") is False
        assert game.is_available("bender") is True
        assert game.is_available("fry") is True

        # If any game is not advertised, then it is not available to anyone
        for state in [state for state in GameState if state != GameState.ADVERTISED]:
            game.game_state = state
            assert game.is_available("leela") is False
            assert game.is_available("bender") is False
            assert game.is_available("fry") is False

    def test_is_advertised(self):
        game = create_test_game()

        game.game_state = GameState.ADVERTISED
        assert game.is_advertised() is True

        for state in [state for state in GameState if state != GameState.ADVERTISED]:
            game.game_state = state
            assert game.is_advertised() is False

    def test_is_playing(self):
        game = create_test_game()

        game.game_state = GameState.PLAYING
        assert game.is_playing() is True

        for state in [state for state in GameState if state != GameState.PLAYING]:
            game.game_state = state
            assert game.is_playing() is False

    def test_is_in_progress(self):
        assert check_is_in_progress(True, True) is True
        assert check_is_in_progress(True, False) is True
        assert check_is_in_progress(False, True) is True
        assert check_is_in_progress(False, False) is False

    def test_is_fully_joined(self):
        assert check_fully_joined(2, 0) is False
        assert check_fully_joined(2, 1) is False
        assert check_fully_joined(2, 2) is True
        assert check_fully_joined(3, 0) is False
        assert check_fully_joined(3, 1) is False
        assert check_fully_joined(3, 2) is False
        assert check_fully_joined(3, 3) is True
        assert check_fully_joined(3, 0) is False
        assert check_fully_joined(4, 1) is False
        assert check_fully_joined(4, 2) is False
        assert check_fully_joined(4, 3) is False
        assert check_fully_joined(4, 4) is True

    def test_is_viable(self):
        for available in [0, 1, 2, 3, 4]:
            assert check_is_viable(True, available) is True
        for available in [0, 1]:
            assert check_is_viable(False, available) is False
        for available in [2, 3, 4]:
            assert check_is_viable(False, available) is True

    def test_is_move_pending(self):
        game = create_test_game()
        game._engine.is_move_pending.return_value = True
        assert game.is_move_pending("handle") is True
        game._engine.is_move_pending.assert_called_once_with("handle")

    def test_is_legal_move(self):
        game = create_test_game()
        game._engine.is_legal_move.return_value = True
        assert game.is_legal_move("handle", "move_id") is True
        game._engine.is_legal_move.assert_called_once_with("handle", "move_id")

    # noinspection PyTypeChecker
    def test_mark_active(self):
        now = pendulum.now()
        game = create_test_game()
        game.last_active_date = None
        game.activity_state = None
        game.mark_active()
        assert game.last_active_date >= now
        assert game.activity_state == ActivityState.ACTIVE

    def test_mark_idle(self):
        game = create_test_game()
        game.activity_state = None
        game.mark_idle()
        assert game.activity_state == ActivityState.IDLE

    def test_mark_inactive(self):
        game = create_test_game()
        game.activity_state = None
        game.mark_inactive()
        assert game.activity_state == ActivityState.INACTIVE

    def test_mark_joined_illegal_state(self):
        game = create_test_game()
        for game_state in [game_state for game_state in GameState if game_state != GameState.ADVERTISED]:
            with pytest.raises(ProcessingError, match=r"Illegal state for operation"):
                game.game_state = game_state
                game.mark_joined("handle")
                assert "leela" not in game.game_players

    def test_mark_joined(self):
        game = create_test_game()
        game.game_state = GameState.ADVERTISED  # otherwise it's an illegal state
        game.mark_joined("leela")
        assert len(game.game_players) == 1
        assert game.game_players["leela"].handle == "leela"
        assert game.game_players["leela"].player_color is None
        assert game.game_players["leela"].player_type == PlayerType.HUMAN
        assert game.game_players["leela"].player_state == PlayerState.JOINED

    def test_mark_started_illegal_state(self):
        game = create_test_game()
        game.players = 4
        game.mark_joined("leela")
        game.mark_joined("bender")
        for game_state in [game_state for game_state in GameState if game_state != GameState.ADVERTISED]:
            with pytest.raises(ProcessingError, match=r"Illegal state for operation"):
                game.game_state = game_state
                game.mark_started()
            assert game.game_state == game_state  # should not change

    # noinspection PyTypeChecker
    def test_mark_started(self):
        now = pendulum.now()
        game = create_test_game()
        game.players = 4
        game.mark_joined("leela")
        game.mark_joined("bender")

        # this stubs out the start_game() method and gives us access to what it returns, for later validation
        # it's a little funky, but works pretty well
        colors = {}

        def stubbed_start_game(mode, handles):
            nonlocal colors
            assert mode == game.mode
            colors = {
                handles[0]: PlayerColor.YELLOW,
                handles[1]: PlayerColor.RED,
                handles[2]: PlayerColor.GREEN,
                handles[3]: PlayerColor.BLUE,
            }
            return colors

        game._engine.start_game = stubbed_start_game

        game.game_state = GameState.ADVERTISED  # otherwise it's an illegal state
        game.last_active_date = None
        game.started_date = None
        game.mark_started()
        assert game.game_state == GameState.PLAYING
        assert game.last_active_date >= now
        assert game.started_date >= now
        assert len(game.game_players) == 4  # the two we added and two programmatic ones

        programmatic = [handle for handle in game.game_players.keys() if handle not in ("leela", "bender")]
        assert len(programmatic) == 2
        for handle in programmatic:
            assert handle in _NAMES  # the name gets randomly assigned
            assert game.game_players[handle].handle == handle
            assert game.game_players[handle].player_color == colors[handle]  # check that it gets what was returned by start_game()
            assert game.game_players[handle].player_type == PlayerType.PROGRAMMATIC
            assert game.game_players[handle].player_state == PlayerState.PLAYING

        human = [handle for handle in game.game_players.keys() if handle in ("leela", "bender")]
        assert len(human) == 2
        for handle in ["leela", "bender"]:
            assert game.game_players[handle].handle == handle
            assert game.game_players[handle].player_color == colors[handle]  # check that it gets what was returned by start_game()
            assert game.game_players[handle].player_type == PlayerType.HUMAN
            assert game.game_players[handle].player_state == PlayerState.PLAYING

    def test_mark_completed_illegal_state(self):
        game = create_test_game()
        for game_state in [game_state for game_state in GameState if game_state != GameState.PLAYING]:
            with pytest.raises(ProcessingError, match=r"Illegal state for operation"):
                game.game_state = game_state
                game.mark_completed("comment")
            assert game.game_state == game_state  # should not change
            game._engine.stop_game.assert_not_called()

    # noinspection PyTypeChecker
    def test_mark_completed(self):
        gp1 = GamePlayer("gp1", PlayerColor.YELLOW, PlayerType.PROGRAMMATIC, PlayerState.PLAYING)
        gp2 = GamePlayer("gp2", PlayerColor.RED, PlayerType.HUMAN, PlayerState.PLAYING)
        gp1_copy = GamePlayer("gp1", PlayerColor.YELLOW, PlayerType.PROGRAMMATIC, PlayerState.FINISHED)
        gp2_copy = GamePlayer("gp2", PlayerColor.RED, PlayerType.HUMAN, PlayerState.FINISHED)
        now = pendulum.now()
        game = create_test_game()
        game.game_players = {"gp1": gp1, "gp2": gp2}
        game.completed_date = None
        game.game_state = GameState.PLAYING  # otherwise it's an illegal state
        game.completed_comment = None
        game.mark_completed("comment")
        assert game.completed_date >= now
        assert game.game_state == GameState.COMPLETED
        assert game.completed_comment == "comment"
        assert game.game_players == {"gp1": gp1_copy, "gp2": gp2_copy}
        game._engine.stop_game.assert_called_once()

    def test_mark_cancelled_illegal_state(self):
        game = create_test_game()
        for game_state in [game_state for game_state in GameState if game_state not in (GameState.PLAYING, GameState.ADVERTISED)]:
            with pytest.raises(ProcessingError, match=r"Illegal state for operation"):
                game.game_state = game_state
                game.mark_cancelled(CancelledReason.CANCELLED, "comment")
            assert game.game_state == game_state  # should not change
            game._engine.stop_game.assert_not_called()

    # noinspection PyTypeChecker
    def test_mark_cancelled(self):
        for game_state in (GameState.PLAYING, GameState.ADVERTISED):  # either state is legal
            gp1 = GamePlayer("gp1", PlayerColor.YELLOW, PlayerType.PROGRAMMATIC, PlayerState.PLAYING)
            gp2 = GamePlayer("gp2", PlayerColor.RED, PlayerType.HUMAN, PlayerState.PLAYING)
            gp1_copy = GamePlayer("gp1", PlayerColor.YELLOW, PlayerType.PROGRAMMATIC, PlayerState.FINISHED)
            gp2_copy = GamePlayer("gp2", PlayerColor.RED, PlayerType.HUMAN, PlayerState.FINISHED)
            now = pendulum.now()
            game = create_test_game()
            game.game_players = {"gp1": gp1, "gp2": gp2}
            game.completed_date = None
            game.game_state = game_state
            game.completed_comment = None
            game.mark_cancelled(CancelledReason.NOT_VIABLE, "comment")
            assert game.completed_date >= now
            assert game.game_state == GameState.CANCELLED
            assert game.cancelled_reason == CancelledReason.NOT_VIABLE
            assert game.completed_comment == "comment"
            assert game.game_players == {"gp1": gp1_copy, "gp2": gp2_copy}
            game._engine.stop_game.assert_called_once()

    def test_mark_quit_illegal_state(self):
        for game_state in [game_state for game_state in GameState if game_state not in (GameState.PLAYING, GameState.ADVERTISED)]:
            gp1 = GamePlayer("gp1", PlayerColor.YELLOW, PlayerType.PROGRAMMATIC, PlayerState.PLAYING)
            game = create_test_game()
            game.game_players = {"gp1": gp1}
            game.game_state = game_state
            with pytest.raises(ProcessingError, match=r"Illegal state for operation"):
                game.mark_quit("gp1")
            assert game.game_state == game_state  # should not change
            assert "gp1" in game.game_players  # should not change

    def test_mark_quit_advertised(self):
        gp1 = GamePlayer("gp1", PlayerColor.YELLOW, PlayerType.PROGRAMMATIC, PlayerState.PLAYING)
        game = create_test_game()
        game.game_players = {"gp1": gp1}
        game.game_state = GameState.ADVERTISED
        game.mark_quit("gp1")
        assert "gp1" not in game.game_players

    def test_mark_quit_started(self):
        gp1 = GamePlayer("gp1", PlayerColor.YELLOW, PlayerType.PROGRAMMATIC, PlayerState.PLAYING)
        gp1_copy = GamePlayer("gp1", PlayerColor.YELLOW, PlayerType.PROGRAMMATIC, PlayerState.QUIT)
        game = create_test_game()
        game.game_players = {"gp1": gp1}
        game.game_state = GameState.PLAYING
        game.mark_quit("gp1")
        assert game.game_players["gp1"] == gp1_copy

    def test_execute_move(self):
        game = create_test_game()
        game.execute_move("handle", "move_id")
        game._engine.execute_move.assert_called_once_with("handle", "move_id")

    def test_mark_joined_programmatic(self):
        game = create_test_game()
        game.game_players = {}
        game._mark_joined_programmatic()
        assert len(game.game_players) == 1
        gp1 = list(game.game_players.values())[0]
        assert gp1.handle in _NAMES
        assert gp1.player_color is None  # will be assigned later
        assert gp1.player_type == PlayerType.PROGRAMMATIC
        assert gp1.player_state == PlayerState.JOINED

    def test_assign_handle(self):
        game = create_test_game()

        game.game_players = {}
        handle = game._assign_handle()
        assert handle in _NAMES

        game.game_players = {"gp1": MagicMock(handle="Frodo"), "gp2": MagicMock(handle="Gimli")}
        for _ in range(0, 100):
            handle = game._assign_handle()
            assert handle in _NAMES and handle not in ("Frodo", "Gimli")


class TestStateManager:
    """
    Test the StateManager class.
    """

    def test_mark_active_no_websocket(self):
        player = MagicMock(websocket=None)
        mgr = StateManager()
        mgr.mark_active(player)
        player.mark_active.assert_called_once()

    def test_mark_active_unknown_websocket(self):
        websocket = MagicMock()
        player = MagicMock(websocket=websocket)
        mgr = StateManager()
        with pytest.raises(ProcessingError, match=r"Did not find player websocket"):
            mgr.mark_active(player)
        player.mark_active.assert_not_called()

    def test_mark_active(self):
        websocket = MagicMock()
        player = MagicMock(websocket=websocket)
        mgr = StateManager()
        mgr._websocket_map[websocket] = MagicMock()
        mgr.mark_active(player)
        player.mark_active.assert_called_once()
        mgr._websocket_map[websocket].mark_active.assert_called_once()

    def test_track_websocket_duplicate(self):
        original = MagicMock()
        websocket = MagicMock()
        mgr = StateManager()
        mgr._websocket_map[websocket] = original
        with pytest.raises(ProcessingError, match=r"Duplicate websocket encountered"):
            mgr.track_websocket(websocket)
        assert mgr._websocket_map[websocket] is original

    @patch("apologiesserver.manager.pendulum.now")
    def test_track_websocket(self, now):
        now.return_value = to_date("2020-05-11T16:57:00,000")
        websocket = MagicMock()
        mgr = StateManager()
        mgr.track_websocket(websocket)
        assert mgr._websocket_map[websocket] == TrackedWebsocket(websocket)

    def test_delete_websocket_unknown(self):
        websocket = MagicMock()
        mgr = StateManager()
        mgr.delete_websocket(websocket)  # no-op because it's unknown

    def test_delete_websocket(self):
        websocket = MagicMock()
        mgr = StateManager()
        mgr._websocket_map[websocket] = MagicMock()
        mgr.delete_websocket(websocket)
        assert websocket not in mgr._websocket_map

    def test_get_websocket_count(self):
        mgr = StateManager()
        mgr.track_websocket(MagicMock())
        mgr.track_websocket(MagicMock())
        mgr.track_websocket(MagicMock())
        assert mgr.get_websocket_count() == 3

    def test_lookup_all_websockets(self):
        websocket1 = MagicMock()
        websocket2 = MagicMock()
        websocket3 = MagicMock()
        mgr = StateManager()
        mgr.track_websocket(websocket1)
        mgr.track_websocket(websocket2)
        mgr.track_websocket(websocket3)
        assert mgr.lookup_all_websockets() == [websocket1, websocket2, websocket3]

    def test_lookup_players_for_websocket(self):
        player = MagicMock(player_id="player_id")
        websocket = MagicMock()
        mgr = StateManager()
        mgr.lookup_player = MagicMock()
        mgr.lookup_player.side_effect = [player, None]
        mgr.track_websocket(websocket)
        assert mgr.lookup_players_for_websocket(websocket) == []
        mgr._websocket_map[websocket].player_ids.add("player_id")
        mgr._websocket_map[websocket].player_ids.add("bogus")
        assert mgr.lookup_players_for_websocket(websocket) == [player]

    @patch("apologiesserver.manager.pendulum.now")
    @patch("apologiesserver.manager.uuid4")
    def test_track_game(self, uuid4, now):
        uuid4.return_value = "game_id"
        now.return_value = to_date("2020-05-11T16:57:00,000")
        player = MagicMock(handle="leela")
        advertised = AdvertiseGameContext("name", GameMode.STANDARD, 3, Visibility.PUBLIC, ["a", "b"])
        mgr = StateManager()
        game = mgr.track_game(player, advertised)
        assert game == TrackedGame.for_context("leela", "game_id", advertised)
        assert mgr._game_map["game_id"] is game

    def test_delete_game(self):
        game = MagicMock()
        mgr = StateManager()
        mgr._game_map["game"] = game
        mgr.delete_game(MagicMock(game_id="bogus"))  # safe to delete unknown game
        mgr.delete_game(MagicMock(game_id="game"))
        assert "game" not in mgr._game_map

    def test_get_total_game_count(self):
        game1 = MagicMock()
        mgr = StateManager()
        assert mgr.get_total_game_count() == 0
        mgr._game_map["game1"] = game1
        assert mgr.get_total_game_count() == 1

    def test_get_in_progress_game_count(self):
        game1 = MagicMock()
        game1.is_in_progress.return_value = True
        game2 = MagicMock()
        game2.is_in_progress.return_value = False
        game3 = MagicMock()
        game3.is_in_progress.return_value = True
        mgr = StateManager()
        assert mgr.get_in_progress_game_count() == 0
        mgr._game_map["game1"] = game1
        mgr._game_map["game2"] = game2
        mgr._game_map["game3"] = game3
        assert mgr.get_in_progress_game_count() == 2  # game1 and game3

    def test_lookup_game_game_id(self):
        game = MagicMock()
        mgr = StateManager()
        mgr._game_map["game"] = game
        assert mgr.lookup_game(game_id=None) is None
        assert mgr.lookup_game(game_id="bogus") is None
        assert mgr.lookup_game(game_id="game") is game

    def test_lookup_game_player(self):
        game = MagicMock()
        mgr = StateManager()
        mgr._game_map["game"] = game
        assert mgr.lookup_game(player=MagicMock(game_id=None)) is None
        assert mgr.lookup_game(player=MagicMock(game_id="bogus")) is None
        assert mgr.lookup_game(player=MagicMock(game_id="game")) is game

    def test_lookup_all_games(self):
        game1 = MagicMock()
        game2 = MagicMock()
        game3 = MagicMock()
        mgr = StateManager()
        mgr._game_map["game1"] = game1
        mgr._game_map["game2"] = game2
        mgr._game_map["game3"] = game3
        assert mgr.lookup_all_games() == [game1, game2, game3]

    def test_lookup_in_progress_games(self):
        game1 = MagicMock()
        game1.is_in_progress.return_value = True
        game2 = MagicMock()
        game2.is_in_progress.return_value = False
        game3 = MagicMock()
        game3.is_in_progress.return_value = True
        mgr = StateManager()
        mgr._game_map["game1"] = game1
        mgr._game_map["game2"] = game2
        mgr._game_map["game3"] = game3
        assert mgr.lookup_in_progress_games() == [game1, game3]

    def test_lookup_game_players(self):
        player = MagicMock()
        gp1 = GamePlayer("gp1", PlayerColor.YELLOW, PlayerType.PROGRAMMATIC, PlayerState.PLAYING)
        gp2 = GamePlayer("gp2", PlayerColor.RED, PlayerType.HUMAN, PlayerState.PLAYING)
        game = create_test_game()
        game.game_players = {"gp1": gp1, "gp2": gp2}
        mgr = StateManager()
        mgr.lookup_player = MagicMock()
        mgr.lookup_player.return_value = player
        assert mgr.lookup_game_players(game) == [player]
        mgr.lookup_player.assert_called_once_with(handle="gp2")

    def test_lookup_available_games(self):
        player = MagicMock(handle="handle")
        game1 = MagicMock()
        game1.is_available.return_value = True
        game2 = MagicMock()
        game2.is_available.return_value = False
        game3 = MagicMock()
        game3.is_available.return_value = True
        mgr = StateManager()
        mgr._game_map["game1"] = game1
        mgr._game_map["game2"] = game2
        mgr._game_map["game3"] = game3
        assert mgr.lookup_available_games(player) == [game1, game3]
        game1.is_available.assert_called_once_with("handle")
        game2.is_available.assert_called_once_with("handle")
        game3.is_available.assert_called_once_with("handle")

    @patch("apologiesserver.manager.pendulum.now")
    @patch("apologiesserver.manager.uuid4")
    def test_track_player(self, uuid4, now):
        uuid4.return_value = "player_id"
        now.return_value = to_date("2020-05-11T16:57:00,000")
        websocket = MagicMock()
        mgr = StateManager()
        mgr.track_websocket(websocket)  # this would always be done ahead of time, so do it here
        mgr._websocket_map[websocket].last_active_date = None  # so we can tell it was reset
        player = mgr.track_player(websocket, "handle")
        assert player == TrackedPlayer.for_context("player_id", websocket, "handle")
        assert mgr._websocket_map[websocket].last_active_date == to_date("2020-05-11T16:57:00,000")  # we always mark the websocket
        assert "player_id" in mgr._websocket_map[websocket].player_ids
        assert mgr._player_map["player_id"] is player
        assert mgr._handle_map["handle"] == "player_id"
        with pytest.raises(ProcessingError, match=r"Handle is already in use"):
            mgr.track_player(websocket, "handle")
        assert mgr._player_map["player_id"] is player
        assert mgr._handle_map["handle"] == "player_id"

    @patch("apologiesserver.manager.pendulum.now")
    def test_retrack_player(self, now):
        now.return_value = to_date("2020-05-11T16:57:00,000")
        player = MagicMock(player_id="player_id")
        websocket = MagicMock()
        mgr = StateManager()
        mgr.track_websocket(websocket)  # this would always be done ahead of time, so do it here
        mgr._websocket_map[websocket].last_active_date = None  # so we can tell it was reset
        mgr.retrack_player(player, websocket)
        assert player.websocket == websocket
        assert mgr._websocket_map[websocket].last_active_date == to_date("2020-05-11T16:57:00,000")  # we always mark the websocket
        assert "player_id" in mgr._websocket_map[websocket].player_ids

    def test_delete_player_no_websocket(self):
        mgr = StateManager()
        mgr._player_map["player_id"] = MagicMock()
        mgr._handle_map["handle"] = MagicMock()
        mgr.delete_player(MagicMock(player_id="bogus", handle="bogus", websocket=MagicMock()))  # safe to delete unknown stuff
        mgr.delete_player(MagicMock(player_id="player_id", handle="handle", websocket=None))
        assert "player_id" not in mgr._player_map
        assert "handle" not in mgr._handle_map

    def test_delete_player_unknown_websocket(self):
        websocket = MagicMock()
        mgr = StateManager()
        # note: not tracking the websocket, so it will not exist when we try to look it up
        mgr._player_map["player_id"] = MagicMock()
        mgr._handle_map["handle"] = MagicMock()
        mgr.delete_player(MagicMock(player_id="bogus", handle="bogus", websocket=MagicMock()))  # safe to delete unknown stuff
        mgr.delete_player(MagicMock(player_id="player_id", handle="handle", websocket=websocket))
        assert "player_id" not in mgr._player_map
        assert "handle" not in mgr._handle_map

    def test_delete_player(self):
        websocket = MagicMock()
        mgr = StateManager()
        mgr.track_websocket(websocket)  # this would always be done ahead of time, so do it here
        mgr._websocket_map[websocket].player_ids.add("player_id")
        mgr._player_map["player_id"] = MagicMock()
        mgr._handle_map["handle"] = MagicMock()
        mgr.delete_player(MagicMock(player_id="bogus", handle="bogus", websocket=MagicMock()))  # safe to delete unknown stuff
        mgr.delete_player(MagicMock(player_id="player_id", handle="handle", websocket=websocket))
        assert "player_id" not in list(mgr._websocket_map[websocket].player_ids)
        assert "player_id" not in mgr._player_map
        assert "handle" not in mgr._handle_map

    def test_get_registered_player_count(self):
        player = MagicMock()
        mgr = StateManager()
        assert mgr.get_registered_player_count() == 0
        mgr._player_map["player"] = player
        assert mgr.get_registered_player_count() == 1

    def test_lookup_player_player_id(self):
        player = MagicMock()
        mgr = StateManager()
        mgr._player_map["player"] = player
        assert mgr.lookup_player(player_id=None) is None
        assert mgr.lookup_player(player_id="bogus") is None
        assert mgr.lookup_player(player_id="player") is player

    def test_lookup_player_handle(self):
        player = MagicMock(player_id="player")
        mgr = StateManager()
        mgr._player_map["player"] = player
        mgr._handle_map["handle"] = "player"
        assert mgr.lookup_player(handle=None) is None
        assert mgr.lookup_player(handle="bogus") is None
        assert mgr.lookup_player(handle="handle") is player

    def test_lookup_all_players(self):
        player = MagicMock()
        mgr = StateManager()
        mgr._player_map["player"] = player
        assert mgr.lookup_all_players() == [player]

    def test_lookup_websocket_activity(self):
        date = to_date("2020-05-12T16:26:00,000")
        websocket = MagicMock()
        tracked = MagicMock(websocket=websocket, last_active_date=date, player_ids=OrderedSet(["1", "2", "3"]))
        mgr = StateManager()
        mgr._websocket_map[websocket] = tracked
        assert mgr.lookup_websocket_activity() == [(tracked, date, 3)]

    def test_lookup_player_activity(self):
        date = to_date("2020-05-12T16:26:00,000")
        tracked = MagicMock(player_id="player_id", last_active_date=date, connection_state=ConnectionState.CONNECTED)
        mgr = StateManager()
        mgr._player_map["player_id"] = tracked
        assert mgr.lookup_player_activity() == [(tracked, date, ConnectionState.CONNECTED)]

    def test_lookup_game_activity(self):
        date = to_date("2020-05-12T16:26:00,000")
        tracked1 = MagicMock(game_id="1", last_active_date=date, completed=False)
        tracked2 = MagicMock(game_id="2", last_active_date=None, completed=True)
        mgr = StateManager()
        mgr._game_map["1"] = tracked1
        mgr._game_map["2"] = tracked2
        assert mgr.lookup_game_activity() == [(tracked1, date)]

    def test_lookup_game_completion(self):
        date = to_date("2020-05-12T16:26:00,000")
        tracked1 = MagicMock(game_id="1", completed_date=None, completed=False)
        tracked2 = MagicMock(game_id="2", completed_date=date, completed=True)
        mgr = StateManager()
        mgr._game_map["1"] = tracked1
        mgr._game_map["2"] = tracked2
        assert mgr.lookup_game_completion() == [(tracked2, date)]


class TestGame:
    """
    Test a complete game via the StateManager interface.

    This basically covers the steps that would happen in a real game via the
    public interface, except directly against the manager interface instead.
    Unlike the public interface, the manager interface is synchronous, which
    makes everything a lot easier to deal with if debugging is required.
    """

    def test_complete_game_standard(self):
        TestGame.play_game(mode=GameMode.STANDARD, player_count=4, handles=["leela"])

    def test_complete_game_adult(self):
        TestGame.play_game(mode=GameMode.ADULT, player_count=3, handles=["leela"])

    # pylint: disable=too-many-locals

    @staticmethod
    def play_game(mode: GameMode, player_count: int, handles: List[str]) -> None:
        assert len(handles) >= 1

        print("Testing complete game with mode %s and 'human' players %s" % (mode, handles))

        websocket = MagicMock()

        name = "Demo Game"
        visibility = Visibility.PUBLIC
        invited_handles: List[str] = []
        advertised = AdvertiseGameContext(name, mode, player_count, visibility, invited_handles)

        mgr = StateManager()
        print("Created state manager.")

        mgr.track_websocket(websocket)
        print("Tracked simulated websocket")

        players: Dict[str, TrackedPlayer] = {}
        for handle in handles:
            player = mgr.track_player(websocket, handle)
            players[handle] = player
            print("Created player %s with id %s" % (player.handle, player.player_id))

        game = mgr.track_game(players[handles[0]], advertised)
        print("Advertised game '%s' with id %s" % (game.name, game.game_id))

        for handle in handles:
            game.mark_joined(handle)
        game.mark_started()
        for player in players.values():
            player.mark_playing()
        print("Started game")
        print(
            "Players: %s"
            % ["%s (%s)" % (player.handle, player.player_color.value) for player in game.get_game_players()]  # type: ignore
        )

        completed = False
        while not completed:
            handle, player_type = game.get_next_turn()
            if player_type == PlayerType.PROGRAMMATIC:
                view = game.get_player_view(handle)
                moves = game.get_legal_moves(handle)
                move = RewardV1InputSource().choose_move(game.mode, view, moves, Rules.evaluate_move)
                (completed, _winner, comment) = game.execute_move(handle, move.id)
            else:
                moves = game.get_legal_moves(handle)
                context = GamePlayerTurnContext.for_moves(handle=handle, game_id=game.game_id, moves=moves)
                move_id = random.choice(list(context.moves.keys()))  # simulates input from the websocket client
                (completed, _winner, comment) = game.execute_move(handle, move_id)
            history = game.get_recent_history(1)
            if history:
                color = "General" if not history[0].color else history[0].color.value
                action = history[0].action
                print("%s - %s" % (color, action))
            if completed:
                for player in players.values():
                    player.mark_quit()
                game.mark_completed(comment)
                print("%s" % comment)

        for player in players.values():
            mgr.delete_player(player)
        mgr.delete_game(game)
        mgr.delete_websocket(websocket)

        print("Test completed")
