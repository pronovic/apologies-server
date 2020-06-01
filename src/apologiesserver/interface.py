# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=unsubscriptable-object

"""
Definition of the public interface for the server.

Both requests (message sent from a client to the server) and events (published 
from the server to one or more clients) can be serialized and deserialized to 
and from JSON.  However, we apply much tighter validation rules on the context
associated with requests, since the input is untrusted.  We assume that the
unit tests and the Python type validations imposed by MyPy give us everything
we need for events that are only built internally.

The file notes/API.md includes a detailed discussion of each request and event.
"""

from __future__ import annotations  # see: https://stackoverflow.com/a/33533514/2907667

from abc import ABC
from enum import Enum
from typing import Any, Dict, List, Optional, Type

import attr
import cattr
import orjson
from apologies.game import CardType, GameMode, History, Pawn, Player, PlayerColor, PlayerView, Position
from apologies.rules import Action, ActionType, Move
from attr import Attribute
from attr.validators import and_, in_
from pendulum.datetime import DateTime
from pendulum.parser import parse

from .validator import enum, length, notempty, string, stringlist

__all__ = [
    "Visibility",
    "CancelledReason",
    "PlayerType",
    "PlayerState",
    "ConnectionState",
    "ActivityState",
    "GameState",
    "FailureReason",
    "MessageType",
    "ProcessingError",
    "GamePlayer",
    "RegisteredPlayer",
    "AdvertisedGame",
    "GameStatePawn",
    "GameStatePlayer",
    "GameStateHistory",
    "GameAction",
    "GameMove",
    "RegisterPlayerContext",
    "ReregisterPlayerContext",
    "AdvertiseGameContext",
    "JoinGameContext",
    "ExecuteMoveContext",
    "SendMessageContext",
    "RequestFailedContext",
    "RegisteredPlayersContext",
    "AvailableGamesContext",
    "PlayerRegisteredContext",
    "PlayerUnregisteredContext",
    "PlayerIdleContext",
    "PlayerInactiveContext",
    "PlayerMessageReceivedContext",
    "GameAdvertisedContext",
    "GameInvitationContext",
    "GameJoinedContext",
    "GameStartedContext",
    "GameCancelledContext",
    "GameCompletedContext",
    "GameIdleContext",
    "GameInactiveContext",
    "GamePlayerQuitContext",
    "GamePlayerChangeContext",
    "GameStateChangeContext",
    "GamePlayerTurnContext",
    "Message",
]


class Visibility(Enum):
    """Visibility for advertised games."""

    PUBLIC = "Public"
    PRIVATE = "Private"


class CancelledReason(Enum):
    """Reasons a game can be cancelled."""

    CANCELLED = "Game was cancelled by advertiser"
    NOT_VIABLE = "Game is no longer viable."
    INACTIVE = "The game was idle too long and was marked inactive"
    SHUTDOWN = "Game was cancelled due to system shutdown"


class PlayerType(Enum):
    """Types of players."""

    HUMAN = "Human"
    PROGRAMMATIC = "Programmatic"


class PlayerState(Enum):
    """A player's game state."""

    WAITING = "Waiting"
    JOINED = "Joined"
    PLAYING = "Playing"
    FINISHED = "Finished"
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


class GameState(Enum):
    """A game's state."""

    ADVERTISED = "Advertised"
    PLAYING = "Playing"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class FailureReason(Enum):
    """Failure reasons advertised to clients."""

    INVALID_REQUEST = "Invalid request"
    DUPLICATE_USER = "Handle is already in use"
    INVALID_AUTH = "Missing or invalid authorization header"
    WEBSOCKET_LIMIT = "Connection limit reached; try again later"
    USER_LIMIT = "System user limit reached; try again later"
    GAME_LIMIT = "System game limit reached; try again later"
    INVALID_PLAYER = "Unknown or invalid player"
    INVALID_GAME = "Unknown or invalid game"
    NOT_PLAYING = "Player is not playing a game"
    NOT_ADVERTISER = "Player did not advertise this game"
    ALREADY_PLAYING = "Player is already playing a game"
    NO_MOVE_PENDING = "No move is pending for this player"
    ILLEGAL_MOVE = "The chosen move is not legal"
    ADVERTISER_MAY_NOT_QUIT = "Advertiser may not quit a game (cancel instead)"
    INTERNAL_ERROR = "Internal error"


