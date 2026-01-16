import random
import string
from unittest.mock import AsyncMock, MagicMock

from pendulum.datetime import DateTime
from pendulum.parser import parse


def coroutine_mock() -> AsyncMock:
    # This replaces asynctest's CoroutineMock, which is what I originally used when writing
    # this code.  Unfortunately, even when I was writing this back in 2020, asynctest had
    # effectively been abandoned, and I didn't realize that.  It doesn't work with Python
    # 3.11 or later.
    #
    # Source: https://github.com/openwallet-foundation/acapy/blob/main/acapy_agent/tests/mock.py
    # See also: https://github.com/openwallet-foundation/acapy/pull/2566
    return AsyncMock(return_value=MagicMock())


def random_string(length: int = 10) -> str:
    chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
    return "".join([random.choice(chars) for _ in range(length)])


# noinspection PyTypeChecker
def to_date(date: str) -> DateTime:
    # This function seems to have the wrong type hint
    return parse(date)  # type: ignore


def mock_handler() -> MagicMock:
    """Create a mocked handler that can be locked and used as expected."""
    lock = coroutine_mock()
    handler = MagicMock()
    handler.__enter__.return_value = handler
    handler.execute_tasks = coroutine_mock()
    handler.manager = MagicMock()
    handler.manager.lock = lock
    handler.manager.lock.__aenter__ = lock
    handler.manager.lock.__aexit__ = lock
    return handler
