# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=unsubscriptable-object

"""
Definition of the public interface for the server.

Both requests (message sent from a client to the server) and events (published 
from the server to one or more clients) can be serialized and deserialized to 
and from JSON.  However, we apply much tighter validation rules on the context
associated with requests, since the input is untrusted.  We assume that the
Python type validations imposed by MyPy give us everything we need for events
that are only built internally.

The file notes/API.md includes a detailed discussion of each request and event.
"""

from __future__ import annotations  # see: https://stackoverflow.com/a/33533514/2907667

from abc import ABC
from enum import Enum
from typing import Any, Dict, Optional, Sequence

import attr
import cattr
import orjson
from apologies.game import GameMode, PlayerColor
from attr import Attribute
from attr.validators import and_, in_
from pendulum.datetime import DateTime
from pendulum.parser import parse

from .validator import enum, notempty, string, stringlist

# There are a lot of classes as part of this interface, so it's useful to import *.
# However, when we do that, we want to expose only the public parts of the interface.
__all__ = [
    "Visibility",
    "FailureReason",
    "CancelledReason",
    "PlayerType",
    "PlayerState",
    "ConnectionState",
    "ActivityState",
    "PlayState",
    "RegisterPlayerContext",
    "AdvertiseGameContext",
    "JoinGameContext",
    "ExecuteMoveContext",
    "SendMessageContext",
    "RequestFailedContext",
    "RegisteredPlayersContext",
    "AvailableGamesContext",
    "PlayerRegisteredContext",
    "PlayerMessageReceivedContext",
    "GameAdvertisedContext",
    "GameInvitationContext",
    "GameJoinedContext",
    "GameCancelledContext",
    "GameCompletedContext",
    "GamePlayerChangeContext",
    "GameStateChangeContext",
    "GamePlayerTurnContext",
    "MessageType",
    "Message",
]


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


class Context(ABC):
    """Abstract message context."""


@attr.s
class RegisterPlayerContext(Context):
    """Context for a REGISTER_PLAYER request."""

    handle = attr.ib(type=str, validator=string)


@attr.s
class AdvertiseGameContext(Context):
    """Context for an ADVERTISE_GAME request."""

    name = attr.ib(type=str, validator=string)
    mode = attr.ib(type=GameMode, validator=enum(GameMode))
    players = attr.ib(type=int, validator=in_([2, 3, 4]))
    visibility = attr.ib(type=Visibility, validator=enum(Visibility))
    invited_handles = attr.ib(type=Sequence[str], validator=stringlist)


@attr.s
class JoinGameContext(Context):
    """Context for a JOIN_GAME request."""

    game_id = attr.ib(type=str, validator=string)


@attr.s
class ExecuteMoveContext(Context):
    """Context for an EXECUTE_MOVE request."""

    move_id = attr.ib(type=str, validator=string)


@attr.s
class SendMessageContext(Context):
    """Context for an SEND_MESSAGE request."""

    message = attr.ib(type=str, validator=string)
    recipient_handles = attr.ib(type=Sequence[str], validator=and_(stringlist, notempty))


@attr.s
class RequestFailedContext(Context):
    """Context for a REQUEST_FAILED event."""

    reason = attr.ib(type=FailureReason)
    comment = attr.ib(type=Optional[str])


@attr.s
class RegisteredPlayersContext(Context):
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


@attr.s
class AvailableGamesContext(Context):
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


@attr.s
class PlayerRegisteredContext(Context):
    """Context for an PLAYER_REGISTERED event."""

    player_id = attr.ib(type=str)


@attr.s
class PlayerMessageReceivedContext(Context):
    """Context for an PLAYER_MESSAGE_RECEIVED event."""

    sender_handle = attr.ib(type=str)
    recipient_handles = attr.ib(type=Sequence[str])
    message = attr.ib(type=str)


@attr.s
class GameAdvertisedContext(Context):
    """Context for an GAME_ADVERTISED event."""

    game_id = attr.ib(type=str)
    name = attr.ib(type=str)
    mode = attr.ib(type=GameMode)
    advertiser_handle = attr.ib(type=str)
    players = attr.ib(type=int)
    visibility = attr.ib(type=Visibility)
    invited_handles = attr.ib(type=Sequence[str])


@attr.s
class GameInvitationContext(Context):
    """Context for an GAME_INVITATION event."""

    game_id = attr.ib(type=str)
    name = attr.ib(type=str)
    mode = attr.ib(type=GameMode)
    advertiser_handle = attr.ib(type=str)
    players = attr.ib(type=int)
    visibility = attr.ib(type=Visibility)


