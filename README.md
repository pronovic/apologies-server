# Apologies Server

![](https://img.shields.io/pypi/l/apologies-server.svg)
![](https://img.shields.io/pypi/wheel/apologies-server.svg)
![](https://img.shields.io/pypi/pyversions/apologies-server.svg)
![](https://github.com/pronovic/apologies-server/workflows/Test%20Suite/badge.svg)

[Apologies Server](https://gitub.com/pronovic/apologies-server) is a [Websocket](https://en.wikipedia.org/wiki/WebSocket) server interface used to interactively play a multi-player game using the [Apologies](https://gitub.com/pronovic/apologies) library.  The Apologies library implements a game similar to the [Sorry](https://en.wikipedia.org/wiki/Sorry!_(game)) board game.

Developer documentation is found in [DEVELOPER.md](DEVELOPER.md).  See that
file for notes about how the code is structured, how to set up a development
environment, etc.

_Note_: This library is alpha quality.  It is under active development and
the interface can be expected to change over time.

_Note:_ At present, the Apologies Server runs as a single stateful process that
maintains game state in memory.  It cannot be horizontally scaled, and there is
no option for an external data store.  Further, there is no support for
authentication or authorization.  These features will eventually be layered
into the system in an incremental fashion.  
