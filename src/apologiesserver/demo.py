# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import

"""
Implements a quick'n'dirty game-playing client.

This is designed to hit a significant fraction of the public interface
and prove that it seems to work for a single client using a single
websocket.  It's not intended as a stress or volume test.

This is the rough order of operations:

    - register 1st player and extract player id
    - list players
    - drop the websocket
    - re-register 1st player
    - register 2nd player and extract player id
    - register 3rd player and extract player id
    - list players
    - 1st player sends message to 2nd player
    - 2nd player sends message to 1st player and 3rd player
    - 1st player advertise 4-player public game
    - players list available games
    - 2nd player joins game
    - 3rd player joins game
    - 1st player cancels game
    - 2nd player advertises a 4-player private game, inviting 1st player
    - 1st player joins game
    - 3rd player joins game
    - 3rd player unregisters
    - 1st player quits
    - 2nd player starts game (we get 1 "human" and 3 programmatic players)
    - game enters a loop handling game state change and game player turn events, picking a turn randomly
    
Since this demo is part of the apologiesserver source tree, it
can use all of the same interface objects.  However, the network
traffic is going over the wire (even if it is against localhost)
so this is a real test of the server. 
"""

import asyncio
import logging
from asyncio import AbstractEventLoop, Future  # pylint: disable=unused-import
from typing import List, cast

import websockets
from websockets import WebSocketClientProtocol

from .interface import *
from .util import receive, send

log = logging.getLogger("apologies.demo")


async def _register(websocket: WebSocketClientProtocol, handle: str) -> str:
    context = RegisterPlayerContext(handle=handle)
    request = Message(MessageType.REGISTER_PLAYER, context=context)
    await send(websocket, request)
    response = await receive(websocket)
    log.info("Completed registering handle=%s, got player_id=%s", handle, response.player_id)
    return response.player_id  # type: ignore


async def _reregister(websocket: WebSocketClientProtocol, player_id: str) -> str:
    request = Message(MessageType.REREGISTER_PLAYER, player_id=player_id)
    await send(websocket, request)
    response = await receive(websocket)
    log.info("Completed re-registering player_id=%s", response.player_id)
    return response.player_id  # type: ignore


async def _list_players(websocket: WebSocketClientProtocol, player_id: str) -> None:
    request = Message(MessageType.LIST_PLAYERS, player_id=player_id)
    await send(websocket, request)
    response = await receive(websocket)
    context = cast(RegisteredPlayersContext, response.context)
    log.info("Current players: %s", [player.handle for player in context.players])


async def _send_message(websocket: WebSocketClientProtocol, player_id: str, recipients: List[str], message: str) -> None:
    context = SendMessageContext(message=message, recipient_handles=recipients)
    request = Message(MessageType.SEND_MESSAGE, player_id=player_id, context=context)
    await send(websocket, request)
    log.info("Completed sending message '%s' to recipients %s", message, recipients)
    response = await receive(websocket)
    context = cast(PlayerMessageReceivedContext, response.context)  # type: ignore
    log.info("Received message '%s' for recipients %s", context.message, context.recipient_handles)


async def _websocket_client(uri: str) -> None:
    log.info("Completed starting websocket client")  # ok, it's a bit of a lie

    async with websockets.connect(uri=uri) as websocket:
        leela = await _register(websocket, "leela")
        await _list_players(websocket, leela)

    async with websockets.connect(uri=uri) as websocket:
        try:
            await _register(websocket, "leela")
            log.error("Expected duplicate user error?")
        except ProcessingError:
            pass

        leela = await _reregister(websocket, leela)
        fry = await _register(websocket, "fry")
        bender = await _register(websocket, "bender")

        await _list_players(websocket, leela)

        await _send_message(websocket, fry, ["leela", "bender"], "When is dinner?")
        await _send_message(websocket, bender, ["fry"], "It's you, meatbag!")


def _run_demo(loop: AbstractEventLoop, uri: str) -> None:

    """Run the websocket demo, which opens and closes several websockets."""

    loop.run_until_complete(_websocket_client(uri=uri))
    loop.stop()
    loop.close()


def demo(host: str, port: int) -> None:
    """Run the demo."""
    uri = "ws://%s:%d" % (host, port)
    log.info("Demo client started against %s", uri)
    loop = asyncio.get_event_loop()
    _run_demo(loop, uri)
    log.info("Demo client finished")
