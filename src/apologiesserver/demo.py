# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=wildcard-import

"""
Implements a quick'n'dirty game-playing client as a demo.
"""

import asyncio
import logging
from asyncio import AbstractEventLoop

log = logging.getLogger("apologies.demo")


# pylint: disable=unused-argument
async def _websocket_client(uri: str) -> None:
    """The asynchronous websocket client."""
    log.info("Completed starting websocket client")  # ok, it's a bit of a lie


def _run_demo(loop: AbstractEventLoop, uri: str) -> None:

    """Run the websocket demo."""

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
