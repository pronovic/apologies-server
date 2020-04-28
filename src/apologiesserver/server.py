# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:

import asyncio
import json
import logging
from typing import Awaitable

import websockets
from websockets import WebSocketServerProtocol

import time
import asyncio
import signal
import logging
from asyncio import AbstractEventLoop

# logging.basicConfig()

import logging

logger = logging.getLogger("websockets")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

# # Signals that are handled to cause shutdown
_SHUTDOWN_SIGNALS = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)


STATE = {"value": 0}

USERS = set()


def state_event() -> str:
    return json.dumps({"type": "state", **STATE})


def users_event() -> str:
    return json.dumps({"type": "users", "count": len(USERS)})


async def notify_state():
    print("notify_state()")
    if USERS:  # asyncio.wait doesn't accept an empty list
        message = state_event()
        print("   message: %s" % message)
        await asyncio.wait([user.send(message) for user in USERS])


async def notify_users():
    print("notify_users()")
    if USERS:  # asyncio.wait doesn't accept an empty list
        message = users_event()
        print("   message: %s" % message)
        await asyncio.wait([user.send(message) for user in USERS])


async def register(websocket: WebSocketServerProtocol):
    print("Got register event for: %s" % websocket)
    USERS.add(websocket)
    await notify_users()


async def unregister(websocket: WebSocketServerProtocol):
    print("Got unregister event for: %s" % websocket)
    USERS.remove(websocket)
    await notify_users()


async def apologies(websocket: WebSocketServerProtocol, path: str):
    # This method seems to be invoked once for each client that connects.
    # I guess it's the main processing loop for a client?
    print("In apologies() for %s" % websocket)
    # register(websocket) sends user_event() to websocket
    await register(websocket)
    print("After register() for %s" % websocket)
    try:
        print("Now at websocket.send(state_event()) for %s" % websocket)
        await websocket.send(state_event())
        print("Now after websocket.send(state_event()) for %s" % websocket)
        async for message in websocket:
            # This appears to effectively be a loop, even though it doesn't look
            # like it.  We stay in this block, executing the code below once
            # for every message that is received. This goes on forever, until
            # the finally block detects that the client has gone away.  So
            # this block effectively needs to check all of the allowed messages
            # and reject anything else.  It looks like there is no equivalent
            # of HTTP status for the response - there's either data or there
            # isn't.  Everything operates on the data.  It appears that we do
            # not necessarily need to return a response for an event.  It's all
            # asynchronous, so the client isn't "expecting" anything.  This is
            # going to require a whole new way of thinking about how code is
            # structured.
            print("Within async for message in websocket for %s" % websocket)
            data = json.loads(message)
            print("Data for %s: %s" % (websocket, data))
            if data["action"] == "minus":
                STATE["value"] -= 1
                await notify_state()
            elif data["action"] == "plus":
                STATE["value"] += 1
                await notify_state()
            else:
                logging.error("unsupported event: {}", data)
    finally:
        print("Now unregistering: %s" % websocket)
        await unregister(websocket)


import time


async def hello(s):
    print("hello {} ({:.4f})".format(s, time.time()))
    time.sleep(0.3)


# import time

# # See: https://stackoverflow.com/a/28034554/2907667
# async def do_every(period, f, *args) -> None:
#     """
#     Execute a function periodically.
#
#     Args:
#         period: A period as passed to time.sleep(), fractional seconds
#         f: Function to execute
#         *args: Arguments to pass to f() when executed
#     """
#     def g_tick():
#         t = time.time()
#         count = 0
#         while True:
#             count += 1
#             yield max(t + count * period - time.time(), 0)
#
#     g = g_tick()
#     while True:
#         await asyncio.sleep(next(g))
#         f(*args)

# async def _run_task(period, f, *args) -> None:
#     """Run a task periodically."""
#     # See also: https://stackoverflow.com/a/28034554/2907667
#     def g_tick():
#         t = time.time()
#         count = 0
#         while True:
#             count += 1
#             yield max(t + count * period - time.time(), 0)
#
#     g = g_tick()
#     while True:
#         await asyncio.sleep(next(g))
#         f(*args)
#
# from threading import Thread
#
# def _start(loop):
#     asyncio.set_event_loop(loop)
#     loop.run_forever()


# def main():
# try:
# new_loop = asyncio.new_event_loop()
# t = Thread(target=_start, args=(new_loop,))
# t.start()
# # asyncio.run_coroutine_threadsafe(do_every(1, hello, "foo"), new_loop)
# asyncio.run_coroutine_threadsafe(_run_task(1, hello, "foo"), new_loop)

# setup_signal_handlers(asyncio.get_event_loop())
#
# start_scheduler()
# schedule_periodic_task(1, hello, "foo")

# print("Server started")
# start_server = websockets.serve(apologies, "localhost", 8765)
# asyncio.get_event_loop().run_until_complete(start_server)
# asyncio.get_event_loop().run_forever()
# except KeyboardInterrupt:  # TODO: need some signal setup here so we can shutdown gracefully
#     print("Server completed")

import asyncio
from datetime import datetime

from periodic import Periodic


async def task1():
    p = Periodic(1, hello, "foo")
    await p.start()


async def task2():
    p = Periodic(2, hello, "bar")
    await p.start()


async def apologies_server(stop):
    async with websockets.serve(apologies, "localhost", 8765):
        await stop


def main():
    loop = asyncio.get_event_loop()
    stop = loop.create_future()
    for s in _SHUTDOWN_SIGNALS:
        loop.add_signal_handler(s, stop.set_result, None)
    loop.create_task(task1())
    loop.create_task(task2())
    server = websockets.serve(apologies, "localhost", 8765)
    loop.run_until_complete(apologies_server(stop))
    loop.stop()
    loop.close()


if __name__ == "__main__":
    main()
