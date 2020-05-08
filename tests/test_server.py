# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:

from unittest.mock import MagicMock

import pytest
from websockets.http import Headers

from apologiesserver.interface import ProcessingError
from apologiesserver.server import _parse_authorization


class TestFunctions:
    """
    Test Python functions.
    """

    def test_parse_authorization_empty(self):
        headers = Headers()
        headers["Authorization"] = "bogus"
        websocket = MagicMock(request_headers=headers)
        with pytest.raises(ProcessingError, match=r"Missing or invalid authorization header"):
            _parse_authorization(websocket)

    def test_parse_authorization_invalid(self):
        headers = Headers()
        headers["Authorization"] = "bogus"
        websocket = MagicMock(request_headers=headers)
        with pytest.raises(ProcessingError, match=r"Missing or invalid authorization header"):
            _parse_authorization(websocket)

    def test_parse_authorization_valid_upper(self):
        headers = Headers()
        headers["AUTHORIZATION"] = "PLAYER abcde"
        websocket = MagicMock(request_headers=headers)
        assert _parse_authorization(websocket) == "abcde"

    def test_parse_authorization_valid_lower(self):
        headers = Headers()
        headers["authorization"] = "player abcde"
        websocket = MagicMock(request_headers=headers)
        assert _parse_authorization(websocket) == "abcde"

    def test_parse_authorization_mixed(self):
        headers = Headers()
        headers["Authorization"] = "Player abcde"
        websocket = MagicMock(request_headers=headers)
        assert _parse_authorization(websocket) == "abcde"

    def test_parse_authorization_whitespace(self):
        headers = Headers()
        headers["authorization"] = "  Player    abcde    "
        websocket = MagicMock(request_headers=headers)
        assert _parse_authorization(websocket) == "abcde"


class TestCoroutines:
    """
    Test Python coroutines.
    """

    def test_parse_authorization(self):
        pass
