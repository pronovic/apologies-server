# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=redefined-outer-name,wildcard-import

from unittest.mock import MagicMock

import pytest
from asynctest import CoroutineMock
from asynctest import MagicMock as AsyncMock
from asynctest import patch

from apologiesserver.event import EventHandler, RequestContext, TaskQueue
from apologiesserver.interface import *


class TestTaskQueue:
    """
    Test the TaskQueue class.
    """

    def test_disconnect(self):
        socket1 = MagicMock()
        socket2 = MagicMock()

        queue = TaskQueue()
        assert queue.disconnects == set()

        queue.disconnect(None)
        assert queue.disconnects == set()

        queue.disconnect(socket1)
        assert queue.disconnects == {socket1}

        queue.disconnect(socket2)
        assert queue.disconnects == {socket1, socket2}

        queue.disconnect(socket1)
        assert queue.disconnects == {socket1, socket2}

        queue.clear()
        assert queue.disconnects == set()

    def test_message(self):
        socket1 = MagicMock()
        socket2 = MagicMock()
        socket3 = MagicMock()

        message1 = MagicMock()
        message1.to_json.return_value = "json1"

        message2 = MagicMock()
        message2.to_json.return_value = "json2"

        message3 = MagicMock()
        message3.to_json.return_value = "json3"

        player = MagicMock(websocket=socket2)

        queue = TaskQueue()
        assert queue.messages == []

        queue.message(message1, websockets=None, players=None)
        assert queue.messages == []

        queue.message(message1, websockets=[], players=[])
        assert queue.messages == []

        queue.message(message1, websockets=[socket1])
        assert queue.messages == [("json1", socket1)]

        queue.message(message2, players=[player])
        assert queue.messages == [("json1", socket1), ("json2", socket2)]

        queue.message(message3, websockets=[socket1, socket3], players=[player])
        assert queue.messages == [
            ("json1", socket1),
            ("json2", socket2),
            ("json3", socket1),
            ("json3", socket3),
            ("json3", socket2),
        ]

        queue.clear()
        assert queue.messages == []

    @pytest.mark.asyncio
    @patch("apologiesserver.event.asyncio")
    async def test_execute_empty(self, stub):
        stub.wait = CoroutineMock()
        queue = TaskQueue()
        await queue.execute()
        stub.wait.assert_not_awaited()  # wait() doesn't accept an empty list, so we just don't call it

    @pytest.mark.asyncio
    @patch("apologiesserver.event.asyncio")
    async def test_execute(self, stub):
        stub.wait = CoroutineMock()

        socket1 = MagicMock()
        socket1.close = MagicMock()
        socket1.close.return_value = "1"

        socket2 = MagicMock()
        socket2.send = MagicMock()
        socket2.send.return_value = "2"

        socket3 = MagicMock()
        socket3.send = MagicMock()
        socket3.send.return_value = "3"

        message1 = MagicMock()
        message1.to_json.return_value = "json1"

        message2 = MagicMock()
        message2.to_json.return_value = "json2"

        queue = TaskQueue()
        queue.disconnect(socket1)
        queue.message(message1, websockets=[socket1])  # will be ignored because socket is disconnected
        queue.message(message2, websockets=[socket2, socket3])
        await queue.execute()

        expected = [
            "1",
            "2",
            "3",
        ]  # this is kind of hokey, since they're really coroutines, but it proves what we need
        stub.wait.assert_awaited_once_with(expected)
        socket1.close.assert_called_once()
        socket2.send.assert_called_once_with("json2")
        socket3.send.assert_called_once_with("json2")


class TestEventHandler:
    """
    Test the basic EventHandler functionality.
    """


class TestTaskMethods:
    """
    Test the task-related methods on EventHandler.
    """


class TestRequestMethods:
    """
    Test the request-related methods on EventHandler.
    """


class TestEventMethods:
    """
    Test the event-related methods on EventHandler.
    """
