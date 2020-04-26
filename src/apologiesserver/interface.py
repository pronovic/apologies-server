# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:

"""
Definition of the public interface for the server (see also notes/API.md).

Both requests (messages from a client) and events (messages to a client) can be
serialized and deserialized to and from JSON.  However, we apply much tighter
validation rules on requests, since the input is untrusted.  We assume that the
Python type validations imposed by MyPy give us everything we need for events.
"""

from __future__ import annotations  # see: https://stackoverflow.com/a/33533514/2907667

from enum import Enum
from typing import Any, Dict, Optional, Sequence

import attr
import cattr
import orjson
from apologies.game import GameMode, PlayerColor
from attr import Attribute
from attr.validators import and_ as _and
from attr.validators import in_ as _in
from pendulum.datetime import DateTime
from pendulum.parser import parse


# pylint: disable=unsubscriptable-object
def _notempty(_: Any, attribute: Attribute[Sequence[str]], value: Sequence[str]) -> Any:
    """attrs validator to ensure that a list is not empty."""
    if len(value) == 0:
        raise ValueError("'%s' may not be empty" % attribute.name)


# pylint: disable=unsubscriptable-object
def _string(_: Any, attribute: Attribute[str], value: str) -> Any:
    """attrs validator to ensure that a string is non-empty."""
    # Annoyingly, due to some quirk in the CattrConverter, we end up with "None" rather than None for strings set to JSON null
    # As a result, we need to prevent "None" as a legal value, but that's probably better anyway.
    if value is None or value == "None" or not isinstance(value, str) or len(value) == 0:
        raise ValueError("'%s' must be non-empty string" % attribute.name)


# pylint: disable=unsubscriptable-object
def _stringlist(_: Any, attribute: Attribute[Sequence[str]], value: Sequence[str]) -> Any:
    """attrs validator to ensure that a string list contains non-empty values."""
    # Annoyingly, due to some quirk in the CattrConverter, we end up with "None" rather than None for strings set to JSON null
    # As a result, we need to prevent "None" as a legal value, but that's probably better anyway.
    for element in value:
        if element is None or element == "None" or not isinstance(element, str) or len(element) == 0:
            raise ValueError("'%s' elements must be non-empty strings" % attribute.name)


class Visibility(Enum):
    """Visibility for advertised games."""

    PUBLIC = "Public"
    PRIVATE = "Private"


class FailureReason(Enum):
    """Failure reasons advertised to clients."""

    USER_LIMIT = "User limit reached"
    INTERNAL_ERROR = "Internal error"


class CancelledReason(Enum):
    """Reasons a game can be cancelled."""

    CANCELLED = "Game was cancelled by advertiser"
    NOT_VIABLE = "Game is no longer viable."


class PlayerType(Enum):
    """Types of players."""

    HUMAN = "Human"
    PROGRAMMATIC = "Programmatic"


class PlayerState(Enum):
    """State of a player within a game."""

    JOINED = "Joined"
    QUIT = "Quit"
    DISCONNECTED = "Disconnected"


class ConnectionState(Enum):
    """A player's connection state."""

    CONNECTED = "Connected"
    DISCONNECTED = "Disconnected"


class ActivityState(Enum):
    """A player's activity state."""

    ACTIVE = "Active"
    IDLE = "Idle"
    INACTIVE = "Inactive"


class PlayState(Enum):
    """A player's play state."""

    WAITING = "Waiting to Play"
    JOINED = "Joined a Game"
    PLAYING = "Playing a Game"


@attr.s
class RegisterPlayerContext:
    """Context for a REGISTER_PLAYER request."""

    handle = attr.ib(type=str, validator=_string)


@attr.s
class AdvertiseGameContext:
    """Context for an ADVERTISE_GAME request."""

    name = attr.ib(type=str, validator=_string)
    mode = attr.ib(type=GameMode, validator=_in(GameMode))
    players = attr.ib(type=int, validator=_in([2, 3, 4]))
    visibility = attr.ib(type=Visibility, validator=_in(Visibility))
    invited_handles = attr.ib(type=Sequence[str], validator=_stringlist)


@attr.s
class JoinGameContext:
    """Context for a JOIN_GAME request."""

    game_id = attr.ib(type=str, validator=_string)


@attr.s
class ExecuteMoveContext:
    """Context for an EXECUTE_MOVE request."""

    move_id = attr.ib(type=str, validator=_string)


@attr.s
class SendMessageContext:
    """Context for an SEND_MESSAGE request."""

    message = attr.ib(type=str, validator=_string)
    recipient_handles = attr.ib(type=Sequence[str], validator=_and(_stringlist, _notempty))