class MessageType(Enum):
    """Enumeration of all message types, including received events and published requests."""

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
    SERVER_SHUTDOWN = "Server Shutdown"
    REQUEST_FAILED = "Request Failed"
    REGISTERED_PLAYERS = "Registered Players"
    AVAILABLE_GAMES = "Available Games"
    PLAYER_REGISTERED = "Player Registered"
    PLAYER_UNREGISTERED = "Player Unregistered"
    WEBSOCKET_IDLE = "Connection Idle"
    WEBSOCKET_INACTIVE = "Connection Inactive"
    PLAYER_IDLE = "Player Idle"
    PLAYER_INACTIVE = "Player Inactive"
    PLAYER_MESSAGE_RECEIVED = "Player Message Received"
    GAME_ADVERTISED = "Game Advertise"
    GAME_INVITATION = "Game Invitation"
    GAME_JOINED = "Game Joined"
    GAME_STARTED = "Game Started"
    GAME_CANCELLED = "Game Cancelled"
    GAME_COMPLETED = "Game Completed"
    GAME_IDLE = "Game Idle"
    GAME_INACTIVE = "Game Inactive"
    GAME_PLAYER_QUIT = "Game Player Quit"
    GAME_PLAYER_CHANGE = "Game Player Change"
    GAME_STATE_CHANGE = "Game State Change"
    GAME_PLAYER_TURN = "Game Player Turn"


@attr.s(frozen=True, repr=False)
class ProcessingError(RuntimeError):
    """Exception thrown when there is a general processing error."""

    reason = attr.ib(type=FailureReason)
    comment = attr.ib(type=Optional[str], default=None)
    handle = attr.ib(type=Optional[str], default=None)

    def __repr__(self) -> str:
        return self.comment if self.comment else self.reason.value  # type: ignore

    def __str__(self) -> str:
        return self.__repr__()


@attr.s(frozen=True)
class GamePlayer:
    """The public definition of a player within a game."""

    handle = attr.ib(type=str)
    player_color = attr.ib(type=Optional[PlayerColor])
    player_type = attr.ib(type=PlayerType)
    player_state = attr.ib(type=PlayerState)


@attr.s(frozen=True)
class RegisteredPlayer:
    """The public definition of a player registered with the system."""

    handle = attr.ib(type=str)
    registration_date = attr.ib(type=DateTime)
    last_active_date = attr.ib(type=DateTime)
    connection_state = attr.ib(type=ConnectionState)
    activity_state = attr.ib(type=ActivityState)
    player_state = attr.ib(type=PlayerState)
    game_id = attr.ib(type=Optional[str])


@attr.s(frozen=True)
class AdvertisedGame:
    """A game that has been advertised in the system."""

    game_id = attr.ib(type=str)
    name = attr.ib(type=str)
    mode = attr.ib(type=GameMode)
    advertiser_handle = attr.ib(type=str)
    players = attr.ib(type=int)
    available = attr.ib(type=int)
    visibility = attr.ib(type=Visibility)
    invited_handles = attr.ib(type=List[str])


@attr.s(frozen=True)
class GameStatePawn:
    """State of a pawn in a game."""

    color = attr.ib(type=PlayerColor)
    id = attr.ib(type=str)
    start = attr.ib(type=bool)
    home = attr.ib(type=bool)
    safe = attr.ib(type=Optional[int])
    square = attr.ib(type=Optional[int])

    @staticmethod
    def for_pawn(pawn: Pawn) -> GameStatePawn:
        """Create a GameStatePawn based on apologies.game.Pawn."""
        color = pawn.color
        index = "%s" % pawn.index
        start = pawn.position.start
        home = pawn.position.home
        safe = pawn.position.safe
        square = pawn.position.square
        return GameStatePawn(color, index, start, home, safe, square)

    @staticmethod
    def for_position(pawn: Pawn, position: Position) -> GameStatePawn:
        """Create a GameStatePawn based on apologies.game.Pawn and apologies.gamePosition."""
        color = pawn.color
        index = "%s" % pawn.index
        start = position.start
        home = position.home
        safe = position.safe
        square = position.square
        return GameStatePawn(color, index, start, home, safe, square)


