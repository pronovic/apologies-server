# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:

"""
System configuration.
"""

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
DEFAULT_CLOSE_TIMEOUT_SEC = 10
DEFAULT_WEBSOCKET_LIMIT = 1000
DEFAULT_TOTAL_GAME_LIMIT = 1000
DEFAULT_IN_PROGRESS_GAME_LIMIT = 25
DEFAULT_REGISTERED_PLAYER_LIMIT = 100
DEFAULT_WEBSOCKET_IDLE_THRESH_MIN = 2
DEFAULT_WEBSOCKET_INACTIVE_THRESH_MIN = 5
DEFAULT_PLAYER_IDLE_THRESH_MIN = 15
DEFAULT_PLAYER_INACTIVE_THRESH_MIN = 30
DEFAULT_GAME_IDLE_THRESH_MIN = 10
DEFAULT_GAME_INACTIVE_THRESH_MIN = 20
DEFAULT_GAME_RETENTION_THRESH_MIN = 2880  # 2 days
IDLE_WEBSOCKET_CHECK_PERIOD_SEC = 120
IDLE_WEBSOCKET_CHECK_DELAY_SEC = 300
IDLE_PLAYER_CHECK_PERIOD_SEC = 120
IDLE_PLAYER_CHECK_DELAY_SEC = 300
IDLE_GAME_CHECK_PERIOD_SEC = 120
IDLE_GAME_CHECK_DELAY_SEC = 300
OBSOLETE_GAME_CHECK_PERIOD_SEC = 300
OBSOLETE_GAME_CHECK_DELAY_SEC = 300

DEFAULTS = {
    "logfile_path": DEFAULT_LOGFILE_PATH,
    "server_host": DEFAULT_SERVER_HOST,
    "server_port": DEFAULT_SERVER_PORT,
    "close_timeout_sec": DEFAULT_CLOSE_TIMEOUT_SEC,
    "websocket_limit": DEFAULT_WEBSOCKET_LIMIT,
    "total_game_limit": DEFAULT_TOTAL_GAME_LIMIT,
    "in_progress_game_limit": DEFAULT_IN_PROGRESS_GAME_LIMIT,
    "registered_player_limit": DEFAULT_REGISTERED_PLAYER_LIMIT,
    "websocket_idle_thresh_min": DEFAULT_WEBSOCKET_IDLE_THRESH_MIN,
    "websocket_inactive_thresh_min": DEFAULT_WEBSOCKET_INACTIVE_THRESH_MIN,
    "player_idle_thresh_min": DEFAULT_PLAYER_IDLE_THRESH_MIN,
    "player_inactive_thresh_min": DEFAULT_PLAYER_INACTIVE_THRESH_MIN,
    "game_idle_thresh_min": DEFAULT_GAME_IDLE_THRESH_MIN,
    "game_inactive_thresh_min": DEFAULT_GAME_INACTIVE_THRESH_MIN,
    "game_retention_thresh_min": DEFAULT_GAME_RETENTION_THRESH_MIN,
    "idle_websocket_check_period_sec": IDLE_WEBSOCKET_CHECK_PERIOD_SEC,
    "idle_websocket_check_delay_sec": IDLE_WEBSOCKET_CHECK_DELAY_SEC,
    "idle_player_check_period_sec": IDLE_PLAYER_CHECK_PERIOD_SEC,
    "idle_player_check_delay_sec": IDLE_PLAYER_CHECK_DELAY_SEC,
    "idle_game_check_period_sec": IDLE_GAME_CHECK_PERIOD_SEC,
    "idle_game_check_delay_sec": IDLE_GAME_CHECK_DELAY_SEC,
    "obsolete_game_check_period_sec": OBSOLETE_GAME_CHECK_PERIOD_SEC,
    "obsolete_game_check_delay_sec": OBSOLETE_GAME_CHECK_DELAY_SEC,
}

