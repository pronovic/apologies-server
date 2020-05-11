# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=redefined-outer-name,wildcard-import

from unittest.mock import MagicMock

import pendulum
import pytest
from apologies.game import GameMode, PlayerColor

from apologiesserver.interface import *
from apologiesserver.manager import _MANAGER, _NAMES, TrackedGame, TrackedPlayer, manager

from .util import random_string


def create_test_player(player_id="id", handle="handle"):
    return TrackedPlayer(player_id=player_id, websocket=MagicMock(), handle=handle)


def create_test_game():
    return TrackedGame("game_id", "handle", "name", GameMode.STANDARD, 3, Visibility.PRIVATE, [])


def check_fully_joined(players: int, game_players: int) -> bool:
    game = TrackedGame("game_id", "handle", "name", GameMode.STANDARD, 3, Visibility.PRIVATE, [])
    game.players = players
    game.game_players = {random_string(): MagicMock() for _ in range(game_players)}
    return game.is_fully_joined()


def check_is_in_progress(advertised: bool, playing: bool) -> bool:
    game = TrackedGame("game_id", "handle", "name", GameMode.STANDARD, 3, Visibility.PRIVATE, ["bender", "fry"])
    game.is_advertised = MagicMock()  # type: ignore
    game.is_playing = MagicMock()  # type: ignore
    game.is_advertised.return_value = advertised  # type: ignore
    game.is_playing.return_value = playing  # type: ignore
    return game.is_in_progress()


def check_is_viable(advertised: bool, available: int) -> bool:
    game = TrackedGame("game_id", "handle", "name", GameMode.STANDARD, 3, Visibility.PRIVATE, [])
    game.is_advertised = MagicMock()  # type: ignore
    game.get_available_player_count = MagicMock()  # type: ignore
    game.is_advertised.return_value = advertised  # type: ignore
    game.get_available_player_count.return_value = available  # type: ignore
    return game.is_viable()


