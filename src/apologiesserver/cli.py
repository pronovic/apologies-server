# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:

# TODO: should be ok to start unit testing this, I think the structure is final

import argparse
import sys
from typing import Any, List

from .config import DEFAULT_CONFIG_PATH, config, load_config
from .server import server
from .util import setup_logging


def run_server(argv: List[str]) -> None:
    """Start the Apologies server."""

    parser = argparse.ArgumentParser(
        description="Start the apologies server and let it run forever.",
        epilog="By default, the server writes logs to stdout. If you prefer, you can "
        "specify the path to a logfile, and logs will be written there instead.  "
        'The default configuration file is "%s".  '
        "If the default configuration file is not found, default values will be set.  "
        "If you override the default config file, it must exist.  "
        'You may override any individual config parameter with "--override param:value".' % DEFAULT_CONFIG_PATH,
    )

    parser.add_argument("--quiet", action="store_true", help="decrease log verbosity from INFO to ERROR")
    parser.add_argument("--verbose", action="store_true", help="increase log verbosity from INFO to DEBUG")
    parser.add_argument("--debug", action="store_true", help="like --verbose but also include websockets logs")
    parser.add_argument("--config", type=str, help="path to configuration on disk")
    parser.add_argument("--logfile", type=str, help="path to logfile on disk (default is stdout)")
    parser.add_argument("--override", type=str, action="append", help='override a config parameter as "param:value"')

    args = parser.parse_args(args=argv[2:])

    overrides = {} if not args.override else {token[0]: token[1] for token in [override.split(":") for override in args.override]}
    if args.logfile:
        overrides["logfilePath"] = args.logfile  # we want to expose this a little more explicitly in the argument list

    load_config(args.config, overrides)
    setup_logging(args.quiet, args.verbose, args.debug, config().logfile_path)

    server()


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
