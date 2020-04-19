Apologies Server Python Library
===============================

Release v\ |version|

.. image:: https://img.shields.io/pypi/l/apologies-server.svg
    :target: https://pypi.org/project/apologies-server/

.. image:: https://img.shields.io/pypi/wheel/apologies-server.svg
    :target: https://pypi.org/project/apologies-server/

.. image:: https://img.shields.io/pypi/pyversions/apologies-server.svg
    :target: https://pypi.org/project/apologies-server/

.. image:: https://github.com/pronovic/apologies-server/workflows/Test%20Suite/badge.svg
    :target: https://github.com/pronovic/apologies-server

ApologiesServer_  is a Websocket_ server interface used to interactively play a
multi-player game using the Apologies_ library. The Apologies library
implements a game similar to the Sorry_ board game.

`Note:` At present, the Apologies Server runs as a single stateful process that
maintains game state in memory.  It cannot be horizontally scaled, and there is
no option for an external data store.  Further, there is no support for
authentication or authorization.  These features will eventually be layered
into the system in an incremental fashion.  


Installation
------------

Install the package with pip::

    $ pip install apologies-server


Documentation
-------------

.. toctree::
   :maxdepth: 2
   :glob:



.. _Apologies: https://pypi.org/project/apologies
.. _ApologiesServer: https://pypi.org/project/apologies-server
.. _Sorry: https://en.wikipedia.org/wiki/Sorry!_(game)
.. _Websocket: https://en.wikipedia.org/wiki/WebSocket