@attr.s(frozen=True)
class GameStatePlayer:
    """Player in a game, when describing the state of the board."""

    color = attr.ib(type=PlayerColor)
    turns = attr.ib(type=int)
    hand = attr.ib(type=List[CardType])
    pawns = attr.ib(type=List[GameStatePawn])

    @staticmethod
    def for_player(player: Player) -> GameStatePlayer:
        """Create a GameStatePlayer based on apologies.game.Player."""
        color = player.color
        turns = player.turns
        hand = [card.cardtype for card in player.hand]
        pawns = [GameStatePawn.for_pawn(pawn) for pawn in player.pawns]
        return GameStatePlayer(color, turns, hand, pawns)


@attr.s
class GameStateHistory:
    """History for a game."""

    action = attr.ib(type=str)
    color = attr.ib(type=Optional[PlayerColor])
    timestamp = attr.ib(type=DateTime)

    @staticmethod
    def for_history(history: History) -> GameStateHistory:
        return GameStateHistory(action=history.action, color=history.color, timestamp=history.timestamp)


@attr.s(frozen=True)
class GameAction:
    """An action applied to a pawn in a game."""

    start = attr.ib(type=GameStatePawn)
    end = attr.ib(type=GameStatePawn)

    @staticmethod
    def for_action(action: Action) -> GameAction:
        """Create a GamePlayerAction based on apologies.rules.Action."""
        if action.actiontype == ActionType.MOVE_TO_START:
            # We normalize a MOVE_TO_START action to just a position change, to simplify what the client sees
            start = GameStatePawn.for_pawn(action.pawn)
            end = GameStatePawn.for_position(action.pawn, Position().move_to_start())
            return GameAction(start, end)
        else:  # action.actiontype == ActionType.MOVE_TO_POSITION
            start = GameStatePawn.for_pawn(action.pawn)
            end = GameStatePawn.for_position(action.pawn, action.position)
            return GameAction(start, end)


@attr.s(frozen=True)
class GameMove:
    """A move that may be executed as a result of a player's turn."""

    move_id = attr.ib(type=str)
    card = attr.ib(type=CardType)
    actions = attr.ib(type=List[GameAction])
    side_effects = attr.ib(type=List[GameAction])

    @staticmethod
    def for_move(move: Move) -> GameMove:
        """Create a GameMove based on apologies.rules.Move."""
        move_id = move.id
        card = move.card.cardtype
        actions = [GameAction.for_action(action) for action in move.actions]
        side_effects = [GameAction.for_action(side_effect) for side_effect in move.side_effects]
        return GameMove(move_id, card, actions, side_effects)


class Context(ABC):
    """Abstract message context."""


MAX_HANDLE = 25
"""Maximum length of a player handle."""


@attr.s(frozen=True)
class RegisterPlayerContext(Context):
    """Context for a REGISTER_PLAYER request."""

    handle = attr.ib(type=str, validator=and_(string, length(MAX_HANDLE)))


@attr.s(frozen=True)
class ReregisterPlayerContext(Context):
    """Context for a REREGISTER_PLAYER request."""

    handle = attr.ib(type=str, validator=and_(string, length(MAX_HANDLE)))


@attr.s(frozen=True)
class AdvertiseGameContext(Context):
    """Context for an ADVERTISE_GAME request."""

    name = attr.ib(type=str, validator=string)
    mode = attr.ib(type=GameMode, validator=enum(GameMode))
    players = attr.ib(type=int, validator=in_([2, 3, 4]))
    visibility = attr.ib(type=Visibility, validator=enum(Visibility))
    invited_handles = attr.ib(type=List[str], validator=stringlist)


