# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:

"""
System configuration.
"""

# TODO: should be ok to start unit testing this, I think the structure is final


import configparser
import os
from configparser import ConfigParser, SectionProxy
from typing import Any, Dict, Optional, Union

import attr
import cattr
import orjson

from .util import homedir

# Configuration defaults
DEFAULT_CONFIG_PATH = os.path.join(homedir(), ".apologiesrc")
DEFAULT_LOGFILE_PATH = None
DEFAULT_SERVER_HOST = "localhost"
DEFAULT_SERVER_PORT = 8080
DEFAULT_TOTAL_GAME_LIMIT = 1000
DEFAULT_IN_PROGRESS_GAME_LIMIT = 25
DEFAULT_REGISTERED_PLAYER_LIMIT = 100
DEFAULT_PLAYER_IDLE_THRESH_MIN = 15
DEFAULT_PLAYER_INACTIVE_THRESH_MIN = 30
DEFAULT_GAME_IDLE_THRESH_MIN = 10
DEFAULT_GAME_INACTIVE_THRESH_MIN = 20
DEFAULT_GAME_RETENSION_THRESH_MIN = 2880  # 2 days
IDLE_PLAYER_CHECK_PERIOD_SEC = 120
IDLE_PLAYER_CHECK_DELAY_SEC = 300
IDLE_GAME_CHECK_PERIOD_SEC = 120
IDLE_GAME_CHECK_DELAY_SEC = 300
OBSOLETE_GAME_CHECK_PERIOD_SEC = 300
OBSOLETE_GAME_CHECK_DELAY_SEC = 300


# pylint: disable=too-many-instance-attributes
@attr.s(frozen=True)
class SystemConfig:
    """
    System configuration.
    
    Attributes:
        logfile_path(str): The path to the log file on disk
        server_host(str): The hostname to bind to
        server_port(int): The server port to listen on
        total_game_limit(int): Limit on the total number of tracked games
        in_progress_game_limit(int): Limit on the number of in progress games
        registered_player_limit(int): Limit on the number of registered players
        player_idle_thresh_min(int): Number of minutes of no activity before a player is considered idle
        player_inactive_thresh_min(int): Number of minutes of no activity before a player is considered inactive
        game_idle_thresh_min(int): Number of minutes of no activity before a game is considered idle
        game_inactive_thresh_min(int): Number of minutes of no activity before a game is considered inactive
        game_retension_thresh_min(int): Number of minutes to retain data about games after they are completed
        idle_player_check_period_sec(int): Number of seconds to wait between executions of the Idle Player Check task
        idle_player_check_delay_sec(int): Number of seconds to delay before the first Idle Player Check task
        idle_game_check_period_sec(int): Number of seconds to wait between executions of the Idle Game Check task
        idle_game_check_delay_sec(int): Number of seconds to delay before the first Idle Player Check task
        obsolete_game_check_period_sec(int):  Number of seconds to wait between executions of the Obsolete Game Check task
        obsolete_game_check_delay_sec(int): Number of seconds to delay before the first Idle Player Check task
    """

    logfile_path = attr.ib(type=str, default=DEFAULT_LOGFILE_PATH)
    server_host = attr.ib(type=str, default=DEFAULT_SERVER_HOST)
    server_port = attr.ib(type=int, default=DEFAULT_SERVER_PORT)
    total_game_limit = attr.ib(type=int, default=DEFAULT_TOTAL_GAME_LIMIT)
    in_progress_game_limit = attr.ib(type=int, default=DEFAULT_IN_PROGRESS_GAME_LIMIT)
    registered_player_limit = attr.ib(type=int, default=DEFAULT_REGISTERED_PLAYER_LIMIT)
    player_idle_thresh_min = attr.ib(type=int, default=DEFAULT_PLAYER_IDLE_THRESH_MIN)
    player_inactive_thresh_min = attr.ib(type=int, default=DEFAULT_PLAYER_INACTIVE_THRESH_MIN)
    game_idle_thresh_min = attr.ib(type=int, default=DEFAULT_GAME_IDLE_THRESH_MIN)
    game_inactive_thresh_min = attr.ib(type=int, default=DEFAULT_GAME_INACTIVE_THRESH_MIN)
    game_retension_thresh_min = attr.ib(type=int, default=DEFAULT_GAME_RETENSION_THRESH_MIN)
    idle_player_check_period_sec = attr.ib(type=int, default=IDLE_PLAYER_CHECK_PERIOD_SEC)
    idle_player_check_delay_sec = attr.ib(type=int, default=IDLE_PLAYER_CHECK_DELAY_SEC)
    idle_game_check_period_sec = attr.ib(type=int, default=IDLE_GAME_CHECK_PERIOD_SEC)
    idle_game_check_delay_sec = attr.ib(type=int, default=IDLE_GAME_CHECK_DELAY_SEC)
    obsolete_game_check_period_sec = attr.ib(type=int, default=OBSOLETE_GAME_CHECK_PERIOD_SEC)
    obsolete_game_check_delay_sec = attr.ib(type=int, default=OBSOLETE_GAME_CHECK_DELAY_SEC)

    def to_json(self) -> str:
        """Serialize to JSON."""
        return orjson.dumps(cattr.unstructure(self), option=orjson.OPT_INDENT_2).decode("utf-8")  # type: ignore


