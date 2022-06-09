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

The file docs/design.rst includes a detailed discussion of each request and event.
"""

from __future__ import annotations  # see: https://stackoverflow.com/a/33533514/2907667

import json
from abc import ABC
from enum import Enum
from typing import Any, Dict, List, Optional, Type

import cattrs
from apologies import Action, ActionType, CardType, GameMode, History, Move, Pawn, Player, PlayerColor, PlayerView, Position
from attr import Attribute
from attr.validators import and_, in_
from attrs import define, field, frozen
from cattrs.errors import ClassValidationError
from pendulum.datetime import DateTime
from pendulum.parser import parse

from .validator import enum, length, notempty, regex, string, stringlist

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
    OPTIMAL_MOVE = "Optimal Move"
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


@frozen(repr=False)
class ProcessingError(RuntimeError):
    """Exception thrown when there is a general processing error."""

    reason: FailureReason
    comment: Optional[str] = None
    handle: Optional[str] = None

    def __repr__(self) -> str:
        return self.comment if self.comment else self.reason.value

    def __str__(self) -> str:
        return self.__repr__()


@frozen
class GamePlayer:
    """The public definition of a player within a game."""

    handle: str
    player_color: Optional[PlayerColor]
    player_type: PlayerType
    player_state: PlayerState


@frozen
class RegisteredPlayer:
    """The public definition of a player registered with the system."""

    handle: str
    registration_date: DateTime
    last_active_date: DateTime
    connection_state: ConnectionState
    activity_state: ActivityState
    player_state: PlayerState
    game_id: Optional[str]


@frozen
class AdvertisedGame:
    """A game that has been advertised in the system."""

    game_id: str
    name: str
    mode: GameMode
    advertiser_handle: str
    players: int
    available: int
    visibility: Visibility
    invited_handles: List[str]


@frozen
class GameStatePawn:
    """State of a pawn in a game."""

    color: PlayerColor
    id: str
    start: bool
    home: bool
    safe: Optional[int]
    square: Optional[int]

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


@frozen
class GameStatePlayer:
    """Player in a game, when describing the state of the board."""

    color: PlayerColor
    turns: int
    hand: List[CardType]
    pawns: List[GameStatePawn]

    @staticmethod
    def for_player(player: Player) -> GameStatePlayer:
        """Create a GameStatePlayer based on apologies.game.Player."""
        color = player.color
        turns = player.turns
        hand = [card.cardtype for card in player.hand]
        pawns = [GameStatePawn.for_pawn(pawn) for pawn in player.pawns]
        return GameStatePlayer(color, turns, hand, pawns)


@define
class GameStateHistory:
    """History for a game."""

    action: str
    color: Optional[PlayerColor]
    card: Optional[CardType]
    timestamp: DateTime

    @staticmethod
    def for_history(history: History) -> GameStateHistory:
        return GameStateHistory(action=history.action, color=history.color, card=history.card, timestamp=history.timestamp)


@frozen
class GameAction:
    """An action applied to a pawn in a game."""

    start: GameStatePawn
    end: GameStatePawn

    @staticmethod
    def for_action(action: Action) -> GameAction:
        """Create a GamePlayerAction based on apologies.rules.Action."""
        if action.actiontype == ActionType.MOVE_TO_START:
            # We normalize a MOVE_TO_START action to just a position change, to simplify what the client sees
            start = GameStatePawn.for_pawn(action.pawn)
            end = GameStatePawn.for_position(action.pawn, Position().move_to_start())
            return GameAction(start, end)
        else:  # action.actiontype == ActionType.MOVE_TO_POSITION
            if not action.position:
                raise ValueError("Action has no associated position")
            start = GameStatePawn.for_pawn(action.pawn)
            end = GameStatePawn.for_position(action.pawn, action.position)
            return GameAction(start, end)


@frozen
class GameMove:
    """A move that may be executed as a result of a player's turn."""

    move_id: str
    card: CardType
    actions: List[GameAction]
    side_effects: List[GameAction]

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

MAX_GAME_NAME = 40
"""Maximum length of a game name."""

HANDLE_REGEX = r"[a-zA-Z0-9_-]+"
"""Regular expression that handles must match."""


