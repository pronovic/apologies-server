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
from typing import Any, Dict, Optional, Sequence, Type

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
    "RegisterPlayerContext",
    "AdvertiseGameContext",
    "JoinGameContext",
    "ExecuteMoveContext",
    "SendMessageContext",
    "RequestFailedContext",
    "RegisteredPlayer",
    "RegisteredPlayersContext",
    "AvailableGame",
    "AvailableGamesContext",
    "PlayerRegisteredContext",
    "PlayerMessageReceivedContext",
    "GameAdvertisedContext",
    "GameInvitationContext",
    "GameJoinedContext",
    "GameCancelledContext",
    "GameCompletedContext",
    "GamePlayer",
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

    WAITING = "Waiting"
    JOINED = "Joined"
    PLAYING = "Playing"
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
class RegisteredPlayer:
    """A registered player within a RegisteredPlayersContext."""

    handle = attr.ib(type=str)
    registration_date = attr.ib(type=DateTime)
    last_active_date = attr.ib(type=DateTime)
    connection_state = attr.ib(type=ConnectionState)
    activity_state = attr.ib(type=ActivityState)
    player_state = attr.ib(type=PlayerState)
    game_id = attr.ib(type=str)


@attr.s
class RegisteredPlayersContext(Context):
    """Context for a REGISTERED_PLAYERS event."""

    players = attr.ib(type=Sequence[RegisteredPlayer])


@attr.s
class AvailableGame:
    """An available game within an AvailableGamesContext."""

    game_id = attr.ib(type=str)
    name = attr.ib(type=str)
    mode = attr.ib(type=GameMode)
    advertiser_handle = attr.ib(type=str)
    players = attr.ib(type=int)
    available = attr.ib(type=int)
    visibility = attr.ib(type=Visibility)
    invited = attr.ib(type=bool)


@attr.s
class AvailableGamesContext(Context):
    """Context for an AVAILABLE_GAMES event."""

    games = attr.ib(type=Sequence[AvailableGame])


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
class GamePlayer:
    """A game player within a GamePlayerChangeContext."""

    handle = attr.ib(type=Optional[str])
    player_type = attr.ib(type=PlayerType)
    player_state = attr.ib(type=PlayerState)


@attr.s
class GamePlayerChangeContext(Context):
    """Context for an GAME_PLAYER_CHANGE event."""

    comment = attr.ib(type=Optional[str])
    players = attr.ib(type=Dict[PlayerColor, GamePlayer])


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
    REGISTER_PLAYER = "Register Player"
    REREGISTER_PLAYER = "Reregister Player"
    UNREGISTER_PLAYER = "Unregister Player"
    LIST_PLAYERS = "List Players"
    ADVERTISE_GAME = "Advertise Game"
    LIST_AVAILABLE_GAMES = "List Available"
    JOIN_GAME = "Join Game"
    QUIT_GAME = "Quit Game"
    START_GAME = "Start Game"
    CANCEL_GAME = "Cancel Game"
    EXECUTE_MOVE = "Execute Move"
    RETRIEVE_GAME_STATE = "Retrieve Game State"
    SEND_MESSAGE = "Send Message"

    # Events published from server to one or more clients
    REQUEST_FAILED = "Request Failed"
    REGISTERED_PLAYERS = "Registered Players"
    AVAILABLE_GAMES = "Available Games"
    PLAYER_REGISTERED = "Player Registered"
    PLAYER_DISCONNECTED = "Player Disconnected"
    PLAYER_IDLE = "Player Idle"
    PLAYER_INACTIVE = "Player Inactive"
    PLAYER_MESSAGE_RECEIVED = "Player Message Received"
    GAME_ADVERTISED = "Game Advertised"
    GAME_INVITATION = "Game Invitation"
    GAME_JOINED = "Game Joined"
    GAME_STARTED = "Game Started"
    GAME_CANCELLED = "Game Cancelled"
    GAME_COMPLETED = "Game Completed"
    GAME_IDLE = "Game Idle"
    GAME_INACTIVE = "Game Inactive"
    GAME_OBSOLETE = "Game Obsolete"
    GAME_PLAYER_CHANGE = "Game Player Change"
    GAME_STATE_CHANGE = "Game State Change"
    GAME_PLAYER_TURN = "Game Player Turn"


