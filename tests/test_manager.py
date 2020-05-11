# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=redefined-outer-name,wildcard-import

from unittest.mock import MagicMock

import pendulum

from apologiesserver.interface import *
from apologiesserver.manager import _MANAGER, TrackedPlayer, manager


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
        websocket = MagicMock()
        player = TrackedPlayer.for_context("id", websocket, "handle")
        assert player.player_id == "id"
        assert player.handle == "handle"
        assert player.websocket is websocket
        assert player.registration_date is not None
        assert player.last_active_date is not None
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
        player = TrackedPlayer(player_id="id", websocket=MagicMock(), handle="handle")
        player.last_active_date = None
        player.activity_state = None
        player.connection_state = None
        player.mark_active()
        assert player.last_active_date >= now
        assert player.activity_state == ActivityState.ACTIVE
        assert player.connection_state == ConnectionState.CONNECTED

    def test_mark_idle(self):
        player = TrackedPlayer(player_id="id", websocket=MagicMock(), handle="handle")
        player.activity_state = None
        player.mark_idle()
        assert player.activity_state == ActivityState.IDLE

    def test_mark_inactive(self):
        player = TrackedPlayer(player_id="id", websocket=MagicMock(), handle="handle")
        player.activity_state = None
        player.mark_inactive()
        assert player.activity_state == ActivityState.INACTIVE

    def test_mark_joined(self):
        game = MagicMock(game_id="game_id")
        player = TrackedPlayer(player_id="id", websocket=MagicMock(), handle="handle")
        player.game_id = None
        player.player_state = None
        player.mark_joined(game)
        assert player.game_id == "game_id"
        assert player.player_state == PlayerState.JOINED

    def test_mark_playing(self):
        player = TrackedPlayer(player_id="id", websocket=MagicMock(), handle="handle")
        player.player_state = None
        player.mark_playing()
        assert player.player_state == PlayerState.PLAYING

    def test_mark_quit(self):
        player = TrackedPlayer(player_id="id", websocket=MagicMock(), handle="handle")
        player.game_id = "game_id"
        player.player_state = None
        player.mark_quit()
        assert player.game_id is None
        assert player.player_state == PlayerState.WAITING  # they move through QUIT and back to WAITING

    def test_mark_disconnected(self):
        player = TrackedPlayer(player_id="id", websocket=MagicMock(), handle="handle")
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
        pass

    def test_to_advertised_game(self):
        pass

    def test_get_game_players(self):
        pass

    def test_is_available(self):
        pass

    def test_is_in_progress(self):
        pass

    def test_is_advertised(self):
        pass

    def test_is_playing(self):
        pass

    def test_is_viable(self):
        pass

    def test_is_fully_joined(self):
        pass

    def test_is_move_pending(self):
        pass

    def test_is_legal_move(self):
        pass

    def test_get_next_turn(self):
        pass

    def test_mark_active(self):
        pass

    def test_mark_idle(self):
        pass

    def test_mark_inactive(self):
        pass

    def test_mark_started(self):
        pass

    def test_mark_completed(self):
        pass

    def test_mark_cancelled(self):
        pass

    def test_mark_joined(self):
        pass

    def test_mark_quit(self):
        pass

    def test_get_player_view(self):
        pass

    def test_execute_move(self):
        pass

    def test_mark_joined_programmatic(self):
        pass

    def test_assign_color(self):
        pass

    def test_assign_handle(self):
        pass


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