@frozen
class RegisterPlayerContext(Context):
    """Context for a REGISTER_PLAYER request."""

    handle: str = field(validator=and_(string, length(MAX_HANDLE), regex(HANDLE_REGEX)))


@frozen
class ReregisterPlayerContext(Context):
    """Context for a REREGISTER_PLAYER request."""

    handle: str = field(validator=and_(string, length(MAX_HANDLE), regex(HANDLE_REGEX)))


@frozen
class AdvertiseGameContext(Context):
    """Context for an ADVERTISE_GAME request."""

    name: str = field(validator=and_(string, length(MAX_GAME_NAME)))
    mode: GameMode = field(validator=enum(GameMode))
    players: int = field(validator=in_([2, 3, 4]))
    visibility: Visibility = field(validator=enum(Visibility))
    invited_handles: List[str] = field(validator=stringlist)


@frozen
class JoinGameContext(Context):
    """Context for a JOIN_GAME request."""

    game_id: str = field(validator=string)


@frozen
class ExecuteMoveContext(Context):
    """Context for an EXECUTE_MOVE request."""

    move_id: str = field(validator=string)


@frozen
class SendMessageContext(Context):
    """Context for an SEND_MESSAGE request."""

    message: str = field(validator=string)
    recipient_handles: List[str] = field(validator=and_(stringlist, notempty))


@frozen
class RequestFailedContext(Context):
    """Context for a REQUEST_FAILED event."""

    reason: FailureReason
    comment: Optional[str]
    handle: Optional[str] = None


@frozen
class RegisteredPlayersContext(Context):
    """Context for a REGISTERED_PLAYERS event."""

    players: List[RegisteredPlayer]


@frozen
class AvailableGamesContext(Context):
    """Context for an AVAILABLE_GAMES event."""

    games: List[AdvertisedGame]


@frozen
class PlayerRegisteredContext(Context):
    """Context for a PLAYER_REGISTERED event."""

    handle: str


@frozen
class PlayerUnregisteredContext(Context):
    """Context for a PLAYER_UNREGISTERED event."""

    handle: str


@frozen
class PlayerIdleContext(Context):
    """Context for a PLAYER_IDLE event."""

    handle: str


@frozen
class PlayerInactiveContext(Context):
    """Context for a PLAYER_INACTIVE event."""

    handle: str


@frozen
class PlayerMessageReceivedContext(Context):
    """Context for a PLAYER_MESSAGE_RECEIVED event."""

    sender_handle: str
    recipient_handles: List[str]
    message: str


@frozen
class GameAdvertisedContext(Context):
    """Context for a GAME_ADVERTISED event."""

    game: AdvertisedGame


@frozen
class GameInvitationContext(Context):
    """Context for a GAME_INVITATION event."""

    game: AdvertisedGame


@frozen
class GameJoinedContext(Context):
    """Context for a GAME_JOINED event."""

    player_handle: str
    game_id: str
    name: str
    mode: GameMode
    advertiser_handle: str


@frozen
class GameStartedContext(Context):
    """Context for a GAME_STARTED event."""

    game_id: str


@frozen
class GameCancelledContext(Context):
    """Context for a GAME_CANCELLED event."""

    game_id: str
    reason: CancelledReason
    comment: Optional[str]


@frozen
class GameCompletedContext(Context):
    """Context for a GAME_COMPLETED event."""

    game_id: str
    winner: str
    comment: str


@frozen
class GameIdleContext(Context):
    """Context for a GAME_IDLE event."""

    game_id: str


@frozen
class GameInactiveContext(Context):
    """Context for a GAME_INACTIVE event."""

    game_id: str


@frozen
class GamePlayerQuitContext(Context):
    """Context for a GAME_PLAYER_LEFT event."""

    handle: str
    game_id: str


@frozen
class GamePlayerChangeContext(Context):
    """Context for a GAME_PLAYER_CHANGE event."""

    game_id: str
    comment: Optional[str]
    players: List[GamePlayer]