@attr.s
class RequestFailedContext:
    """Context for a REQUEST_FAILED event."""

    reason = attr.ib(type=FailureReason)
    comment = attr.ib(type=Optional[str])


@attr.s
class RegisteredPlayersContext:
    """Context for a REGISTERED_PLAYERS event."""

    @attr.s
    class Player:
        handle = attr.ib(type=str)
        registration_date = attr.ib(type=DateTime)
        last_active_date = attr.ib(type=DateTime)
        connection_state = attr.ib(type=ConnectionState)
        activity_state = attr.ib(type=ActivityState)
        play_state = attr.ib(type=PlayState)
        game_id = attr.ib(type=str)

    players = attr.ib(type=Sequence["RegisteredPlayersContext.Player"])

    @players.default
    def default_players(self) -> Sequence["RegisteredPlayersContext.Player"]:
        return []


@attr.s
class AvailableGamesContext:
    """Context for an AVAILABLE_GAMES event."""

    @attr.s
    class Game:
        game_id = attr.ib(type=str)
        name = attr.ib(type=str)
        mode = attr.ib(type=GameMode)
        advertiser_handle = attr.ib(type=str)
        players = attr.ib(type=int)
        available = attr.ib(type=int)
        visibility = attr.ib(type=Visibility)
        invited = attr.ib(type=bool)

    games = attr.ib(type=Sequence["AvailableGamesContext.Game"])

    @games.default
    def default_games(self) -> Sequence["AvailableGamesContext.Game"]:
        return []


@attr.s
class PlayerRegisteredContext:
    """Context for an PLAYER_REGISTERED event."""

    player_id = attr.ib(type=str)


@attr.s
class PlayerMessageReceivedContext:
    """Context for an PLAYER_MESSAGE_RECEIVED event."""

    sender_handle = attr.ib(type=str)
    recipient_handles = attr.ib(type=Sequence[str])
    message = attr.ib(type=str)


@attr.s
class GameAdvertisedContext:
    """Context for an GAME_ADVERTISED event."""

    game_id = attr.ib(type=str)
    name = attr.ib(type=str)
    mode = attr.ib(type=GameMode)
    advertiser_handle = attr.ib(type=str)
    players = attr.ib(type=int)
    visibility = attr.ib(type=Visibility)
    invited_handles = attr.ib(type=Sequence[str])


@attr.s
class GameInvitationContext:
    """Context for an GAME_INVITATION event."""

    game_id = attr.ib(type=str)
    name = attr.ib(type=str)
    mode = attr.ib(type=GameMode)
    advertiser_handle = attr.ib(type=str)
    players = attr.ib(type=int)
    visibility = attr.ib(type=Visibility)


@attr.s
class GameJoinedContext:
    """Context for an GAME_JOINED event."""

    game_id = attr.ib(type=str)


@attr.s
class GameCancelledContext:
    """Context for an GAME_CANCELLED event."""

    reason = attr.ib(type=CancelledReason)
    comment = attr.ib(type=Optional[str])


@attr.s
class GameCompletedContext:
    """Context for an GAME_COMPLETED event."""

    comment = attr.ib(type=Optional[str])


@attr.s
class GamePlayerChangeContext:
    """Context for an GAME_PLAYER_CHANGE event."""

    @attr.s
    class Player:
        handle = attr.ib(type=str)
        type = attr.ib(type=PlayerType)
        state = attr.ib(type=PlayerState)

    comment = attr.ib(type=Optional[str])
    players = attr.ib(type=Dict[PlayerColor, "GamePlayerChangeContext.Player"])

    @players.default
    def default_players(self) -> Dict[PlayerColor, "GamePlayerChangeContext.Player"]:
        return {}


@attr.s
class GameStateChangeContext:
    """Context for an GAME_STATE_CHANGE event."""

    stuff = attr.ib(type=str)  # TODO: finalize GameStateChangeContext


@attr.s
class GamePlayerTurnContext:
    """Context for an GAME_PLAYER_TURN event."""

    stuff = attr.ib(type=str)  # TODO: finalize GamePlayerTurnContext


class RequestType(Enum):
    """Enumeration of all request types, mapped to the associated context (if any)."""

    REGISTER_PLAYER = RegisterPlayerContext
    REREGISTER_PLAYER = None
    UNREGISTER_PLAYER = None
    LIST_PLAYERS = None
    ADVERTISE_GAME = AdvertiseGameContext
    LIST_AVAILABLE_GAMES = None
    JOIN_GAME = JoinGameContext
    QUIT_GAME = None
    START_GAME = None
    CANCEL_GAME = None
    EXECUTE_MOVE = ExecuteMoveContext
    RETRIEVE_GAME_STATE = None
    SEND_MESSAGE = SendMessageContext