@attr.s
class GameJoinedContext(Context):
    """Context for an GAME_JOINED event."""

    game_id = attr.ib(type=str)


@attr.s
class GameCancelledContext(Context):
    """Context for an GAME_CANCELLED event."""

    reason = attr.ib(type=CancelledReason)
    comment = attr.ib(type=Optional[str])


@attr.s
class GameCompletedContext(Context):
    """Context for an GAME_COMPLETED event."""

    comment = attr.ib(type=Optional[str])


@attr.s
class GamePlayerChangeContext(Context):
    """Context for an GAME_PLAYER_CHANGE event."""

    @attr.s
    class Player:
        handle = attr.ib(type=str)
        type = attr.ib(type=PlayerType)
        state = attr.ib(type=PlayerState)

    comment = attr.ib(type=Optional[str])
    players = attr.ib(type=Dict[PlayerColor, "GamePlayerChangeContext.Player"])


@attr.s
class GameStateChangeContext(Context):
    """Context for an GAME_STATE_CHANGE event."""

    stuff = attr.ib(type=str)  # TODO: finalize GameStateChangeContext


@attr.s
class GamePlayerTurnContext(Context):
    """Context for an GAME_PLAYER_TURN event."""

    stuff = attr.ib(type=str)  # TODO: finalize GamePlayerTurnContext


class MessageType(Enum):
    """Enumeration of all message types, mapped to the associated context (if any)."""

    # Requests sent from client to server
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

    # Events published from server to one or more clients
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
    Visibility,
    FailureReason,
    CancelledReason,
    PlayerType,
    PlayerState,
    ConnectionState,
    ActivityState,
    PlayState,
    MessageType,
    GameMode,
]


class _CattrConverter(cattr.Converter):  # type: ignore
    """
    Cattr converter for requests and events, to standardize conversion of dates and enumerations.
    """

    def __init__(self) -> None:
        super().__init__()
        self.register_unstructure_hook(DateTime, lambda datetime: datetime.isoformat() if datetime else None)
        self.register_structure_hook(DateTime, lambda string, _: parse(string) if string else None)
        for element in _ENUMS:
            self.register_unstructure_hook(element, lambda value: value.name if value else None)
            self.register_structure_hook(element, lambda string, _, e=element: e[string] if string else None)


# Cattr converter used to serialize and deserialize requests and responses
_CONVERTER = _CattrConverter()

# noinspection PyTypeChecker
@attr.s
class Message:
    """A message that is part of the public interface, either a client request or a published event."""

    message = attr.ib(type=MessageType)
    context = attr.ib(type=Context, default=None)

    @message.validator
    def _validate_message(self, attribute: Attribute[MessageType], value: MessageType) -> None:
        if value is None or not isinstance(value, MessageType):
            raise ValueError("'%s' must be a MessageType" % attribute.name)

    @context.validator
    def _validate_context(self, attribute: Attribute[Context], value: Context) -> None:
        if self.message.value is not None:
            if self.context is None:
                raise ValueError("Message type %s requires a context" % self.message.name)
            elif not isinstance(self.context, self.message.value):
                raise ValueError("Message type %s does not support this context" % self.message.name)
        else:
            if self.context is not None:
                raise ValueError("Message type %s does not allow a context" % self.message.name)

    def to_json(self) -> str:
        """Convert the request to JSON."""
        d = _CONVERTER.unstructure(self)  # pylint: disable=invalid-name
        if d["context"] is None:
            del d["context"]
        return orjson.dumps(d, option=orjson.OPT_INDENT_2).decode("utf-8")  # type: ignore

    @staticmethod
    def from_json(data: str) -> Message:
        """Create a request based on JSON data."""
        d = orjson.loads(data)  # pylint: disable=invalid-name
        if "message" not in d or d["message"] is None:
            raise ValueError("Message type is required")
        try:
            message = MessageType[d["message"]]
        except KeyError:
            raise ValueError("Unknown message type: %s" % d["message"])
        if message.value is None:
            if "context" in d and d["context"] is not None:
                raise ValueError("Message type %s does not allow a context" % message.name)
            context = None
        else:
            if "context" not in d or d["context"] is None:
                raise ValueError("Message type %s requires a context" % message.name)
            try:
                context = _CONVERTER.structure(d["context"], message.value)
            except KeyError as e:
                raise ValueError("Invalid value %s" % str(e))
            except TypeError as e:
                raise ValueError("Message type %s does not support this context" % message.name, e)
        return Message(message, context)
