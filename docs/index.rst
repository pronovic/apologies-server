Apologies Server Python Library
===============================

Release v\ |version|

.. image:: https://img.shields.io/pypi/l/apologiesserver.svg
    :target: https://pypi.org/project/apologiesserver/

.. image:: https://img.shields.io/pypi/wheel/apologiesserver.svg
    :target: https://pypi.org/project/apologiesserver/

.. image:: https://img.shields.io/pypi/pyversions/apologiesserver.svg
    :target: https://pypi.org/project/apologiesserver/

.. image:: https://github.com/pronovic/apologies-server/workflows/Test%20Suite/badge.svg
    :target: https://github.com/pronovic/apologies-server

.. image:: https://readthedocs.org/projects/apologies-server/badge/?version=latest&style=flat
    :target: https://apologies-server.readthedocs.io/en/latest/


ApologiesServer_  is a Websocket_ server interface used to interactively play a
multi-player game using the Apologies_ library. The Apologies library
implements a game similar to the Sorry_ board game.

It was written as a learning exercise and technology demonstration effort, and
serves as a complete example of how to manage a modern (circa 2020) Python
project, including style checks, code formatting, integration with IntelliJ, CI
builds at GitHub, and integration with PyPI and Read the Docs.

As of this writing, the published PyPI project does not include a script to run
the server. The only way to run it is from the codebase, for local testing. See
the developer_ documentation on GitHub for more information.

As a technology demonstration effort, the Apologies Server is fairly
simplistic.  It runs as a single stateful process that maintains game state in
memory.  It cannot be horizontally scaled, and there is no option for an
external data store.  There is also only limited support for authentication and
authorization - any player can register any handle that is not currently being
used.  We do enforce resource limits (open connections, registered users,
in-progress games) to limit the amount of damage abusive clients can do. 


Installation
------------

Install the package with pip::

    $ pip install apologiesserver


Design Documentation
--------------------

- :doc:`/design`


.. toctree::
   :maxdepth: 2
   :glob:


.. _Docs: design.rst
.. _Apologies: https://pypi.org/project/apologies
.. _ApologiesServer: https://pypi.org/project/apologiesserver
.. _Sorry: https://en.wikipedia.org/wiki/Sorry!_(game)
.. _Websocket: https://en.wikipedia.org/wiki/WebSocket
.. _developer: https://github.com/pronovic/apologies-server/blob/master/DEVELOPER.md#running-the-server
