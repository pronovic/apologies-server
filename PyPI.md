# Apologies Server

[![pypi](https://img.shields.io/pypi/v/apologiesserver.svg)](https://pypi.org/project/apologiesserver/)
[![license](https://img.shields.io/pypi/l/apologiesserver.svg)](https://github.com/pronovic/apologies-server/blob/master/LICENSE)
[![wheel](https://img.shields.io/pypi/wheel/apologiesserver.svg)](https://pypi.org/project/apologiesserver/)
[![python](https://img.shields.io/pypi/pyversions/apologiesserver.svg)](https://pypi.org/project/apologiesserver/)
[![docs](https://readthedocs.org/projects/apologies-server/badge/?version=stable&style=flat)](https://apologies-server.readthedocs.io/en/stable/)
[![coverage](https://coveralls.io/repos/github/pronovic/apologies-server/badge.svg?branch=master)](https://coveralls.io/github/pronovic/apologies-server?branch=master)

[Apologies Server](https://github.com/pronovic/apologies-server) is a [Websocket](https://en.wikipedia.org/wiki/WebSocket) server interface used to interactively play a multi-player game using the [Apologies](https://github.com/pronovic/apologies) library.  The Apologies library implements a game similar to the [Sorry](https://en.wikipedia.org/wiki/Sorry!_(game)) board game.  

It was written as a learning exercise and technology demonstration effort, and serves as a complete example of how to manage a modern (circa 2020) Python project, including style checks, code formatting, integration with IntelliJ, [CI builds at GitHub](https://github.com/pronovic/apologies-server/actions), and integration with [PyPI](https://pypi.org/project/apologiesserver/) and [Read the Docs](https://apologies-server.readthedocs.io/en/stable/).  

See the [documentation](https://apologies-server.readthedocs.io/en/stable/design.html) for notes about the public interface and the event model.

## Not Maintained

I developed this code in mid-2020 during COVID-enforced downtime, as part of an effort to write a UI called [Apologies UI](https://github.com/pronovic/apologies-ui).  Javascript moves really fast, and by mid-2021, the UI implementation was already partially obsolete.  By late 2022, this server implementation was also partially obsolete.  In particular, the [asynctest](https://pypi.org/project/asynctest/) library I choose for unit testing my asynchronous code hasn't been updated for more than 3 years, and does not support Python 3.11.

I don't have the time, or frankly the interest, to rewrite the unit test suite to work with Python 3.11. So, as of November 2022, I have decided to archive this repository and stop maintaining it. It's best to treat this code (in conjunction with Apologies UI itself) as a snapshot of a working design from 2020.  The server code still works fine with earlier versions of Python, and it's still a reasonable example, but it will become less and less relevant as time goes on.
