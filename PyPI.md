# Apologies Server

![](https://img.shields.io/pypi/l/apologies-server.svg)
![](https://img.shields.io/pypi/wheel/apologies-server.svg)
![](https://img.shields.io/pypi/pyversions/apologies-server.svg)
![](https://github.com/pronovic/apologies-server/workflows/Test%20Suite/badge.svg)

[Apologies Server](https://gitub.com/pronovic/apologies-server) is a [Websocket](https://en.wikipedia.org/wiki/WebSocket) server interface used to interactively play a multi-player game using the [Apologies](https://gitub.com/pronovic/apologies) library.  The Apologies library implements a game similar to the [Sorry](https://en.wikipedia.org/wiki/Sorry!_(game)) board game.

_Note:_ At present, the Apologies Server runs as a single stateful process that
maintains game state in memory.  It cannot be horizontally scaled, and there is
no option for an external data store.  There is also only limited support for
authentication and authorization - basically, any player can register any
available handle.  We do enforce resource limits (open connections, registered
users, in-progress games) to limit the amount of damage abusive clients can do.