class TestFunctions:
    """
    Test Python functions.
    """

    def test_manager(self):
        assert _MANAGER is not None
        assert manager() is _MANAGER


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

    def test_is_available_public(self):
        leela = MagicMock(handle="leela")
        bender = MagicMock(handle="bender")
        fry = MagicMock(handle="fry")
        game = TrackedGame("game_id", "handle", "name", GameMode.STANDARD, 3, Visibility.PUBLIC, ["bender", "fry"])

        # If a public game is advertised, then it is available anyone (regardless of whether they are invited)
        game.game_state = GameState.ADVERTISED
        assert game.is_available(leela) is True
        assert game.is_available(bender) is True
        assert game.is_available(fry) is True

        # If any game is not advertised, then it is not available to anyone
        for state in [state for state in GameState if state != GameState.ADVERTISED]:
            game.game_state = state
            assert game.is_available(leela) is False
            assert game.is_available(bender) is False
            assert game.is_available(fry) is False

    def test_is_available_private(self):
        leela = MagicMock(handle="leela")
        bender = MagicMock(handle="bender")
        fry = MagicMock(handle="fry")
        game = TrackedGame("game_id", "handle", "name", GameMode.STANDARD, 3, Visibility.PRIVATE, ["bender", "fry"])

        # If a private game is advertised, then it is available only for an invited handle
        game.game_state = GameState.ADVERTISED
        assert game.is_available(leela) is False
        assert game.is_available(bender) is True
        assert game.is_available(fry) is True

        # If any game is not advertised, then it is not available to anyone
        for state in [state for state in GameState if state != GameState.ADVERTISED]:
            game.game_state = state
            assert game.is_available(leela) is False
            assert game.is_available(bender) is False
            assert game.is_available(fry) is False

    def test_is_in_progress(self):
        assert check_is_in_progress(True, True) is True
        assert check_is_in_progress(True, False) is True
        assert check_is_in_progress(False, True) is True
        assert check_is_in_progress(False, False) is False

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
        with pytest.raises(NotImplementedError):
            assert game.is_move_pending("handle")

    def test_is_legal_move(self):
        game = create_test_game()
        with pytest.raises(NotImplementedError):
            assert game.is_legal_move("handle", "move_id")

    def test_get_next_turn(self):
        game = create_test_game()
        with pytest.raises(NotImplementedError):
            assert game.get_next_turn()

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

    def test_mark_joined(self):
        player1 = create_test_player(player_id="1", handle="leela")
        game = create_test_game()
        game.mark_joined(player1)
        assert len(game.game_players) == 1
        assert game.game_players["leela"].handle == "leela"
        assert game.game_players["leela"].player_color is not None
        assert game.game_players["leela"].player_type == PlayerType.HUMAN
        assert game.game_players["leela"].player_state == PlayerState.JOINED

    # noinspection PyTypeChecker
    def test_mark_started(self):
        player1 = create_test_player(player_id="1", handle="leela")
        player2 = create_test_player(player_id="2", handle="bender")

        now = pendulum.now()
        game = create_test_game()
        game.players = 4
        game.mark_joined(player1)
        game.mark_joined(player2)

        game.game_state = None
        game.last_active_date = None
        game.started_date = None
        game.mark_started()
        assert game.game_state == GameState.PLAYING
        assert game.last_active_date >= now
        assert game.started_date >= now
        assert len(game.game_players) == 4  # the two we added and two programmatic ones

        # make sure each color got assigned once
        colors = [player.player_color for player in game.game_players.values()]
        assert len(colors) == 4
        assert PlayerColor.RED in colors
        assert PlayerColor.YELLOW in colors
        assert PlayerColor.GREEN in colors
        assert PlayerColor.BLUE in colors

        # make sure we got 2 programatic players with unique names in the right state
        programmatic = [player.handle for player in game.game_players.values() if player.handle not in ("leela", "bender")]
        assert len(programmatic) == 2
        for handle in programmatic:
            assert handle in _NAMES
            assert game.game_players[handle].player_color is not None
            assert game.game_players[handle].handle == handle
            assert game.game_players[handle].player_type == PlayerType.PROGRAMMATIC
            assert game.game_players[handle].player_state == PlayerState.PLAYING

        # make sure we still have 2 human players in the right state
        human = [player.handle for player in game.game_players.values() if player.handle in ("leela", "bender")]
        assert len(human) == 2
        for handle in ["leela", "bender"]:
            assert game.game_players[handle].handle == handle
            assert game.game_players[handle].player_color is not None
            assert game.game_players[handle].player_type == PlayerType.HUMAN
            assert game.game_players[handle].player_state == PlayerState.PLAYING

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
        game.game_state = None
        game.completed_comment = None
        game.mark_completed("comment")
        assert game.completed_date >= now
        assert game.game_state == GameState.COMPLETED
        assert game.completed_comment == "comment"
        assert game.game_players == {"gp1": gp1_copy, "gp2": gp2_copy}

    # noinspection PyTypeChecker
    def test_mark_cancelled(self):
        gp1 = GamePlayer("gp1", PlayerColor.YELLOW, PlayerType.PROGRAMMATIC, PlayerState.PLAYING)
        gp2 = GamePlayer("gp2", PlayerColor.RED, PlayerType.HUMAN, PlayerState.PLAYING)
        gp1_copy = GamePlayer("gp1", PlayerColor.YELLOW, PlayerType.PROGRAMMATIC, PlayerState.FINISHED)
        gp2_copy = GamePlayer("gp2", PlayerColor.RED, PlayerType.HUMAN, PlayerState.FINISHED)
        now = pendulum.now()
        game = create_test_game()
        game.game_players = {"gp1": gp1, "gp2": gp2}
        game.completed_date = None
        game.game_state = None
        game.completed_comment = None
        game.mark_cancelled(CancelledReason.NOT_VIABLE, "comment")
        assert game.completed_date >= now
        assert game.game_state == GameState.CANCELLED
        assert game.cancelled_reason == CancelledReason.NOT_VIABLE
        assert game.completed_comment == "comment"
        assert game.game_players == {"gp1": gp1_copy, "gp2": gp2_copy}

    def test_mark_quit_advertised(self):
        player = MagicMock(handle="gp1")
        gp1 = GamePlayer("gp1", PlayerColor.YELLOW, PlayerType.PROGRAMMATIC, PlayerState.PLAYING)
        game = create_test_game()
        game.game_players = {"gp1": gp1}
        game.game_state = GameState.ADVERTISED
        game.mark_quit(player)
        assert "gp1" not in game.game_players

    def test_mark_quit_started(self):
        player = MagicMock(handle="gp1")
        gp1 = GamePlayer("gp1", PlayerColor.YELLOW, PlayerType.PROGRAMMATIC, PlayerState.PLAYING)
        gp1_copy = GamePlayer("gp1", PlayerColor.YELLOW, PlayerType.PROGRAMMATIC, PlayerState.QUIT)
        game = create_test_game()
        game.game_players = {"gp1": gp1}
        game.game_state = GameState.PLAYING
        game.mark_quit(player)
        assert game.game_players["gp1"] == gp1_copy

    def test_get_player_view(self):
        player = MagicMock()
        game = create_test_game()
        with pytest.raises(NotImplementedError):
            assert game.get_player_view(player)

    def test_execute_move(self):
        player = MagicMock()
        game = create_test_game()
        with pytest.raises(NotImplementedError):
            assert game.execute_move(player, "move_id")

    # pylint: disable=protected-access
    def test_mark_joined_programmatic(self):
        game = create_test_game()
        game.game_players = {}
        game._mark_joined_programmatic()
        assert len(game.game_players) == 1
        gp1 = list(game.game_players.values())[0]
        assert gp1.handle in _NAMES
        assert gp1.player_color in PlayerColor
        assert gp1.player_type == PlayerType.PROGRAMMATIC
        assert gp1.player_state == PlayerState.JOINED

    # pylint: disable=protected-access
    def test_assign_color(self):
        # Player colors are assigned in order that they are defined in PlayerColor
        # This test makes an assumption about that order; if it changes, then this test will fail

        game = create_test_game()

        game.players = 2
        game.game_players = {}
        assert game._assign_color() in (PlayerColor.RED, PlayerColor.YELLOW)

        game.players = 2
        game.game_players = {"gp1": MagicMock(player_color=PlayerColor.RED)}
        assert game._assign_color() == PlayerColor.YELLOW

        game.players = 3
        game.game_players = {}
        assert game._assign_color() in (PlayerColor.RED, PlayerColor.YELLOW, PlayerColor.GREEN)

        game.players = 3
        game.game_players = {"gp1": MagicMock(player_color=PlayerColor.YELLOW)}
        assert game._assign_color() in (PlayerColor.RED, PlayerColor.GREEN)

        game.players = 3
        game.game_players = {"gp1": MagicMock(player_color=PlayerColor.YELLOW), "gp2": MagicMock(player_color=PlayerColor.RED)}
        assert game._assign_color() == PlayerColor.GREEN

    # pylint: disable=protected-access
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

    def test_track_game(self):
        pass

    def test_total_game_count(self):
        pass

    def test_in_progress_game_count(self):
        pass

    def test_lookup_game(self):
        pass

    def test_delete_game(self):
        pass

    def test_lookup_all_games(self):
        pass

    def test_lookup_in_progress_games(self):
        pass

    def test_lookup_game_players(self):
        pass

    def test_lookup_available_games(self):
        pass

    def test_track_player(self):
        pass

    def test_registered_player_count(self):
        pass

    def test_lookup_player(self):
        pass

    def test_delete_player(self):
        pass

    def test_lookup_all_players(self):
        pass

    def test_lookup_websocket(self):
        pass

    def test_lookup_websockets(self):
        pass

    def test_lookup_all_websockets(self):
        pass

    def test_lookup_player_for_websocket(self):
        pass

    def test_lookup_player_activity(self):
        pass

    def test_lookup_game_activity(self):
        pass

    def test_lookup_game_completion(self):
        pass
