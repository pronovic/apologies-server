# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import

"""
Implements a quick'n'dirty game-playing client.

This is designed to hit a significant fraction of the public interface
and prove that it seems to work for a single client using a single
websocket.  It's not intended as a stress or volume test.

This is the rough order of operations:

    - register leela and extract player id
    - list players
    - drop the websocket
    - re-register leela
    - register fry and extract player id
    - register fry and extract player id
    - list players
    - fry sends message to leela and bender
    - bender sends message to fry
    - leela player advertise 4-player public game
    - list available games
    - fry joins game
    - bender joins game
    - leela cancels game
    - fry advertises a 4-player private game, inviting leela and bender
    - leela joins game
    - bender joins game
    - bender quits game
    - leela quits game
    - fry player starts game (we get 1 "human" and 3 programmatic players)
    - game enters a loop handling game state change and game player turn events, picking a turn randomly
    
Since this demo is part of the apologiesserver source tree, it can use all of
the same interface objects.  However, the network traffic is going over the
wire (even if it is against localhost) so this is a real test of the server. 

This code looks nothing like a real event-driven application.  It just strings 
together a set of events in a mostly-realistic way to show that the network
interface works. 
"""

import asyncio
import logging
import random
from asyncio import AbstractEventLoop, Future  # pylint: disable=unused-import
from typing import List, cast

import websockets
from websockets import WebSocketClientProtocol
from apologies.engine import Move
from apologies.game import GameMode

from .interface import *
from .util import receive, send, extract

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


async def _list_games(websocket: WebSocketClientProtocol, player_id: str) -> None:
    request = Message(MessageType.LIST_AVAILABLE_GAMES, player_id=player_id)
    await send(websocket, request)
    response = await receive(websocket)
    context = cast(AvailableGamesContext, response.context)
    log.info("Available games: %s", [game.name for game in context.games])


async def _send_message(websocket: WebSocketClientProtocol, player_id: str, recipients: List[str], message: str) -> None:
    context = SendMessageContext(message=message, recipient_handles=recipients)
    request = Message(MessageType.SEND_MESSAGE, player_id=player_id, context=context)
    await send(websocket, request)
    log.info("Completed sending message '%s' to recipients %s", message, recipients)
    response = await receive(websocket)
    context = cast(PlayerMessageReceivedContext, response.context)  # type: ignore
    log.info("Received message '%s' for recipients %s", context.message, context.recipient_handles)


async def _register_public_game(websocket: WebSocketClientProtocol, player_id: str) -> str:
    name = "Public Game"
    mode = GameMode.STANDARD
    players = 4
    visibility = Visibility.PUBLIC
    invited_handles = []
    context = AdvertiseGameContext(name, mode, players, visibility, invited_handles)
    request = Message(MessageType.ADVERTISE_GAME, player_id=player_id, context=context)

    await send(websocket, request)
    response1 = await receive(websocket)
    response2 = await receive(websocket)

    for response in [response1, response2]:
        if response.message == MessageType.GAME_JOINED:
            context = cast(GameJoinedContext, response.context)  # type: ignore
            log.info("Player %s joined game %s", context.handle, context.game_id)

    for response in [response1, response2]:
        if response.message == MessageType.GAME_ADVERTISED:
            context = cast(GameAdvertisedContext, response.context)  # type: ignore
            log.info("Competed registering public game with id %s", context.game.game_id)
            return context.game.game_id


async def _register_private_game(websocket: WebSocketClientProtocol, player_id: str) -> str:
    name = "Private Game"
    mode = GameMode.STANDARD
    players = 4
    visibility = Visibility.PRIVATE
    invited_handles = ["leela", "bender"]
    context = AdvertiseGameContext(name, mode, players, visibility, invited_handles)
    request = Message(MessageType.ADVERTISE_GAME, player_id=player_id, context=context)

    await send(websocket, request)
    response1 = await receive(websocket)
    response2 = await receive(websocket)
    response3 = await receive(websocket)

    for response in [response1, response2, response3]:
        if response.message == MessageType.GAME_JOINED:
            context = cast(GameJoinedContext, response.context)  # type: ignore
            log.info("Player %s joined game %s", context.handle, context.game_id)

    for response in [response1, response2, response3]:
        if response.message == MessageType.GAME_INVITATION:
            context = cast(GameInvitationContext, response.context)  # type: ignore
            log.info("Game %s invited: %s", context.game.name, context.game.invited_handles)

    for response in [response1, response2, response3]:
        if response.message == MessageType.GAME_ADVERTISED:
            context = cast(GameAdvertisedContext, response.context)  # type: ignore
            log.info("Competed registering public game with id %s", context.game.game_id)
            return context.game.game_id


async def _join_game(websocket: WebSocketClientProtocol, player_id: str, game_id: str) -> None:
    context = JoinGameContext(game_id=game_id)
    request = Message(MessageType.JOIN_GAME, player_id=player_id, context=context)
    await send(websocket, request)
    response = await receive(websocket)
    context = cast(GameJoinedContext, response.context)  # type: ignore
    log.info("Player %s joined game %s", context.handle, context.game_id)


async def _quit_game(websocket: WebSocketClientProtocol, player_id: str) -> None:
    request = Message(MessageType.QUIT_GAME, player_id=player_id)
    await send(websocket, request)
    log.info("Player quit game")


async def _cancel_game(websocket: WebSocketClientProtocol, player_id: str) -> None:
    request = Message(MessageType.CANCEL_GAME, player_id=player_id)
    await send(websocket, request)
    response = await receive(websocket)
    context = cast(GameCancelledContext, response.context)  # type: ignore
    log.info("Game %s was cancelled for reason %s (%s)", context.game_id, context.reason, context.comment)


async def _start_game(websocket: WebSocketClientProtocol, player_id: str) -> None:
    request = Message(MessageType.START_GAME, player_id=player_id)
    await send(websocket, request)
    log.info("Started game")


async def _play_move(websocket: WebSocketClientProtocol, player_id: str, game_id: str, move: Move) -> None:
    context = ExecuteMoveContext(move_id=move.move_id)
    request = Message(MessageType.EXECUTE_MOVE, player_id=player_id, context=context)
    await send(websocket, request)
    log.info("Playing card %s for move %s", move.card.name, move.move_id)


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

        game_id = await _register_public_game(websocket, leela)
        await _list_games(websocket, leela)
        await _join_game(websocket, fry, game_id)
        await _join_game(websocket, bender, game_id)
        await _cancel_game(websocket, leela)
        await _list_games(websocket, leela)

        game_id = await _register_private_game(websocket, fry)
        await _list_games(websocket, leela)
        await _join_game(websocket, leela, game_id)
        await _join_game(websocket, bender, game_id)
        await _quit_game(websocket, bender)
        await _quit_game(websocket, leela)
        await _start_game(websocket, fry)

        async for data in websocket:
            message = extract(data)
            if message.message == MessageType.GAME_STATE_CHANGE:
                context = cast(GameStateChangeContext, message.context)
                log.info("%s", context.history)
            elif message.message == MessageType.GAME_PLAYER_TURN:
                context = cast(GamePlayerTurnContext, message.context)
                move = random.choice(list(context.moves.values()))
                await _play_move(websocket, fry, game_id, move)


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
