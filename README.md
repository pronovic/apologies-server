# Apologies Server

![](https://img.shields.io/pypi/l/apologies-server.svg)
![](https://img.shields.io/pypi/wheel/apologies-server.svg)
![](https://img.shields.io/pypi/pyversions/apologies-server.svg)
![](https://github.com/pronovic/apologies-server/workflows/Test%20Suite/badge.svg)
![](https://readthedocs.org/projects/apologies-server/badge/?version=latest&style=flat)

[Apologies Server](https://gitub.com/pronovic/apologies-server) is a [Websocket](https://en.wikipedia.org/wiki/WebSocket) server interface used to interactively play a multi-player game using the [Apologies](https://gitub.com/pronovic/apologies) library.  The Apologies library implements a game similar to the [Sorry](https://en.wikipedia.org/wiki/Sorry!_(game)) board game.

Developer documentation is found in [DEVELOPER.md](DEVELOPER.md).  See that
file for notes about how the code is structured, how to set up a development
environment, etc.  

The API and event model are discussed in [design.rst](docs/design.rst).  See
that files for information about scheduled jobs, all messages in the public
API, and what you can expect when each event is triggered.

There is a quick'n'dirty websocket client demo implemented in [demo.py](src/apologiesserver/demo.py). See
[DEVELOPER.md](DEVELOPER.md) for notes about how to run it.  

_Note:_ At present, the Apologies Server runs as a single stateful process that
maintains game state in memory.  It cannot be horizontally scaled, and there is
no option for an external data store.  There is also only limited support for
authentication and authorization - basically, any player can register any
available handle.  We do enforce resource limits (open connections, registered
users, in-progress games) to limit the amount of damage abusive clients can do.