class EventType(Enum):
    """Enumeration of all event types, mapped to the associated context (if any)."""

    REQUEST_FAILED = RequestFailedContext
    REGISTERED_PLAYERS = RegisteredPlayersContext
    AVAILABLE_GAMES = AvailableGamesContext
    PLAYER_REGISTERED = PlayerRegisteredContext
    PLAYER_DISCONNECTED = None
    PLAYER_IDLE = None
    PLAYER_INACTIVE = None
    PLAYER_MESSAGE_RECEIVED = PlayerMessageReceivedContext
    GAME_ADVERTISED = GameAdvertisedContext
    GAME_INVITATION = GameInvitationContext
    GAME_JOINED = GameJoinedContext
    GAME_STARTED = None
    GAME_CANCELLED = GameCancelledContext
    GAME_COMPLETED = GameCompletedContext
    GAME_IDLE = None
    GAME_INACTIVE = None
    GAME_OBSOLETE = None
    GAME_PLAYER_CHANGE = GamePlayerChangeContext
    GAME_STATE_CHANGE = GameStateChangeContext
    GAME_PLAYER_TURN = GamePlayerTurnContext


# List of all enumerations that are part of the public interface
_ENUMS = [
    GameMode,
    ActivityState,
    CancelledReason,
    ConnectionState,
    EventType,
    FailureReason,
    PlayState,
    PlayerState,
    PlayerType,
    RequestType,
    Visibility,
]


class _CattrConverter(cattr.Converter):  # type: ignore
    """
    Cattr converter for requests and events, to standardize conversion of dates and enumerations.
    """

    def __init__(self) -> None:
        super().__init__()
        self.register_unstructure_hook(DateTime, lambda datetime: datetime.isoformat() if datetime else None)
        self.register_structure_hook(DateTime, lambda string, _: parse(string) if string else None)
        for enum in _ENUMS:
            self.register_unstructure_hook(enum, lambda value: value.name if value else None)
            self.register_structure_hook(enum, lambda string, _, e=enum: e[string] if string else None)


# Cattr converter used to serialize and deserialize requests and responses
_CONVERTER = _CattrConverter()

# TODO: there's too much overlap between Request and Event
#   I need to pull up something - not sure if it's a different
#   module for JSON-realted stuff (maybe in util) or whether
#   I want a parent class.  Either way, it's ugly right now.

# TODO: whenever I pull this out, I need to standardize
#   the error-handling behavior so we get errors that can
#   be returned to callers.  Right now, it's a mismash of
#   AssertionError, TypeError, and ValueError, and it's
#   not intelligible.


@attr.s
class Request:
    """A request received from a client."""

    request = attr.ib(type=RequestType)
    context = attr.ib(type=Any, default=None)

    # noinspection PyTypeChecker
    def to_json(self) -> str:
        """Convert the request to JSON."""
        assert self.request is not None
        if self.request.value is not None:
            assert isinstance(self.context, self.request.value)
        else:
            assert self.context is None
        d = _CONVERTER.unstructure(self)  # pylint: disable=invalid-name
        if d["context"] is None:
            del d["context"]
        return orjson.dumps(d, option=orjson.OPT_INDENT_2).decode("utf-8")  # type: ignore

    @staticmethod
    def from_json(data: str) -> Request:
        """Create a request based on JSON data."""
        d = orjson.loads(data)  # pylint: disable=invalid-name
        request = RequestType[d["request"]]
        if request.value is None:
            assert "context" not in d or d["context"] is None
        else:
            assert "context" in d and d["context"] is not None
        context = None if request.value is None else _CONVERTER.structure(d["context"], request.value)
        return Request(request, context)


@attr.s
class Event:
    """An event published to a client."""

    event = attr.ib(type=EventType)
    context = attr.ib(type=Any, default=None)

    # noinspection PyTypeChecker
    def to_json(self) -> str:
        """Convert the event to JSON."""
        assert self.event is not None
        if self.event.value is not None:
            assert isinstance(self.context, self.event.value)
        else:
            assert self.context is None
        d = _CONVERTER.unstructure(self)  # pylint: disable=invalid-name
        if d["context"] is None:
            del d["context"]
        return orjson.dumps(d, option=orjson.OPT_INDENT_2).decode("utf-8")  # type: ignore

    @staticmethod
    def from_json(data: str) -> Event:
        """Create an event based on JSON data."""
        d = orjson.loads(data)  # pylint: disable=invalid-name
        event = EventType[d["event"]]
        if event.value is None:
            assert "context" not in d or d["context"] is None
        else:
            assert "context" in d and d["context"] is not None
        context = None if event.value is None else _CONVERTER.structure(d["context"], event.value)
        return Event(event, context)
