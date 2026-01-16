# Apologies Server

[![pypi](https://img.shields.io/pypi/v/apologiesserver.svg)](https://pypi.org/project/apologiesserver/)
[![license](https://img.shields.io/pypi/l/apologiesserver.svg)](https://github.com/pronovic/apologies-server/blob/master/LICENSE)
[![wheel](https://img.shields.io/pypi/wheel/apologiesserver.svg)](https://pypi.org/project/apologiesserver/)
[![python](https://img.shields.io/pypi/pyversions/apologiesserver.svg)](https://pypi.org/project/apologiesserver/)
[![docs](https://readthedocs.org/projects/apologies-server/badge/?version=stable&style=flat)](https://apologies-server.readthedocs.io/en/stable/)
[![coverage](https://coveralls.io/repos/github/pronovic/apologies-server/badge.svg?branch=master)](https://coveralls.io/github/pronovic/apologies-server?branch=master)

[Apologies Server](https://github.com/pronovic/apologies-server) is a [Websocket](https://en.wikipedia.org/wiki/WebSocket) server interface used to interactively play a multi-player game using the [Apologies](https://github.com/pronovic/apologies) library.  The Apologies library implements a game similar to the [Sorry](https://en.wikipedia.org/wiki/Sorry!_(game)) board game.  

I originally developed this code in mid-2020 during COVID-enforced downtime, as
part of an effort to write a UI to play the Apologies board game in a web
browser.  However, Javascript moves really fast, and by mid-2021, my UI
implementation was already partially obsolete, and I abandoned work on it.

This code is still a reasonable example of how to build a Websocket server
including a state machine to manage board game state.  However, its main
purpose was to support the process of building that web UI, so it's not
designed or architected for production use.  It doesn't really look like
something I would write today, given the benefit of more experience with async
design patterns in Python.  But, it works.

See the [documentation](https://apologies-server.readthedocs.io/en/stable/design.html) for notes about the public interface and the event model.

## Prototype Code