@frozen
class GameStateChangeContext(Context):
    """Context for a GAME_STATE_CHANGE event."""

    game_id: str
    recent_history: List[GameStateHistory]
    player: GameStatePlayer
    opponents: List[GameStatePlayer]

    @staticmethod
    def for_context(game_id: str, view: PlayerView, history: List[History]) -> GameStateChangeContext:
        """Create a GameStateChangeContext based on apologies.game.PlayerView."""
        player = GameStatePlayer.for_player(view.player)
        recent_history = [GameStateHistory.for_history(entry) for entry in history]
        opponents = [GameStatePlayer.for_player(opponent) for opponent in view.opponents.values()]
        return GameStateChangeContext(game_id=game_id, recent_history=recent_history, player=player, opponents=opponents)


@frozen
class GamePlayerTurnContext(Context):
    """Context for a GAME_PLAYER_TURN event."""

    handle: str
    game_id: str
    drawn_card: Optional[CardType]
    moves: Dict[str, GameMove]

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
    MessageType.OPTIMAL_MOVE: True,
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
    MessageType.OPTIMAL_MOVE: None,
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


class _CattrConverter(cattrs.GenConverter):
    """
    Cattr converter for requests and events, to standardize conversion of dates and enumerations.
    """

    def __init__(self) -> None:
        super().__init__()
        self.register_unstructure_hook(DateTime, lambda value: value.format(_DATE_FORMAT) if value else None)  # type: ignore
        self.register_structure_hook(DateTime, lambda value, _: parse(value) if value else None)
        for element in _ENUMS:
            self.register_unstructure_hook(element, lambda value: value.name if value else None)  # type: ignore
            self.register_structure_hook(element, lambda value, _, e=element: e[value] if value else None)  # type: ignore


# Cattr converter used to serialize and deserialize requests and responses
_CONVERTER = _CattrConverter()


# noinspection PyTypeChecker
@frozen
class Message:
    """A message that is part of the public interface, either a client request or a published event."""

    message: MessageType = field()
    player_id: Optional[str] = field(default=None, repr=False)  # this is a secret, so we don't want it printed or logged
    context: Any = field(default=None)

    @message.validator
    def _validate_message(self, attribute: Attribute[MessageType], value: MessageType) -> None:
        if value is None or not isinstance(value, MessageType):
            raise ValueError("'%s' must be a MessageType" % attribute.name)

    # noinspection PyUnresolvedReferences
    @player_id.validator
    def _validate_player_id(self, _attribute: Attribute[str], value: str) -> None:
        if _PLAYER_ID[self.message]:
            if value is None:
                raise ValueError("Message type %s requires a player id" % self.message.name)
        else:
            if value is not None:
                raise ValueError("Message type %s does not allow a player id" % self.message.name)

    # noinspection PyTypeHints
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
        d["context"] = _CONVERTER.unstructure(self.context)
        if d["player_id"] is None:
            del d["player_id"]
        if d["context"] is None:
            del d["context"]
        return json.dumps(d, indent="  ")

    @staticmethod
    def for_json(data: str) -> Message:  # pylint: disable=too-many-branches:
        """Create a request based on JSON data."""
        d = json.loads(data)  # pylint: disable=invalid-name
        if "message" not in d or d["message"] is None:
            raise ValueError("Message type is required")
        try:
            message = MessageType[d["message"]]
        except KeyError as e:
            raise ValueError("Unknown message type: %s" % d["message"]) from e
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
                context = _CONVERTER.structure(d["context"], _CONTEXT[message])  # type: ignore
            except ClassValidationError as e:
                # Unfortunately, we can't always distinguish between all different kinds of bad
                # input.  In particular, it's sometimes difficult to tell apart a single bad field
                # in a valid context from a context of the wrong type.  We used to be able to
                # distinguish more cases when using cattrs.Converter, but now that we need
                # catts.GenConverter, we're stuck with less-useful error messages in some cases.
                value_errors = [c for c in e.exceptions if isinstance(c, ValueError)]
                key_errors = [c for c in e.exceptions if isinstance(c, KeyError)]
                if value_errors:
                    raise value_errors[0]
                elif key_errors:
                    raise ValueError("Invalid value %s" % str(key_errors[0])) from e
                else:
                    raise ValueError("Message type %s does not support this context" % message.name, e) from e
        return Message(message, player_id, context)
