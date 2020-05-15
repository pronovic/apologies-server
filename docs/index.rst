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

.. image:: https://readthedocs.org/projects/apologies-server/badge/?version=latest&style=flat
    :target: https://apologies-server.readthedocs.io/en/latest/


ApologiesServer_  is a Websocket_ server interface used to interactively play a
multi-player game using the Apologies_ library. The Apologies library
implements a game similar to the Sorry_ board game.

`Note:` At present, the Apologies Server runs as a single stateful process that
maintains game state in memory.  It cannot be horizontally scaled, and there is
no option for an external data store.  There is also only limited support for
authentication and authorization - basically, any player can register any
available handle.  We do enforce resource limits (open connections, registered
users, in-progress games) to limit the amount of damage abusive clients can do. 


Installation
------------

Install the package with pip::

    $ pip install apologies-server


Design Documentation
--------------------

- :doc:`/design`


.. toctree::
   :maxdepth: 2
   :glob:


.. _Docs: design.rst
.. _Apologies: https://pypi.org/project/apologies
.. _ApologiesServer: https://pypi.org/project/apologies-server
.. _Sorry: https://en.wikipedia.org/wiki/Sorry!_(game)
.. _Websocket: https://en.wikipedia.org/wiki/WebSocket