# Map from MessageType to context
_CONTEXT: Dict[MessageType, Optional[Type[Context]]] = {
    MessageType.REGISTER_PLAYER: RegisterPlayerContext,
    MessageType.REREGISTER_PLAYER: None,
    MessageType.UNREGISTER_PLAYER: None,
    MessageType.LIST_PLAYERS: None,
    MessageType.ADVERTISE_GAME: AdvertiseGameContext,
    MessageType.LIST_AVAILABLE_GAMES: None,
    MessageType.JOIN_GAME: JoinGameContext,
    MessageType.QUIT_GAME: None,
    MessageType.START_GAME: None,
    MessageType.CANCEL_GAME: None,
    MessageType.EXECUTE_MOVE: ExecuteMoveContext,
    MessageType.RETRIEVE_GAME_STATE: None,
    MessageType.SEND_MESSAGE: SendMessageContext,
    MessageType.REQUEST_FAILED: RequestFailedContext,
    MessageType.REGISTERED_PLAYERS: RegisteredPlayersContext,
    MessageType.AVAILABLE_GAMES: AvailableGamesContext,
    MessageType.PLAYER_REGISTERED: PlayerRegisteredContext,
    MessageType.PLAYER_DISCONNECTED: None,
    MessageType.PLAYER_IDLE: None,
    MessageType.PLAYER_INACTIVE: None,
    MessageType.PLAYER_MESSAGE_RECEIVED: PlayerMessageReceivedContext,
    MessageType.GAME_ADVERTISED: GameAdvertisedContext,
    MessageType.GAME_INVITATION: GameInvitationContext,
    MessageType.GAME_JOINED: GameJoinedContext,
    MessageType.GAME_STARTED: None,
    MessageType.GAME_CANCELLED: GameCancelledContext,
    MessageType.GAME_COMPLETED: GameCompletedContext,
    MessageType.GAME_IDLE: None,
    MessageType.GAME_INACTIVE: None,
    MessageType.GAME_OBSOLETE: None,
    MessageType.GAME_PLAYER_CHANGE: GamePlayerChangeContext,
    MessageType.GAME_STATE_CHANGE: GameStateChangeContext,
    MessageType.GAME_PLAYER_TURN: GamePlayerTurnContext,
}

# List of all enumerations that are part of the public interface
_ENUMS = [
    Visibility,
    FailureReason,
    CancelledReason,
    PlayerType,
    PlayerState,
    ConnectionState,
    ActivityState,
    MessageType,
    GameMode,
    PlayerColor,
]

_DATE_FORMAT = "YYYY-MM-DDTHH:mm:ss,SSSZ"  # gives us something like "2020-04-27T09:02:14,334+00:00"


class _CattrConverter(cattr.Converter):  # type: ignore
    """
    Cattr converter for requests and events, to standardize conversion of dates and enumerations.
    """

    def __init__(self) -> None:
        super().__init__()
        self.register_unstructure_hook(DateTime, lambda value: value.format(_DATE_FORMAT) if value else None)
        self.register_structure_hook(DateTime, lambda value, _: parse(value) if value else None)
        for element in _ENUMS:
            self.register_unstructure_hook(element, lambda value: value.name if value else None)
            self.register_structure_hook(element, lambda value, _, e=element: e[value] if value else None)


# Cattr converter used to serialize and deserialize requests and responses
_CONVERTER = _CattrConverter()


# noinspection PyTypeChecker
@attr.s(frozen=True)
class Message:
    """A message that is part of the public interface, either a client request or a published event."""

    message = attr.ib(type=MessageType)
    context = attr.ib(type=Any, default=None)

    @message.validator
    def _validate_message(self, attribute: Attribute[MessageType], value: MessageType) -> None:
        if value is None or not isinstance(value, MessageType):
            raise ValueError("'%s' must be a MessageType" % attribute.name)

    @context.validator
    def _validate_context(self, attribute: Attribute[Context], value: Context) -> None:
        if _CONTEXT[self.message] is not None:
            if self.context is None:
                raise ValueError("Message type %s requires a context" % self.message.name)
            elif not isinstance(self.context, _CONTEXT[self.message]):  # type: ignore
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
        if _CONTEXT[message] is None:
            if "context" in d and d["context"] is not None:
                raise ValueError("Message type %s does not allow a context" % message.name)
            context = None
        else:
            if "context" not in d or d["context"] is None:
                raise ValueError("Message type %s requires a context" % message.name)
            try:
                context = _CONVERTER.structure(d["context"], _CONTEXT[message])
            except KeyError as e:
                raise ValueError("Invalid value %s" % str(e))
            except TypeError as e:
                raise ValueError("Message type %s does not support this context" % message.name, e)
        return Message(message, context)
