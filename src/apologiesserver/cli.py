# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:

import argparse
import sys
from typing import Any, List

from .config import DEFAULT_CONFIG_PATH, DEFAULT_SERVER_HOST, DEFAULT_SERVER_PORT, config, load_config
from .demo import demo
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

    args = parser.parse_args(args=argv)

    overrides = {} if not args.override else {token[0]: token[1] for token in [override.split(":") for override in args.override]}
    if args.logfile:
        overrides["logfile_path"] = args.logfile  # we want to expose this a little more explicitly in the argument list

    load_config(args.config, overrides)
    setup_logging(args.quiet, args.verbose, args.debug, config().logfile_path)

    server()


def run_demo(argv: List[str]) -> None:
    """Start the Apologies demo client."""

    parser = argparse.ArgumentParser(
        description="Start the apologies server demo client.",
        epilog="The client requires that you already have the server running.  "
        "By default, the client writes logs to stdout. If you prefer, you can "
        "specify the path to a logfile, and logs will be written there instead.  ",
    )

    parser.add_argument("--quiet", action="store_true", help="decrease log verbosity from INFO to ERROR")
    parser.add_argument("--verbose", action="store_true", help="increase log verbosity from INFO to DEBUG")
    parser.add_argument("--debug", action="store_true", help="like --verbose but also include websockets logs")
    parser.add_argument("--logfile", type=str, help="path to logfile on disk (default is stdout)")
    parser.add_argument("--host", type=str, default=DEFAULT_SERVER_HOST, help="host where the server is running")
    parser.add_argument("--port", type=int, default=DEFAULT_SERVER_PORT, help="port where the server is running on the host")

    args = parser.parse_args(args=argv)
    setup_logging(args.quiet, args.verbose, args.debug, args.logfile)
    demo(host=args.host, port=args.port)


def _example(argv: List[str]) -> List[str]:
    """Example method."""
    return argv[:]


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
    return _lookup_method(script)(argv=sys.argv[2:])