# pylint: disable=too-many-instance-attributes
@attr.s(frozen=True)
class SystemConfig:
    """
    System configuration.
    
    Attributes:
        logfile_path(str): The path to the log file on disk
        server_host(str): The hostname to bind to
        server_port(int): The server port to listen on
        close_timeout_sec(int): The maximum amount of time to wait when closing a connection
        websocket_limit(int): Limit on the number of websocket connections
        total_game_limit(int): Limit on the total number of tracked games
        in_progress_game_limit(int): Limit on the number of in progress games
        registered_player_limit(int): Limit on the number of registered players
        websocket_idle_thresh_min(int): Number of minutes of no activity before a websocket with no players is considered idle
        websocket_inactive_thresh_min(int): Number of minutes of no activity before a websocket with no players is inactive
        player_idle_thresh_min(int): Number of minutes of no activity before a player is considered idle
        player_inactive_thresh_min(int): Number of minutes of no activity before a player is considered inactive
        game_idle_thresh_min(int): Number of minutes of no activity before a game is considered idle
        game_inactive_thresh_min(int): Number of minutes of no activity before a game is considered inactive
        game_retention_thresh_min(int): Number of minutes to retain data about games after they are completed
        idle_websocket_check_period_sec(int): Number of seconds to wait between executions of the Idle Websocket Check task
        idle_websocket_check_delay_sec(int): Number of seconds to delay before the first Idle Websocket Check task
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
    close_timeout_sec = attr.ib(type=int, default=DEFAULT_CLOSE_TIMEOUT_SEC)
    websocket_limit = attr.ib(type=int, default=DEFAULT_WEBSOCKET_LIMIT)
    total_game_limit = attr.ib(type=int, default=DEFAULT_TOTAL_GAME_LIMIT)
    in_progress_game_limit = attr.ib(type=int, default=DEFAULT_IN_PROGRESS_GAME_LIMIT)
    registered_player_limit = attr.ib(type=int, default=DEFAULT_REGISTERED_PLAYER_LIMIT)
    websocket_idle_thresh_min = attr.ib(type=int, default=DEFAULT_WEBSOCKET_IDLE_THRESH_MIN)
    websocket_inactive_thresh_min = attr.ib(type=int, default=DEFAULT_WEBSOCKET_INACTIVE_THRESH_MIN)
    player_idle_thresh_min = attr.ib(type=int, default=DEFAULT_PLAYER_IDLE_THRESH_MIN)
    player_inactive_thresh_min = attr.ib(type=int, default=DEFAULT_PLAYER_INACTIVE_THRESH_MIN)
    game_idle_thresh_min = attr.ib(type=int, default=DEFAULT_GAME_IDLE_THRESH_MIN)
    game_inactive_thresh_min = attr.ib(type=int, default=DEFAULT_GAME_INACTIVE_THRESH_MIN)
    game_retention_thresh_min = attr.ib(type=int, default=DEFAULT_GAME_RETENTION_THRESH_MIN)
    idle_websocket_check_period_sec = attr.ib(type=int, default=IDLE_WEBSOCKET_CHECK_PERIOD_SEC)
    idle_websocket_check_delay_sec = attr.ib(type=int, default=IDLE_WEBSOCKET_CHECK_DELAY_SEC)
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


def _get(
    parser: Union[Optional[ConfigParser], SectionProxy], key: str, overrides: Optional[Dict[str, Any]], defaults: Dict[str, Any]
) -> Any:
    """Get a value from a parser, overriding or setting a default as necessary."""
    override = overrides[key] if overrides and key in overrides else None
    default = defaults[key] if defaults and key in defaults else None
    return override if override else parser.get(key, default) if parser else default


# pylint: disable=too-many-locals
def _parse(
    parser: Union[Optional[ConfigParser], SectionProxy], overrides: Optional[Dict[str, Any]], defaults: Dict[str, Any]
) -> SystemConfig:
    """Create an SystemConfig based on configuration, applying defaults to values that are not available."""
    logfile_path = _get(parser, "logfile_path", overrides, defaults)
    server_host = _get(parser, "server_host", overrides, defaults)
    server_port = int(_get(parser, "server_port", overrides, defaults))
    close_timeout_sec = int(_get(parser, "close_timeout_sec", overrides, defaults))
    websocket_limit = int(_get(parser, "websocket_limit", overrides, defaults))
    total_game_limit = int(_get(parser, "total_game_limit", overrides, defaults))
    in_progress_game_limit = int(_get(parser, "in_progress_game_limit", overrides, defaults))
    registered_player_limit = int(_get(parser, "registered_player_limit", overrides, defaults))
    websocket_idle_thresh_min = int(_get(parser, "websocket_idle_thresh_min", overrides, defaults))
    websocket_inactive_thresh_min = int(_get(parser, "websocket_inactive_thresh_min", overrides, defaults))
    player_idle_thresh_min = int(_get(parser, "player_idle_thresh_min", overrides, defaults))
    player_inactive_thresh_min = int(_get(parser, "player_inactive_thresh_min", overrides, defaults))
    game_idle_thresh_min = int(_get(parser, "game_idle_thresh_min", overrides, defaults))
    game_inactive_thresh_min = int(_get(parser, "game_inactive_thresh_min", overrides, defaults))
    game_retention_thresh_min = int(_get(parser, "game_retention_thresh_min", overrides, defaults))
    idle_websocket_check_period_sec = int(_get(parser, "idle_websocket_check_period_sec", overrides, defaults))
    idle_websocket_check_delay_sec = int(_get(parser, "idle_websocket_check_delay_sec", overrides, defaults))
    idle_player_check_period_sec = int(_get(parser, "idle_player_check_period_sec", overrides, defaults))
    idle_player_check_delay_sec = int(_get(parser, "idle_player_check_delay_sec", overrides, defaults))
    idle_game_check_period_sec = int(_get(parser, "idle_game_check_period_sec", overrides, defaults))
    idle_game_check_delay_sec = int(_get(parser, "idle_game_check_delay_sec", overrides, defaults))
    obsolete_game_check_period_sec = int(_get(parser, "obsolete_game_check_period_sec", overrides, defaults))
    obsolete_game_check_delay_sec = int(_get(parser, "obsolete_game_check_delay_sec", overrides, defaults))
    return SystemConfig(
        logfile_path=logfile_path,
        server_host=server_host,
        server_port=server_port,
        close_timeout_sec=close_timeout_sec,
        websocket_limit=websocket_limit,
        total_game_limit=total_game_limit,
        in_progress_game_limit=in_progress_game_limit,
        registered_player_limit=registered_player_limit,
        websocket_idle_thresh_min=websocket_idle_thresh_min,
        websocket_inactive_thresh_min=websocket_inactive_thresh_min,
        player_idle_thresh_min=player_idle_thresh_min,
        player_inactive_thresh_min=player_inactive_thresh_min,
        game_idle_thresh_min=game_idle_thresh_min,
        game_inactive_thresh_min=game_inactive_thresh_min,
        game_retention_thresh_min=game_retention_thresh_min,
        idle_websocket_check_period_sec=idle_websocket_check_period_sec,
        idle_websocket_check_delay_sec=idle_websocket_check_delay_sec,
        idle_player_check_period_sec=idle_player_check_period_sec,
        idle_player_check_delay_sec=idle_player_check_delay_sec,
        idle_game_check_period_sec=idle_game_check_period_sec,
        idle_game_check_delay_sec=idle_game_check_delay_sec,
        obsolete_game_check_period_sec=obsolete_game_check_period_sec,
        obsolete_game_check_delay_sec=obsolete_game_check_delay_sec,
    )


def _load(config_path: str, overrides: Optional[Dict[str, Any]], defaults: Dict[str, Any]) -> SystemConfig:
    """Load configuration from disk, applying defaults for any value that is not found."""
    if not os.path.exists(config_path):
        return _parse(None, overrides, defaults)
    else:
        parser = configparser.ConfigParser()
        parser.read(config_path)
        return _parse(parser["Server"], overrides, defaults)


def load_config(config_path: Optional[str] = None, overrides: Optional[Dict[str, Any]] = None) -> None:
    """Load global configuration for later use, applying defaults for any value that is not found."""
    global _CONFIG  # pylint: disable=global-statement
    if config_path:
        # if they override the config path, the file must exist
        if not os.path.exists(config_path):
            raise ValueError("Config path does not exist: %s" % config_path)
        _CONFIG = _load(config_path, overrides, DEFAULTS)
    else:
        # however, it's ok if the default config doesn't exist
        _CONFIG = _load(DEFAULT_CONFIG_PATH, overrides, DEFAULTS)


def config() -> SystemConfig:
    """Return system configuration."""
    if not _CONFIG:
        raise ValueError("Configuration has not yet been loaded.")
    return _CONFIG
