# Apologies Server

![](https://img.shields.io/pypi/l/apologiesserver.svg)
![](https://img.shields.io/pypi/wheel/apologiesserver.svg)
![](https://img.shields.io/pypi/pyversions/apologiesserver.svg)
![](https://github.com/pronovic/apologies-server/workflows/Test%20Suite/badge.svg)
![](https://readthedocs.org/projects/apologies-server/badge/?version=latest&style=flat)

[Apologies Server](https://github.com/pronovic/apologies-server) is a [Websocket](https://en.wikipedia.org/wiki/WebSocket) server interface used to interactively play a multi-player game using the [Apologies](https://github.com/pronovic/apologies) library.  The Apologies library implements a game similar to the [Sorry](https://en.wikipedia.org/wiki/Sorry!_(game)) board game.

It was written as a learning exercise and technology demonstration effort, and serves as a complete example of how to manage a modern (circa 2020) Python project, including style checks, code formatting, integration with IntelliJ, [CI builds at GitHub](https://github.com/pronovic/apologies-server/actions), and integration with [PyPI](https://pypi.org/project/apologiesserver/) and [Read the Docs](https://apologies-server.readthedocs.io/en/latest/).  

Developer documentation is found in [DEVELOPER.md](DEVELOPER.md).  See that
file for notes about how the code is structured, how to set up a development
environment, etc.  

The API and event model are discussed in [design.rst](docs/design.rst).  See
that file for information about scheduled jobs, all messages in the public
API, and what you can expect when each event is triggered.

There is a quick'n'dirty websocket client demo implemented in [demo.py](src/apologiesserver/demo.py). See
[DEVELOPER.md](https://github.com/pronovic/apologies-server/blob/master/DEVELOPER.md#running-the-demo) for notes about how to run it.  

As of this writing, the published PyPI project does not include a script to run
the server. The only way to run it is from the codebase, for local testing. See
[DEVELOPER.md](https://github.com/pronovic/apologies-server/blob/master/DEVELOPER.md#running-the-server) for more information.

As a technology demonstration effort, the Apologies Server is fairly
simplistic.  It runs as a single stateful process that maintains game state in
memory.  It cannot be horizontally scaled, and there is no option for an
external data store.  There is also only limited support for authentication and
authorization - any player can register any handle that is not currently being
used.  We do enforce resource limits (open connections, registered users,
in-progress games) to limit the amount of damage abusive clients can do.
