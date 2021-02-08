# Apologies Server

[![pypi](https://img.shields.io/pypi/v/apologiesserver.svg)](https://pypi.org/project/apologiesserver/)
[![license](https://img.shields.io/pypi/l/apologiesserver.svg)](https://github.com/pronovic/apologies-server/blob/master/LICENSE)
[![wheel](https://img.shields.io/pypi/wheel/apologiesserver.svg)](https://pypi.org/project/apologiesserver/)
[![python](https://img.shields.io/pypi/pyversions/apologiesserver.svg)](https://pypi.org/project/apologiesserver/)
[![Test Suite](https://github.com/pronovic/apologies-server/workflows/Test%20Suite/badge.svg)](https://github.com/pronovic/apologies-server/actions?query=workflow%3A%22Test+Suite%22)
[![docs](https://readthedocs.org/projects/apologies-server/badge/?version=stable&style=flat)](https://apologies-server.readthedocs.io/en/stable/)
[![coverage](https://coveralls.io/repos/github/pronovic/apologies-server/badge.svg?branch=master)](https://coveralls.io/github/pronovic/apologies-server?branch=master)

[Apologies Server](https://github.com/pronovic/apologies-server) is a [Websocket](https://en.wikipedia.org/wiki/WebSocket) server interface used to interactively play a multi-player game using the [Apologies](https://github.com/pronovic/apologies) library.  The Apologies library implements a game similar to the [Sorry](https://en.wikipedia.org/wiki/Sorry!_(game)) board game.  

It was written as a learning exercise and technology demonstration effort, and serves as a complete example of how to manage a modern (circa 2020) Python project, including style checks, code formatting, integration with IntelliJ, [CI builds at GitHub](https://github.com/pronovic/apologies-server/actions), and integration with [PyPI](https://pypi.org/project/apologiesserver/) and [Read the Docs](https://apologies-server.readthedocs.io/en/stable/).  

See the [documentation](https://apologies-server.readthedocs.io/en/stable/design.html) for notes about the public interface and the event model.

As of this writing, the published PyPI project does not include a script to run
the server. The only way to run it is from the codebase, for local testing. See
the [developer](https://github.com/pronovic/apologies-server/blob/master/DEVELOPER.md#running-the-server) documentation
at GitHub for more information.

As a technology demonstration effort, the Apologies Server is fairly
simplistic.  It runs as a single stateful process that maintains game state in
memory.  It cannot be horizontally scaled, and there is no option for an
external data store.  There is also only limited support for authentication and
authorization - any player can register any handle that is not currently being
used.  We do enforce resource limits (open connections, registered users,
in-progress games) to limit the amount of damage abusive clients can do.