_CONFIG: Optional[SystemConfig] = None


def _default(overrides: Optional[Dict[str, Any]], key: Any, default: Any) -> Any:
    """Apply default when looking up an override."""
    return default if not overrides else overrides[key] if key in overrides else default


def _defaults(overrides: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Create a complete defaults map based on a set of overrides (which may be partially filled in)."""
    return {
        "logfile_path": _default(overrides, "logfile_path", DEFAULT_LOGFILE_PATH),
        "server_host": _default(overrides, "server_host", DEFAULT_SERVER_HOST),
        "server_port": _default(overrides, "server_port", DEFAULT_SERVER_PORT),
        "total_game_limit": _default(overrides, "total_game_limit", DEFAULT_TOTAL_GAME_LIMIT),
        "in_progress_game_limit": _default(overrides, "in_progress_game_limit", DEFAULT_IN_PROGRESS_GAME_LIMIT),
        "registered_player_limit": _default(overrides, "registered_player_limit", DEFAULT_REGISTERED_PLAYER_LIMIT),
        "player_idle_thresh_min": _default(overrides, "player_idle_thresh_min", DEFAULT_PLAYER_IDLE_THRESH_MIN),
        "player_inactive_thresh_min": _default(overrides, "player_inactive_thresh_min", DEFAULT_PLAYER_INACTIVE_THRESH_MIN),
        "game_idle_thresh_min": _default(overrides, "game_idle_thresh_min", DEFAULT_GAME_IDLE_THRESH_MIN),
        "game_inactive_thresh_min": _default(overrides, "game_inactive_thresh_min", DEFAULT_GAME_INACTIVE_THRESH_MIN),
        "game_retension_thresh_min": _default(overrides, "game_retension_thresh_min", DEFAULT_GAME_RETENSION_THRESH_MIN),
        "idle_player_check_period_sec": _default(overrides, "idle_player_check_period_sec", IDLE_PLAYER_CHECK_PERIOD_SEC),
        "idle_player_check_delay_sec": _default(overrides, "idle_player_check_delay_sec", IDLE_PLAYER_CHECK_DELAY_SEC),
        "idle_game_check_period_sec": _default(overrides, "idle_game_check_period_sec", IDLE_GAME_CHECK_PERIOD_SEC),
        "idle_game_check_delay_sec": _default(overrides, "idle_game_check_delay_sec", IDLE_GAME_CHECK_DELAY_SEC),
        "obsolete_game_check_period_sec": _default(overrides, "obsolete_game_check_period_sec", OBSOLETE_GAME_CHECK_PERIOD_SEC),
        "obsolete_game_check_delay_sec": _default(overrides, "obsolete_game_check_delay_sec", OBSOLETE_GAME_CHECK_DELAY_SEC),
    }


def _get(parser: Union[Optional[ConfigParser], SectionProxy], key: str, default: Any) -> Any:
    """Get a value from a parser, returning default if the parser is not set."""
    return default if not parser else parser.get(key, default)


# pylint: disable=too-many-locals
def _parse(parser: Union[Optional[ConfigParser], SectionProxy], defaults: Dict[str, Any]) -> SystemConfig:
    """Create an SystemConfig based on configuration, applying defaults to values that are not available."""
    logfile_path = _get(parser, "logfile_path", defaults["logfile_path"])
    server_host = _get(parser, "server_host", defaults["server_host"])
    server_port = int(_get(parser, "server_port", defaults["server_port"]))
    total_game_limit = int(_get(parser, "total_game_limit", defaults["total_game_limit"]))
    in_progress_game_limit = int(_get(parser, "in_progress_game_limit", defaults["in_progress_game_limit"]))
    registered_player_limit = int(_get(parser, "registered_player_limit", defaults["registered_player_limit"]))
    player_idle_thresh_min = int(_get(parser, "player_idle_thresh_min", defaults["player_idle_thresh_min"]))
    player_inactive_thresh_min = int(_get(parser, "player_inactive_thresh_min", defaults["player_inactive_thresh_min"]))
    game_idle_thresh_min = int(_get(parser, "game_idle_thresh_min", defaults["game_idle_thresh_min"]))
    game_inactive_thresh_min = int(_get(parser, "game_inactive_thresh_min", defaults["game_inactive_thresh_min"]))
    game_retension_thresh_min = int(_get(parser, "game_retension_thresh_min", defaults["game_retension_thresh_min"]))
    idle_player_check_period_sec = int(_get(parser, "idle_player_check_period_sec", defaults["idle_player_check_period_sec"]))
    idle_player_check_delay_sec = int(_get(parser, "idle_player_check_delay_sec", defaults["idle_player_check_delay_sec"]))
    idle_game_check_period_sec = int(_get(parser, "idle_game_check_period_sec", defaults["idle_game_check_period_sec"]))
    idle_game_check_delay_sec = int(_get(parser, "idle_game_check_delay_sec", defaults["idle_game_check_delay_sec"]))
    obsolete_game_check_period_sec = int(_get(parser, "obsolete_game_check_period_sec", defaults["obsolete_game_check_period_sec"]))
    obsolete_game_check_delay_sec = int(_get(parser, "obsolete_game_check_delay_sec", defaults["obsolete_game_check_delay_sec"]))
    return SystemConfig(
        logfile_path=logfile_path,
        server_host=server_host,
        server_port=server_port,
        total_game_limit=total_game_limit,
        in_progress_game_limit=in_progress_game_limit,
        registered_player_limit=registered_player_limit,
        player_idle_thresh_min=player_idle_thresh_min,
        player_inactive_thresh_min=player_inactive_thresh_min,
        game_idle_thresh_min=game_idle_thresh_min,
        game_inactive_thresh_min=game_inactive_thresh_min,
        game_retension_thresh_min=game_retension_thresh_min,
        idle_player_check_period_sec=idle_player_check_period_sec,
        idle_player_check_delay_sec=idle_player_check_delay_sec,
        idle_game_check_period_sec=idle_game_check_period_sec,
        idle_game_check_delay_sec=idle_game_check_delay_sec,
        obsolete_game_check_period_sec=obsolete_game_check_period_sec,
        obsolete_game_check_delay_sec=obsolete_game_check_delay_sec,
    )


def _load(config_path: str, defaults: Dict[str, Any]) -> SystemConfig:
    """Load configuration from disk, applying defaults for any value that is not found."""
    if not os.path.exists(config_path):
        return _parse(None, defaults)
    else:
        with open(config_path) as f:
            parser = configparser.ConfigParser()
            parser.read(f)
            return _parse(parser["server"], defaults)


def load_config(config_path: Optional[str], overrides: Optional[Dict[str, Any]]) -> None:
    """Load global configuration for later use, applying defaults for any value that is not found."""
    global _CONFIG  # pylint: disable=global-statement
    defaults = _defaults(overrides)
    if config_path:
        if not os.path.exists(config_path):  # if they override config, it must exist
            raise ValueError("Config path does not exist: %s" % config_path)
        _CONFIG = _load(config_path, defaults)
    else:
        _CONFIG = _load(DEFAULT_CONFIG_PATH, defaults)  # it's ok if the default config doesn't exist


def config() -> SystemConfig:
    """Return system configuration."""
    if not _CONFIG:
        raise ValueError("Configuration has not yet been loaded.")
    return _CONFIG
