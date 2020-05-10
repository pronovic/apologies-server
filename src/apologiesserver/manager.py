# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import

"""
State manager.

Python's asyncio is primarily meant for use in single-threaded code, but there is still
concurrent execution happening any time we hit a yield from or await.

We want to minimize the risk of unexpected behavior when there are conflicting requests.
For instance, if we simultaneously get a request to start a game and to quit a game, we
want to make sure that one operation completes entirely before the next one starts.  This
means that we need thread synchronization whenever state is updated.

I've chosen to synchronize all state upate operations behind a single transaction boundary
(a single lock).  This is easier to follow and easier to write (correctly) than tracking
individual locks at a more granular level, like at the player or the game level.  The
state will never be locked for all that long, because state update operations are all done
in-memory and are quite fast.  The slow stuff like network requests all happen outside the
lock, whether we're processing a request or executing a scheduled task.

The design would be different if we were using a database to save state, but this seems
like the best compromise for the simple in-memory design that we're using now.

None of the objects defined in this module are thread-safe, or even thread-aware.  There
are no asynchronous methods or await calls.  Instead, the transaction boundary is handled
at the level of the module.  This simplifies the implementation and avoids confusion.
"""

import asyncio
from typing import List, Tuple

import attr
from websockets import WebSocketServerProtocol

from .interface import *


@attr.s
class MessageQueue:

    """A queue of messages to be sent."""

    messages = attr.ib(type=List[Tuple[Message, WebSocketServerProtocol]])

    @messages.default
    def _messages_default(self) -> List[Tuple[Message, WebSocketServerProtocol]]:
        return []

    def add(self, message: Message, websockets: List[WebSocketServerProtocol]) -> None:
        """Enqueue a message to one or more destination websockets."""
        self.messages.extend([(message, websocket) for websocket in websockets])

    async def send(self) -> None:
        """Send all messages in the queue."""
        await asyncio.wait([websocket.send(message.to_json()) for message, websocket in self.messages])


# TODO: remove pylint stuff once implemented
# pylint: disable=unused-argument
@attr.s
class StateManager:

    """Manages system state."""

    def handle_request(self, message: Message, websocket: WebSocketServerProtocol) -> MessageQueue:
        """Handle a message received on a websocket."""
        return MessageQueue()

    def handle_idle_players(self, idle_thresh_min: int, inactive_thresh_min: int) -> MessageQueue:
        """Handle the idle player check."""
        return MessageQueue()

    def handle_idle_games(self, idle_thresh_min: int, inactive_thresh_min: int) -> MessageQueue:
        """Handle idle games."""
        return MessageQueue()

    def handle_obsolete_games(self, retention_thresh_min: int) -> MessageQueue:
        """Handle obsolete games."""
        return MessageQueue()


_LOCK = asyncio.Lock()
_STATE_MANAGER = StateManager()

# noinspection PyBroadException
async def handle_exception(exception: Exception, websocket: WebSocketServerProtocol) -> None:
    """Handle an exception by sending a request failed event."""
    try:
        raise exception
    except ProcessingError as e:
        context = RequestFailedContext(e.reason, e.comment if e.comment else e.reason.value)
    except ValueError as e:
        context = RequestFailedContext(FailureReason.INVALID_REQUEST, str(e))
    except Exception as e:  # pylint: disable=broad-except
        context = RequestFailedContext(FailureReason.INTERNAL_ERROR, FailureReason.INTERNAL_ERROR.value)
    message = Message(MessageType.REQUEST_FAILED, context)
    await websocket.send(message.to_json())


async def handle_shutdown() -> MessageQueue:
    """Handle a disconnected websocket."""


async def handle_disconnect(websocket: WebSocketServerProtocol) -> None:
    """Handle a disconnected websocket."""


async def handle_message(message: Message, websocket: WebSocketServerProtocol) -> MessageQueue:
    """Handle a message received on a websocket by dispatching to the state manager."""
    with _LOCK:
        return _STATE_MANAGER.handle_request(message, websocket)


async def handle_idle_players(idle_thresh_min: int, inactive_thresh_min: int) -> MessageQueue:
    """Handle the idle player check by dispatching to the state manager."""
    with _LOCK:
        return _STATE_MANAGER.handle_idle_players(idle_thresh_min, inactive_thresh_min)


async def handle_idle_games(idle_thresh_min: int, inactive_thresh_min: int) -> MessageQueue:
    """Handle idle games by dispatching to the state manager."""
    with _LOCK:
        return _STATE_MANAGER.handle_idle_games(idle_thresh_min, inactive_thresh_min)


async def handle_obsolete_games(retention_thresh_min: int) -> MessageQueue:
    """Handle obsolete games by dispatching to the state manager."""
    with _LOCK:
        return _STATE_MANAGER.handle_obsolete_games(retention_thresh_min)