@attr.s(frozen=True)
class JoinGameContext(Context):
    """Context for a JOIN_GAME request."""

    game_id = attr.ib(type=str, validator=string)


@attr.s(frozen=True)
class ExecuteMoveContext(Context):
    """Context for an EXECUTE_MOVE request."""

    move_id = attr.ib(type=str, validator=string)


@attr.s(frozen=True)
class SendMessageContext(Context):
    """Context for an SEND_MESSAGE request."""

    message = attr.ib(type=str, validator=string)
    recipient_handles = attr.ib(type=List[str], validator=and_(stringlist, notempty))


@attr.s(frozen=True)
class RequestFailedContext(Context):
    """Context for a REQUEST_FAILED event."""

    reason = attr.ib(type=FailureReason)
    comment = attr.ib(type=Optional[str])
    handle = attr.ib(type=Optional[str], default=None)


@attr.s(frozen=True)
class RegisteredPlayersContext(Context):
    """Context for a REGISTERED_PLAYERS event."""

    players = attr.ib(type=List[RegisteredPlayer])


@attr.s(frozen=True)
class AvailableGamesContext(Context):
    """Context for an AVAILABLE_GAMES event."""

    games = attr.ib(type=List[AdvertisedGame])


@attr.s(frozen=True)
class PlayerRegisteredContext(Context):
    """Context for a PLAYER_REGISTERED event."""

    handle = attr.ib(type=str)


@attr.s(frozen=True)
class PlayerUnregisteredContext(Context):
    """Context for a PLAYER_UNREGISTERED event."""

    handle = attr.ib(type=str)


@attr.s(frozen=True)
class PlayerIdleContext(Context):
    """Context for a PLAYER_IDLE event."""

    handle = attr.ib(type=str)


@attr.s(frozen=True)
class PlayerInactiveContext(Context):
    """Context for a PLAYER_INACTIVE event."""

    handle = attr.ib(type=str)


@attr.s(frozen=True)
class PlayerMessageReceivedContext(Context):
    """Context for a PLAYER_MESSAGE_RECEIVED event."""

    sender_handle = attr.ib(type=str)
    recipient_handles = attr.ib(type=List[str])
    message = attr.ib(type=str)


@attr.s(frozen=True)
class GameAdvertisedContext(Context):
    """Context for a GAME_ADVERTISED event."""

    game = attr.ib(type=AdvertisedGame)


@attr.s(frozen=True)
class GameInvitationContext(Context):
    """Context for a GAME_INVITATION event."""

    game = attr.ib(type=AdvertisedGame)


@attr.s(frozen=True)
class GameJoinedContext(Context):
    """Context for a GAME_JOINED event."""

    game_id = attr.ib(type=str)
    # TODO: we need the handle of the player that joined, in case multiple players share the same websocket


@attr.s(frozen=True)
class GameStartedContext(Context):
    """Context for a GAME_STARTED event."""

    game_id = attr.ib(type=str)


@attr.s(frozen=True)
class GameCancelledContext(Context):
    """Context for a GAME_CANCELLED event."""

    game_id = attr.ib(type=str)
    reason = attr.ib(type=CancelledReason)
    comment = attr.ib(type=Optional[str])


@attr.s(frozen=True)
class GameCompletedContext(Context):
    """Context for a GAME_COMPLETED event."""

    game_id = attr.ib(type=str)
    comment = attr.ib(type=Optional[str])


@attr.s(frozen=True)
class GameIdleContext(Context):
    """Context for a GAME_IDLE event."""

    game_id = attr.ib(type=str)


@attr.s(frozen=True)
class GameInactiveContext(Context):
    """Context for a GAME_INACTIVE event."""

    game_id = attr.ib(type=str)


@attr.s(frozen=True)
class GamePlayerQuitContext(Context):
    """Context for a GAME_PLAYER_LEFT event."""

    handle = attr.ib(type=str)
    game_id = attr.ib(type=str)


