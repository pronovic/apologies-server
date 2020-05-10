# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=unsubscriptable-object

"""
Shared test utilities.
"""

from unittest.mock import MagicMock

from asynctest import CoroutineMock


def mock_handler() -> MagicMock:
    """Create a mocked handler that can be locked and used as expected."""
    lock = CoroutineMock()
    handler = MagicMock()
    handler.__enter__.return_value = handler
    handler.execute_tasks = CoroutineMock()
    handler.manager = MagicMock()
    handler.manager.lock = lock
    handler.manager.lock.__aenter__ = lock
    handler.manager.lock.__aexit__ = lock
    return handler
