# vim: set ft=python ts=4 sw=4 expandtab:

"""Scripts that are installed by Poetry in the published package."""

from apologiesserver.cli import cli


def server() -> None:
    """Target for Poetry's script configuration."""
    cli("run_server")