@attr.s(frozen=True)
class GamePlayerChangeContext(Context):
    """Context for a GAME_PLAYER_CHANGE event."""

    game_id = attr.ib(type=str)
    comment = attr.ib(type=Optional[str])
    players = attr.ib(type=List[GamePlayer])


@attr.s(frozen=True)
class GameStateChangeContext(Context):
    """Context for a GAME_STATE_CHANGE event."""

    game_id = attr.ib(type=str)
    recent_history = attr.ib(type=List[GameStateHistory])
    player = attr.ib(type=GameStatePlayer)
    opponents = attr.ib(type=List[GameStatePlayer])

    @staticmethod
    def for_context(game_id: str, view: PlayerView, history: List[History]) -> GameStateChangeContext:
        """Create a GameStateChangeContext based on apologies.game.PlayerView."""
        player = GameStatePlayer.for_player(view.player)
        recent_history = [GameStateHistory.for_history(entry) for entry in history]
        opponents = [GameStatePlayer.for_player(opponent) for opponent in view.opponents.values()]
        return GameStateChangeContext(game_id, recent_history, player, opponents)


@attr.s(frozen=True)
class GamePlayerTurnContext(Context):
    """Context for a GAME_PLAYER_TURN event."""

    handle = attr.ib(type=str)
    game_id = attr.ib(type=str)
    drawn_card = attr.ib(type=Optional[CardType])
    moves = attr.ib(type=Dict[str, GameMove])

    @staticmethod
    def for_moves(handle: str, game_id: str, moves: List[Move]) -> GamePlayerTurnContext:
        """Create a GamePlayerTurnContext based on a sequence of apologies.rules.Move."""
        cards = {move.card.cardtype for move in moves}
        drawn_card = None if len(cards) > 1 else next(iter(cards))  # if there's only one card, it's the one they drew from the deck
        converted = {move.id: GameMove.for_move(move) for move in moves}
        return GamePlayerTurnContext(handle, game_id, drawn_card, converted)


# Map from MessageType to whether player id field is allowed/required
_PLAYER_ID: Dict[MessageType, bool] = {
    MessageType.REGISTER_PLAYER: False,
    MessageType.REREGISTER_PLAYER: True,
    MessageType.UNREGISTER_PLAYER: True,
    MessageType.LIST_PLAYERS: True,
    MessageType.ADVERTISE_GAME: True,
    MessageType.LIST_AVAILABLE_GAMES: True,
    MessageType.JOIN_GAME: True,
    MessageType.QUIT_GAME: True,
    MessageType.START_GAME: True,
    MessageType.CANCEL_GAME: True,
    MessageType.EXECUTE_MOVE: True,
    MessageType.RETRIEVE_GAME_STATE: True,
    MessageType.SEND_MESSAGE: True,
    MessageType.SERVER_SHUTDOWN: False,
    MessageType.REQUEST_FAILED: False,
    MessageType.WEBSOCKET_IDLE: False,
    MessageType.WEBSOCKET_INACTIVE: False,
    MessageType.REGISTERED_PLAYERS: False,
    MessageType.AVAILABLE_GAMES: False,
    MessageType.PLAYER_REGISTERED: True,
    MessageType.PLAYER_UNREGISTERED: False,
    MessageType.PLAYER_IDLE: False,
    MessageType.PLAYER_INACTIVE: False,
    MessageType.PLAYER_MESSAGE_RECEIVED: False,
    MessageType.GAME_ADVERTISED: False,
    MessageType.GAME_INVITATION: False,
    MessageType.GAME_JOINED: False,
    MessageType.GAME_STARTED: False,
    MessageType.GAME_CANCELLED: False,
    MessageType.GAME_COMPLETED: False,
    MessageType.GAME_IDLE: False,
    MessageType.GAME_INACTIVE: False,
    MessageType.GAME_PLAYER_QUIT: False,
    MessageType.GAME_PLAYER_CHANGE: False,
    MessageType.GAME_STATE_CHANGE: False,
    MessageType.GAME_PLAYER_TURN: False,
}

