# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:

import sys
from typing import Any, List

from .server import main as server_main


def run_server(_argv: List[str]) -> None:
    """Start the websockets server."""
    server_main()


def _example(argv: List[str]) -> List[str]:
    """Example method."""
    return argv


def _lookup_method(method: str) -> Any:
    """Look up the method in this module with the passed-in name."""
    module = sys.modules[__name__]
    return getattr(module, "%s" % method)


def cli(script: str) -> Any:
    """
    Run the main routine for the named script.

    Args:
        script(str): Name of the script to execute
    """
    return _lookup_method(script)(sys.argv)
