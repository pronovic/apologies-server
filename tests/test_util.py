# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:

import os

import pytest
from asynctest import CoroutineMock
from asynctest import MagicMock as AsyncMock

from apologiesserver.interface import Message, MessageType
from apologiesserver.util import close, homedir, mask, receive, send, setup_logging


class TestUtil:
    """
    Unit tests for utilities.
    """

    def test_homedir(self):
        assert homedir() == os.path.expanduser("~")  # different way to get same value

    @pytest.mark.asyncio
    async def test_close(self):
        websocket = AsyncMock()
        websocket.close = CoroutineMock()
        await close(websocket)
        websocket.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_empty(self):
        message = ""
        websocket = AsyncMock()
        websocket.send = CoroutineMock()
        await send(websocket, message)
        websocket.send.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_send_string(self):
        message = "json"
        websocket = AsyncMock()
        websocket.send = CoroutineMock()
        await send(websocket, message)
        websocket.send.assert_awaited_once_with(message)

    @pytest.mark.asyncio
    async def test_send_message(self):
        message = Message(MessageType.WEBSOCKET_IDLE)
        websocket = AsyncMock()
        websocket.send = CoroutineMock()
        await send(websocket, message)
        websocket.send.assert_awaited_once_with(message.to_json())

    @pytest.mark.asyncio
    async def test_receive_no_timeout(self):
        message = Message(MessageType.WEBSOCKET_INACTIVE)
        data = message.to_json()
        websocket = AsyncMock()
        websocket.recv = CoroutineMock()
        websocket.recv.return_value = data
        assert await receive(websocket, timeout_sec=None) == message

    @pytest.mark.asyncio
    async def test_receive_with_timeout(self):
        message = Message(MessageType.WEBSOCKET_INACTIVE)
        data = message.to_json()
        websocket = AsyncMock()
        websocket.recv = CoroutineMock()
        websocket.recv.return_value = data
        assert await receive(websocket, timeout_sec=3) == message

    def test_mask(self):
        assert mask(None) == ""
        assert mask("") == ""
        assert mask(b"") == ""
        assert mask("hello") == "hello"
        assert mask(b"hello") == "hello"

        assert (
            mask(
                """
        {
          "player_id": null,
        }
        """
            )
            == """
        {
          "player_id": null,
        }
        """
        )

        assert (
            mask(
                """
        {
          "player_id": "",
        }
        """
            )
            == """
        {
          "player_id": "",
        }
        """
        )

        assert (
            mask(
                """
        {
          "player_id": "id",
        }
        """
            )
            == """
        {
          "player_id": "<masked>",
        }
        """
        )

        assert (
            mask(
                """
            {
                 "player_id"    :     "id"  ,
            }
            """
            )
            == """
            {
                 "player_id": "<masked>"  ,
            }
            """
        )

    def test_setup_logging(self):
        setup_logging(quiet=True, verbose=False, debug=False)  # just confirm that it runs
        setup_logging(quiet=False, verbose=True, debug=False)  # just confirm that it runs
        setup_logging(quiet=False, verbose=False, debug=True)  # just confirm that it runs