# Map from MessageType to context
_CONTEXT: Dict[MessageType, Optional[Type[Context]]] = {
    MessageType.REGISTER_PLAYER: RegisterPlayerContext,
    MessageType.REREGISTER_PLAYER: ReregisterPlayerContext,
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
    MessageType.SERVER_SHUTDOWN: None,
    MessageType.REQUEST_FAILED: RequestFailedContext,
    MessageType.WEBSOCKET_IDLE: None,
    MessageType.WEBSOCKET_INACTIVE: None,
    MessageType.REGISTERED_PLAYERS: RegisteredPlayersContext,
    MessageType.AVAILABLE_GAMES: AvailableGamesContext,
    MessageType.PLAYER_REGISTERED: PlayerRegisteredContext,
    MessageType.PLAYER_UNREGISTERED: PlayerUnregisteredContext,
    MessageType.PLAYER_IDLE: PlayerIdleContext,
    MessageType.PLAYER_INACTIVE: PlayerInactiveContext,
    MessageType.PLAYER_MESSAGE_RECEIVED: PlayerMessageReceivedContext,
    MessageType.GAME_ADVERTISED: GameAdvertisedContext,
    MessageType.GAME_INVITATION: GameInvitationContext,
    MessageType.GAME_JOINED: GameJoinedContext,
    MessageType.GAME_STARTED: GameStartedContext,
    MessageType.GAME_CANCELLED: GameCancelledContext,
    MessageType.GAME_COMPLETED: GameCompletedContext,
    MessageType.GAME_IDLE: GameIdleContext,
    MessageType.GAME_INACTIVE: GameInactiveContext,
    MessageType.GAME_PLAYER_QUIT: GamePlayerQuitContext,
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
    CardType,
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
    player_id = attr.ib(type=Optional[str], default=None, repr=False)  # this is a secret, so we don't want it printed or logged
    context = attr.ib(type=Any, default=None)

    @message.validator
    def _validate_message(self, attribute: Attribute[MessageType], value: MessageType) -> None:
        if value is None or not isinstance(value, MessageType):
            raise ValueError("'%s' must be a MessageType" % attribute.name)

    @player_id.validator
    def _validate_player_id(self, _attribute: Attribute[str], value: str) -> None:
        if _PLAYER_ID[self.message]:
            if value is None:
                raise ValueError("Message type %s requires a player id" % self.message.name)
        else:
            if value is not None:
                raise ValueError("Message type %s does not allow a player id" % self.message.name)

    @context.validator
    def _validate_context(self, _attribute: Attribute[Context], value: Context) -> None:
        if _CONTEXT[self.message] is not None:
            if value is None:
                raise ValueError("Message type %s requires a context" % self.message.name)
            elif not isinstance(value, _CONTEXT[self.message]):  # type: ignore
                raise ValueError("Message type %s does not support this context" % self.message.name)
        else:
            if value is not None:
                raise ValueError("Message type %s does not allow a context" % self.message.name)

    def to_json(self) -> str:
        """Convert the request to JSON."""
        d = _CONVERTER.unstructure(self)  # pylint: disable=invalid-name
        if d["player_id"] is None:
            del d["player_id"]
        if d["context"] is None:
            del d["context"]
        return orjson.dumps(d, option=orjson.OPT_INDENT_2).decode("utf-8")  # type: ignore

    @staticmethod
    def for_json(data: str) -> Message:
        """Create a request based on JSON data."""
        d = orjson.loads(data)  # pylint: disable=invalid-name
        if "message" not in d or d["message"] is None:
            raise ValueError("Message type is required")
        try:
            message = MessageType[d["message"]]
        except KeyError:
            raise ValueError("Unknown message type: %s" % d["message"])
        if _PLAYER_ID[message]:
            if "player_id" not in d or d["player_id"] is None:
                raise ValueError("Message type %s requires a player id" % message.name)
            player_id = d["player_id"]
        else:
            if "player_id" in d and d["player_id"] is not None:
                raise ValueError("Message type %s does not allow a player id" % message.name)
            player_id = None
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
        return Message(message, player_id, context)
