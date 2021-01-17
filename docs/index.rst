Apologies Server Python Library
===============================

Release v\ |version|

.. image:: https://img.shields.io/pypi/v/apologiesserver.svg
    :target: https://pypi.org/project/apologiesserver/

.. image:: https://img.shields.io/pypi/l/apologiesserver.svg
    :target: https://github.com/pronovic/apologies-server/blob/master/LICENSE

.. image:: https://img.shields.io/pypi/wheel/apologiesserver.svg
    :target: https://pypi.org/project/apologiesserver/

.. image:: https://img.shields.io/pypi/pyversions/apologiesserver.svg
    :target: https://pypi.org/project/apologiesserver/

.. image:: https://github.com/pronovic/apologies-server/workflows/Test%20Suite/badge.svg
    :target: https://github.com/pronovic/apologies-server/actions?query=workflow%3A%22Test+Suite%22

.. image:: https://readthedocs.org/projects/apologies-server/badge/?version=stable&style=flat
    :target: https://apologies-server.readthedocs.io/en/stable/

ApologiesServer_  is a Websocket_ server interface used to interactively play a
multi-player game using the Apologies_ library. The Apologies library
implements a game similar to the Sorry_ board game.

It was written as a learning exercise and technology demonstration effort, and
serves as a complete example of how to manage a modern (circa 2020) Python
project, including style checks, code formatting, integration with IntelliJ, CI
builds at GitHub, and integration with PyPI and Read the Docs.

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


Running the Server
------------------

The PyPI package includes a script called ``apologies-server``::

   $ apologies-server --help
   usage: apologies-server [-h] [--quiet] [--verbose] [--debug] [--config CONFIG]
                           [--logfile LOGFILE] [--override OVERRIDE]

   Start the apologies server and let it run forever.

   optional arguments:
     -h, --help           show this help message and exit
     --quiet              decrease log verbosity from INFO to ERROR
     --verbose            increase log verbosity from INFO to DEBUG
     --debug              like --verbose but also include websockets logs
     --config CONFIG      path to configuration on disk
     --logfile LOGFILE    path to logfile on disk (default is stdout)
     --override OVERRIDE  override a config parameter as "param:value"

   By default, the server writes logs to stdout. If you prefer, you can specify
   the path to a logfile, and logs will be written there instead. The default
   configuration file is "/Users/kpronovici/.apologiesrc". If the default
   configuration file is not found, default values will be set. If you override
   the default config file, it must exist. You may override any individual config
   parameter with "--override param:value".

The simplest way to start the server is with no arguments::

   $ apologies-server
   2020-06-10 14:31:39,831Z --> [INFO   ] Apologies server started
   2020-06-10 14:31:39,832Z --> [INFO   ] Configuration: {
     "logfile_path": null,
     "server_host": "localhost",
     "server_port": 8080,
     "close_timeout_sec": 10,
     "websocket_limit": 1000,
     "total_game_limit": 1000,
     "in_progress_game_limit": 25,
     "registered_player_limit": 100,
     "websocket_idle_thresh_min": 2,
     "websocket_inactive_thresh_min": 5,
     "player_idle_thresh_min": 15,
     "player_inactive_thresh_min": 30,
     "game_idle_thresh_min": 10,
     "game_inactive_thresh_min": 20,
     "game_retention_thresh_min": 2880,
     "idle_websocket_check_period_sec": 120,
     "idle_websocket_check_delay_sec": 300,
     "idle_player_check_period_sec": 120,
     "idle_player_check_delay_sec": 300,
     "idle_game_check_period_sec": 120,
     "idle_game_check_delay_sec": 300,
     "obsolete_game_check_period_sec": 300,
     "obsolete_game_check_delay_sec": 300
   }
   2020-06-10 14:31:39,832Z --> [INFO   ] Adding signal handlers...
   2020-06-10 14:31:39,832Z --> [INFO   ] Scheduling tasks...
   2020-06-10 14:31:39,832Z --> [INFO   ] Completed starting websocket server

The server displays its configuration when it boots.  You can override any of
this configuration using the switches described in the help output above.

.. _Docs: design.rst
.. _Apologies: https://pypi.org/project/apologies
.. _ApologiesServer: https://pypi.org/project/apologiesserver
.. _Sorry: https://en.wikipedia.org/wiki/Sorry!_(game)
.. _Websocket: https://en.wikipedia.org/wiki/WebSocket
