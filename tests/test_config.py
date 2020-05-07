# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=invalid-name,global-statement

import os

import pytest

from apologiesserver.config import _CONFIG, DEFAULT_CONFIG_PATH, SystemConfig, config, load_config

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures/test_config")


def assert_defaults(c: SystemConfig) -> None:
    """Check that a SystemConfig object has defaults filled in."""
    assert c.logfile_path is None
    assert c.server_host == "localhost"
    assert c.server_port == 8080
    assert c.total_game_limit == 1000
    assert c.in_progress_game_limit == 25
    assert c.registered_player_limit == 100
    assert c.player_idle_thresh_min == 15
    assert c.player_inactive_thresh_min == 30
    assert c.game_idle_thresh_min == 10
    assert c.game_inactive_thresh_min == 20
    assert c.game_retention_thresh_min == 2880
    assert c.idle_player_check_period_sec == 120
    assert c.idle_player_check_delay_sec == 300
    assert c.idle_game_check_period_sec == 120
    assert c.idle_game_check_delay_sec == 300
    assert c.obsolete_game_check_period_sec == 300
    assert c.obsolete_game_check_delay_sec == 300


class TestSystemConfig:
    """
    Unit tests for the SystemConfig class.
    """

    def test_defaults(self):
        c = SystemConfig()
        assert_defaults(c)

    def test_to_json(self):
        c = SystemConfig()
        assert c.to_json() is not None


class TestFunctions:
    """
    Unit tests for the config-related functions.
    """

    def test_default_config_path(self):
        assert DEFAULT_CONFIG_PATH == os.path.join(os.path.expanduser("~"), ".apologiesrc")  # different way to get same value

    def test_config_not_loaded(self):
        global _CONFIG
        saved = _CONFIG
        try:
            _CONFIG = None
            config()
        except ValueError:
            pass
        finally:
            _CONFIG = saved

    def test_load_config_defaults(self):
        if not os.path.exists(DEFAULT_CONFIG_PATH):
            # only bother to test this if the file does not exist; we can't trust what's in there
            load_config()
            assert_defaults(config())

    def test_load_config_path_missing(self):
        config_path = os.path.join(FIXTURE_DIR, "missing.rc")
        assert not os.path.exists(config_path)  # if it exists, the test isn't valid
        with pytest.raises(ValueError):
            load_config(config_path=config_path)

    def test_load_config_path_exists_partial(self):
        config_path = os.path.join(FIXTURE_DIR, "partial.rc")
        load_config(config_path=config_path)
        c = config()
        assert c.logfile_path == "/var/logs/apologies.log"
        assert c.server_host == "example.com"
        assert c.server_port == 8080
        assert c.total_game_limit == 1000
        assert c.in_progress_game_limit == 25
        assert c.registered_player_limit == 100
        assert c.player_idle_thresh_min == 15
        assert c.player_inactive_thresh_min == 30
        assert c.game_idle_thresh_min == 600  # taken from partial.rc
        assert c.game_inactive_thresh_min == 700  # taken from partial.rc
        assert c.game_retention_thresh_min == 2880
        assert c.idle_player_check_period_sec == 120
        assert c.idle_player_check_delay_sec == 300
        assert c.idle_game_check_period_sec == 120
        assert c.idle_game_check_delay_sec == 300
        assert c.obsolete_game_check_period_sec == 300
        assert c.obsolete_game_check_delay_sec == 1400  # taken from partial.rc

    def test_load_config_path_exists_complete(self):
        config_path = os.path.join(FIXTURE_DIR, "complete.rc")
        load_config(config_path=config_path)
        c = config()
        assert c.logfile_path == "/var/logs/apologies.log"
        assert c.server_host == "example.com"
        assert c.server_port == 10
        assert c.total_game_limit == 20
        assert c.in_progress_game_limit == 30
        assert c.registered_player_limit == 40
        assert c.player_idle_thresh_min == 50
        assert c.player_inactive_thresh_min == 60
        assert c.game_idle_thresh_min == 70
        assert c.game_inactive_thresh_min == 80
        assert c.game_retention_thresh_min == 90
        assert c.idle_player_check_period_sec == 100
        assert c.idle_player_check_delay_sec == 110
        assert c.idle_game_check_period_sec == 120
        assert c.idle_game_check_delay_sec == 130
        assert c.obsolete_game_check_period_sec == 140
        assert c.obsolete_game_check_delay_sec == 150

    def test_load_config_overrides_partial(self):
        config_path = os.path.join(FIXTURE_DIR, "partial.rc")
        overrides = {
            "logfile_path": "~/logs/apologies.log",
            "server_host": "whatever.com",
            "game_idle_thresh_min": 900,
            "obsolete_game_check_period_sec": 1500,
        }
        load_config(config_path=config_path, overrides=overrides)
        c = config()
        assert c.logfile_path == "~/logs/apologies.log"  # taken from overrides
        assert c.server_host == "whatever.com"  # taken from overrides
        assert c.server_port == 8080
        assert c.total_game_limit == 1000
        assert c.in_progress_game_limit == 25
        assert c.registered_player_limit == 100
        assert c.player_idle_thresh_min == 15
        assert c.player_inactive_thresh_min == 30
        assert c.game_idle_thresh_min == 900  # taken from overrides
        assert c.game_inactive_thresh_min == 700  # taken from partial.rc
        assert c.game_retention_thresh_min == 2880
        assert c.idle_player_check_period_sec == 120
        assert c.idle_player_check_delay_sec == 300
        assert c.idle_game_check_period_sec == 120
        assert c.idle_game_check_delay_sec == 300
        assert c.obsolete_game_check_period_sec == 1500  # taken from overrides
        assert c.obsolete_game_check_delay_sec == 1400  # taken from partial.rc

    def test_load_config_overrides_all(self):
        config_path = os.path.join(FIXTURE_DIR, "complete.rc")
        overrides = {
            "logfile_path": "~/logs/apologies.log",
            "server_host": "whatever.com",
            "server_port": 100,
            "total_game_limit": 200,
            "in_progress_game_limit": 300,
            "registered_player_limit": 400,
            "player_idle_thresh_min": 500,
            "player_inactive_thresh_min": 600,
            "game_idle_thresh_min": 700,
            "game_inactive_thresh_min": 800,
            "game_retention_thresh_min": 900,
            "idle_player_check_period_sec": 1000,
            "idle_player_check_delay_sec": 1100,
            "idle_game_check_period_sec": 1200,
            "idle_game_check_delay_sec": 1300,
            "obsolete_game_check_period_sec": 1400,
            "obsolete_game_check_delay_sec": 1500,
        }
        load_config(config_path=config_path, overrides=overrides)
        c = config()
        assert c.logfile_path == "~/logs/apologies.log"
        assert c.server_host == "whatever.com"
        assert c.server_port == 100
        assert c.total_game_limit == 200
        assert c.in_progress_game_limit == 300
        assert c.registered_player_limit == 400
        assert c.player_idle_thresh_min == 500
        assert c.player_inactive_thresh_min == 600
        assert c.game_idle_thresh_min == 700
        assert c.game_inactive_thresh_min == 800
        assert c.game_retention_thresh_min == 900
        assert c.idle_player_check_period_sec == 1000
        assert c.idle_player_check_delay_sec == 1100
        assert c.idle_game_check_period_sec == 1200
        assert c.idle_game_check_delay_sec == 1300
        assert c.obsolete_game_check_period_sec == 1400
        assert c.obsolete_game_check_delay_sec == 1500
