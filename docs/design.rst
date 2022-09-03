Event Model & Public Interface
==============================

Periodic Checks
---------------

Periodic checks need somewhere to run.  The initial design is for a single
server that does not horizontally scale, so there is an obvious place to run
these checks. A future design that is intended to horizontally scale will need
a separate scheduling component.

Idle Websocket Check
~~~~~~~~~~~~~~~~~~~~

On a periodic basis, the server will check how long it has been since the most
recent activity for each connected websocket.  A websocket which has no
registered players and exceeds the idle threshold will be marked as idle,
triggering an `Websocket Idle` event.  A websocket which was already idle and
exceeds the inactive threshold, will be terminated, triggering a `Webhook
Inactive` event.  Any websocket associated with at least one registered player
is ignored for the purposes of this check, because we want the players to be
marked idle before their associated connection.

Idle Game Check
~~~~~~~~~~~~~~~

On a periodic basis, the server will check how long it has been since the most
recent activity for each tracked game.  A game which exceeds the idle threshold
will be marked as idle, triggering an `Game Idle` event.  A game which remains
idle and exceeds the inactive threshold will be terminated, triggering a `Game
Inactive` event.  

Idle Player Check
~~~~~~~~~~~~~~~~~

On a periodic basis, the server will check how long it has been since the most
recent activity for each registered player.  A player which exceeds the idle
threshold but is not disconnected will be marked as idle, triggering an `Player
Idle` event.  A player which exceeds the idle threshold and is disconnected, or
which was already idle and exceeds the inactive threshold, will be terminated,
triggering a `Player Inactive` event.

Obsolete Game Check
~~~~~~~~~~~~~~~~~~~

On a periodic basis, the server will check how long it has been since each
completed or cancelled game has finished.  A game which exceeds the game
history retention threshold will be marked as obsolete, triggering a `Game
Obsolete` event.

Client Requests
---------------

All client requests, except the original `Register Player` request, must
contain the player id returned from the `Player Registered` event, as shown
in the examples below.

In all cases, if the request is syntactically invalid, if the arguments are
illegal, or if the request fails for some other reason, a `Request Failed`
event will be generated, containing as much context as possible.

Register Player
~~~~~~~~~~~~~~~

A player registers by providing a handle to be known by.  This triggers a
`Player Registered` event.  All registered players are public, meaning that
their handle is visible via the `Registered Players` event.  There is no
authentication as part of the registration process. Any player can choose any
handle that is not currently in use.  The system may reject new user
registrations if the handle is already in use or if the user registration limit
has been reached, triggering a `Request Failed` event with context.  Successful
registration initializes the player's last active timestamp and marks the
player as active.  

Example request::

    {
      "message": "REGISTER_PLAYER",
      "context": {
        "handle": "leela"
      }
    }

Reregister Player
~~~~~~~~~~~~~~~~~

If a player has become disconnected, but still has access to its player id from
the `Registration Completed` event, it may re-register and get access to its
existing handle by providing the player id.  If the player id is no longer
valid (because there has been a `Player Inactive` event for the player), this
falls back on behavior equivalent to the `Register Player` request.  Successful
re-registration resets the player's last active timestamp and marks the player
as active and connected.

Example request::

    {
      "message": "REREGISTER_PLAYER",
      "player_id": "247179aa-e516-4eed-b68f-7daaa54c0625"
      "context": {
        "handle": "leela"
      }
    }

Unregister Player
~~~~~~~~~~~~~~~~~

A player may unregister at any time.  Once unregistered, the player's handle is
available to be registered by another player.  If the player has joined or is
currently playing a game, unregistering will trigger a `Game Player Left`
event.

Example request::

    {
      "message": "UNREGISTER_PLAYER",
      "player_id": "247179aa-e516-4eed-b68f-7daaa54c0625"
    }

List Players
~~~~~~~~~~~~

Any registered player may request a list of currently registered players.  This
triggers the `Registered Players` event.  Receipt of this message resets the
sender's last active timestamp and marks the sender as active.

Example request::

    {
      "message": "LIST_PLAYERS",
      "player_id": "247179aa-e516-4eed-b68f-7daaa54c0625"
    }

Advertise Game
~~~~~~~~~~~~~~

A registered player may advertise exactly one game, triggering a `Game
Advertised` event.  The advertised game may be for 2-4 players, and may be
"public" (anyone can join) or "private" (only invited players may join).  Even
though anyone can join a public game, it may also have a list of invited
players.  A `Game Invitation` event is triggered for each invited player.  A
player may only advertise a game if it is not already playing another game.
The list of invited players is not validated; it can include any handle, even
the handle of a player which is not currently registered.  The player which
advertises a game will immediately be marked as having joined that game,
triggering a `Game Joined` event.  The system may reject an advertised game if
it is invalid or if the system-wide game limit has been reached. Receipt of
this message resets the sender's last active timestamp and marks the sender as
active.

Example requests::

    {
      "message": "ADVERTISE_GAME",
      "player_id": "247179aa-e516-4eed-b68f-7daaa54c0625",
      "context": {
        "name": "Leela's Game",
        "mode": "STANDARD",
        "players": 3,
        "visibility": "PUBLIC",
        "invited_handles": [ ]
      }
    }

    {
      "message": "ADVERTISE_GAME",
      "player_id": "247179aa-e516-4eed-b68f-7daaa54c0625",
      "context": {
        "name": "Bender's Game",
        "mode": "ADULT",
        "players": 2,
        "visibility": "PRIVATE"
        "invited_handles": [ "bender", "hermes", ]
      }
    }

List Available Games
~~~~~~~~~~~~~~~~~~~~

A registered player may request a list of available games, triggering an
`Available Games` event.  The result will include all public games and any
private games the player has been invited to (by handle), but will be
restricted to include only games that have not started yet.  Receipt of this
message resets the sender's last active timestamp and marks the sender as
active.  A player may request a list of available games even if they are 
already playing another game, although they can only join a game if they
quit the one they are playing.

Example request::

    {
      "message": "LIST_AVAILABLE_GAMES",
      "player_id": "247179aa-e516-4eed-b68f-7daaa54c0625"
    }

Join Game
~~~~~~~~~

A registered player that is not currently playing or advertising another game
may choose to join any available game returned from the `Available Games`
event, triggering a `Game Joined` event.  The request will be rejected with a
`Request Failed` event if the player has joined another game already, if the
game is no longer being advertised, if the game has already been started, or if
the game is private and the player has not been invited to join it.  If this
player completes the number of players advertised for the game, then the game
will be started immediately and a `Game Started` event will be triggered.
Receipt of this message resets the sender's last active timestamp and marks the
sender as active, and also resets the game's last active timestamp and marks
the game as active.

Example request::

    {
      "message": "JOIN_GAME",
      "player_id": "247179aa-e516-4eed-b68f-7daaa54c0625",
      "context": {
        "game_id": "f13b405e-36e5-45f3-a351-e45bf487acfe"
      }
    }

Quit game
~~~~~~~~~

A registered player that has joined a game may quit that game, even if the game
has not yet started or finished.  However, the advertising player may not quit.
The advertising player must cancel the game instead.  Qutting will trigger a
`Game Player Left` event for the game.  If the game continues to be viable, the
player who quit will have their move chosen programmatically for future turns.
Receipt of this message resets the sender's last active timestamp and marks the
sender as active, and also resets the game's last active timestamp and marks
the game as active.

Example request::

    {
      "message": "QUIT_GAME",
      "player_id": "247179aa-e516-4eed-b68f-7daaa54c0625"
    }

Start Game
~~~~~~~~~~

The registered player that advertised a game may start it at any time,
triggering a `Game Started` event. At the point the game is started, if fewer
players have joined than were requested when advertising the game, the
remainder of the player slots will be filled out with a non-user (programmatic)
player managed by the game engine.  Receipt of this message resets the sender's
last active timestamp and marks the sender as active, and also resets the
game's last active timestamp and marks the game as active.

Example request::

    {
      "message": "START_GAME",
      "player_id": "247179aa-e516-4eed-b68f-7daaa54c0625"
    }

Cancel Game
~~~~~~~~~~~

The registered player that advertised a game may cancel it at any time, either
before or after the game has started.  A `Game Cancelled` event will be
triggered.  Receipt of this message resets the sender's last active timestamp
and marks the sender as active.

Example request::

    {
      "message": "CANCEL_GAME",
      "player_id": "247179aa-e516-4eed-b68f-7daaa54c0625"
    }

Execute Move
~~~~~~~~~~~~

When a player has been notified that it is their turn via the `Game Player
Turn` event, it must choose a move from among the legal moves provided in the
event, and request to execute that move by id.  This triggers a `Game Player
Move` event.  When a move has been completed, this triggers one of several
other events depending on the state of the game (potentially a `Game State
Change` event, a `Game Player Turn` event, a `Game Completed` event, etc.).
The request will be rejected with a `Request Failed` event if the player is not
playing a game, if the player's game has been cancelled or completed, if it is
not currently the player's turn, or if the player attempts to execute an
illegal move.  Receipt of this message resets the sender's last active
timestamp and marks the sender as active, and also resets the game's last
active timestamp and marks the game as active.

Example request::

    {
      "message": "EXECUTE_MOVE",
      "player_id": "247179aa-e516-4eed-b68f-7daaa54c0625",
      "context": {
        "move_id": "4"
      }
    }


Execute Optimal Move
~~~~~~~~~~~~~~~~~~~~

When a player has been notified that it is their turn via the `Game Player
Turn` event, it may optionally choose to have the server determine and then
execute the optimal move.  This behaves exactly like the `Execute Move`
request, except that the player does not need to provide a move id.

Example request::

    {
      "message": "OPTIMAL_MOVE",
      "player_id": "247179aa-e516-4eed-b68f-7daaa54c0625",
    }


Retrieve Game State
~~~~~~~~~~~~~~~~~~~

The server will normally push the game state to each player that is associated
with a game whenever the state changes. However, at any time a player may
request the current game state to be pushed again, triggering a `Game State
Change` event for the sender only.  Receipt of this message resets the sender's
last active timestamp and marks the sender as active, and also resets the
game's last active timestamp and marks the game as active.  The request will be
rejected with a `Request Failed Event` if the player is not currently playing
game.

Example request::

    {
      "message": "RETRIEVE_GAME_STATE",
      "player_id": "247179aa-e516-4eed-b68f-7daaa54c0625"
    }

Send Message
~~~~~~~~~~~~

Any registered player may send a short message to one or more other players,
identified by handle, triggering a `Player Message Received` event.  If the
recipient's current status allows the message to be delivered, it will be
delivered immediately.  This facility is intended to provide a chat-type
feature, and the maximum size of a message may be limited.  Receipt of this
message resets the sender's last active timestamp and marks the sender as
active.

Example request::

    {
      "message": "SEND_MESSAGE",
      "player_id": "247179aa-e516-4eed-b68f-7daaa54c0625",
      "context": {
        "message": "Hello!",
        "recipient_handles": [ "hermes", "nibbler" ]
      }
    }

Server Events
-------------

Each server event is associated with a particular situation on the back end.
When triggered, some server events generate a message to one or more players.
Other events only change internal server state, or trigger other events.

Request Failed
~~~~~~~~~~~~~~

This event is triggered if a player request is syntactically invalid, if the
arguments are illegal, or if the request fails for some other reason.   The
message provides context to the sender, telling them what happened via a reason
code.  If possible, the handle of the associated player is provided.  If the
handle can't be established, then it will be ``null``. 

+-----------------------------+-------------------------------------------------+
| Reason Code                 | Description                                     |
+=============================+=================================================+
| ``INVALID_REQUEST``         | Invalid request                                 |
+-----------------------------+-------------------------------------------------+
| ``DUPLICATE_USER``          | Handle is already in use                        |
+-----------------------------+-------------------------------------------------+
| ``INVALID_AUTH``            | Missing or invalid authorization header         |
+-----------------------------+-------------------------------------------------+
| ``WEBSOCKET_LIMIT``         | Connection limit reached; try again later       |
+-----------------------------+-------------------------------------------------+
| ``USER_LIMIT``              | System user limit reached; try again later      |
+-----------------------------+-------------------------------------------------+
| ``GAME_LIMIT``              | System game limit reached; try again later      |
+-----------------------------+-------------------------------------------------+
| ``INVALID_PLAYER``          | Unknown or invalid player                       |
+-----------------------------+-------------------------------------------------+
| ``INVALID_GAME``            | Unknown or invalid game                         |
+-----------------------------+-------------------------------------------------+
| ``NOT_PLAYING``             | Player is not playing a game                    |
+-----------------------------+-------------------------------------------------+
| ``NOT_ADVERTISER``          | Player did not advertise this game              |
+-----------------------------+-------------------------------------------------+
| ``ALREADY_PLAYING``         | Player is already playing a game                |
+-----------------------------+-------------------------------------------------+
| ``NO_MOVE_PENDING``         | No move is pending for this player              |
+-----------------------------+-------------------------------------------------+
| ``ILLEGAL_MOVE``            | The chosen move is not legal                    |
+-----------------------------+-------------------------------------------------+
| ``ADVERTISER_MAY_NOT_QUIT`` | Advertiser may not quit a game (cancel instead) |
+-----------------------------+-------------------------------------------------+
| ``INTERNAL_ERROR``          | Internal error                                  |
+-----------------------------+-------------------------------------------------+

Example messages::

    {
      "message": "REQUEST_FAILED",
      "context": {
        "reason": "WEBSOCKET_LIMIT",
        "comment": "Connection limit reached; try again later",
        "handle": null
      }
    }

    {
      "message": "REQUEST_FAILED",
      "context": {
        "reason": "NOT_PLAYING",
        "comment": "Player is not playing a game",
        "handle": "leela"
      }
    }

Server Shutdown
~~~~~~~~~~~~~~~

At shutdown, the server will send a message to all players, so each player
knows that the server is going away and can cleanup.  State is not maintained
across server restarts, so in-progress games will be interrupted.

Example message::

    {
      "message": "SERVER_SHUTDOWN"
    }

Websocket Connected
~~~~~~~~~~~~~~~~~~~

This event is triggered when a new client connection is established.  Multiple
players can conceivably share the same webhook, since the player is identified
by the player id in the request and not by the webhook itself.  So, we track
webhooks separately from players.

Websocket Disconnected
~~~~~~~~~~~~~~~~~~~~~~

This event is triggered when a webhook disconnects.  A webhook may become
disconnected from the server without the associated players explicitly
unregistering.  A `Player Disconnected` event will be triggered for each player
associated with the disconnected webhook.

Websocket Idle
~~~~~~~~~~~~~~

This event is triggered when the `Idle Websocket Check` determines that a
websocket has been idle for too long.  This notifies the websocket that it is
idle and at risk of being terminated.

Example message::

    {
      "message": "WEBSOCKET_IDLE"
    }

Websocket Inactive
~~~~~~~~~~~~~~~~~~

This event is triggered when the `Idle Websocket Check` determines that a
websocket has exceeded the inactive threshold.  We websocket and will be
disconnected and a `Websocket Disconnected` event will be triggered.

Example message::

    {
      "message": "WEBSOCKET_INACTIVE"
    }

Registered Players
~~~~~~~~~~~~~~~~~~

This event returns information about all registered players.  Returned
information includes each player's handle, their registration date, and current
status.

Example message::

    {
      "message": "REGISTERED_PLAYERS",
      "context": {
        "players": [
           {
             "handle": "leela",
             "registration_date": "2020-04-23 08:42:31,443+00:00",
             "last_active_date": "2020-04-23 08:53:19,116+00:00",
             "connection_state": "CONNECTED",
             "activity_state": "ACTIVE",
             "play_state": "JOINED"
             "game_id": null
           },
           {
             "handle": "nibbler",
             "registration_date": "2020-04-23 09:10:00,116+00:00",
             "last_active_date": "2020-04-23 09:13:02,221+00:00",
             "connection_state": "DISCONNECTED",
             "activity_state": "IDLE",
             "play_state": "PLAYING",
             "game_id": "166a930b-66f0-4e5a-8611-bbbf0a441b3e"
           },
           {
             "handle": "hermes",
             "registration_date": "2020-04-23 10:13:03,441+00:00",
             "last_active_date": "2020-04-23 10:13:03,441+00:00",
             "connection_state": "CONNECTED",
             "activity_state": "ACTIVE",
             "play_state": "WAITING",
             "game_id": null
           },
         ]
      }
    }

Available Games
~~~~~~~~~~~~~~~

This event notifies a player about games that the player may join.  The result
will include all public games and any private games the player has been invited
to (by handle), but will be restricted to include only games that have not
started yet. 

Example message::

    {
      "message": "AVAILABLE_GAMES",
      "context": {
        "games": [
          {
            "game_id": "8fb16554-ca00-4b65-a191-1c52cb0eae37",
            "name": "Planet Express",
            "mode": "ADULT",
            "advertiser_handle": "leela",
            "players": 4,
            "available": 2,
            "visibility": "PUBLIC",
            "invited_handles": [ "bender", "hermes", ]
          }
        ]
      }
    }

Player Registered
~~~~~~~~~~~~~~~~~

This event is triggered when a player successfully registers their handle.

Example message::

    {
      "message": "PLAYER_REGISTERED",
      "player_id": "247179aa-e516-4eed-b68f-7daaa54c0625",
      "context": {
        "handle": "leela" 
      }
    }

Player Reregistered
~~~~~~~~~~~~~~~~~~~

This event is triggered when a player successfully re-registers their handle
using a saved-off player id.  (The message is the same as for the `Player
Registered` event.)

Example message::

    {
      "message": "PLAYER_REGISTERED",
      "context": {
        "player_id": "8fc4a03b-3e4d-438c-a3fc-b6913e829ab3",
        "handle": "leela" 
      }
    }

Player Unregistered
~~~~~~~~~~~~~~~~~~~

This event is triggered when a player unregisters.  If the player has joined or
is currently playing a game, a `Game Player Left` event is triggered.

Example message::

    {
      "message": "PLAYER_UNREGISTERED",
      "context": {
        "handle": "leela"
      }
    }

Player Disconnected
~~~~~~~~~~~~~~~~~~~

A player may become disconnected from the server without explicitly
unregistering.  In this case, the player will be marked as disconnected and
idle.  No events will be sent to the player as long as it remains in a
disconnected state.  If the player has joined or is playing a game, a `Game
Player Left` event is triggered.

Player Idle
~~~~~~~~~~~

This event is triggered when the `Idle Player Check` determines that a player
has been idle for too long.  This notifies the player that it is idle and at
risk of being terminated.

Example message::

    {
      "message": "PLAYER_IDLE",
      "context": {
        "handle": "leela"
      }
    }

Player Inactive
~~~~~~~~~~~~~~~

This event is triggered when the `Idle Player Check` determines that a
disconnected player has exceeded the idle threshold, or an idle player has
exceeded the inactive threshold.  If connected, the player will be
disconnected, and then the `Player Unregistered` event will be triggered.

Example message::

    {
      "message": "PLAYER_INACTIVE",
      "context": {
        "handle": "leela"
      }
    }

Player Message Received
~~~~~~~~~~~~~~~~~~~~~~~

When a registered player sends a `Send Message` request to the server, the
server will notify recipients about the message.  Messages will be delivered to
all registered and connected users, regardless of whether those recipients are
playing a game with the sender.

Example message::

    {
      "message": "PLAYER_MESSAGE_RECEIVED",
      "context": {
        "sender_handle": "leela",
        "recipient_handles": [ "hermes", "nibbler", ],
        "message": "Hello!"
      }
    }

Game Advertised
~~~~~~~~~~~~~~~

This event is triggered when a new game is advertised.  The message is sent to the 
player that advertised the game.  If there are any invited handles, then a `Game
Invitation` event will be triggered for each invited player.

Example message::

    {
      "message": "GAME_ADVERTISED",
      "context": {
        "game": {
          "game_id": "8fb16554-ca00-4b65-a191-1c52cb0eae37",
          "name": "Planet Express",
          "mode": "ADULT",
          "advertiser_handle": "leela",
          "players": 4,
          "available": 2,
          "visibility": "PUBLIC",
          "invited_handles": [ "bender", "hermes", ]
        }
      }  
    }

Game Invitation
~~~~~~~~~~~~~~~

This event notifies a player about a newly-advertised game that the player has been
invited to.  It triggered by the `Game Advertised` event.

Example message::

    {
      "message": "GAME_INVITATION",
      "context": {
        "game": {
          "game_id": "8fb16554-ca00-4b65-a191-1c52cb0eae37",
          "name": "Planet Express",
          "mode": "ADULT",
          "advertiser_handle": "leela",
          "players": 4,
          "available": 2,
          "visibility": "PUBLIC",
          "invited_handles": [ "bender", "hermes", ]
        }
      }  
    }

Game Joined
~~~~~~~~~~~

This event is triggered when a player joins a game.  A player may explicitly
join a game via the `Join Game` request, or may implicitly join a game when
advertising it.   Whenever a player joins a game, a `Game Player Change` event
is triggered.  If this player completes the number of players advertised for
the game, then the game will be started immediately and a `Game Started` event
will be triggered.  

Example message::

    {
      "message": "GAME_JOINED",
      "context": {
        "player_handle": "nibbler",
        "game_id": "f13b405e-36e5-45f3-a351-e45bf487acfe"
        "name": "Planet Express",
        "mode": "ADULT",
        "advertiser_handle": "leela",
      }
    }

Game Started
~~~~~~~~~~~~

This event is triggered when a game is started.  A game may be started
automatically once enough players join, or may be started manually by the
advertising player.  This event also triggers a `Game Player Change`
event that updates the player states.

Example message::

    {
      "message": "GAME_STARTED",
      "context": {
        "game_id": "f13b405e-36e5-45f3-a351-e45bf487acfe"
      }
    }

Game Cancelled
~~~~~~~~~~~~~~

When a game is cancelled or must be stopped prior to completion for some other
reason, the server will trigger this event.  A game may be cancelled explicitly
by the player which advertised it, or might be cancelled by the server if it is
no longer viable, or if it has exceeded the inactive timeout, or during server
shutdown.  Cancelled and completed games are tracked for a limited period of
time after finishing.  Games cancelled due to server shutdown do not result in
a notification message.

Example message::

    {
      "message": "GAME_CANCELLED",
      "context": {
        "game_id": "f13b405e-36e5-45f3-a351-e45bf487acfe",
        "reason": "NOT_VIABLE",
        "comment": "Player nibbler unregistered"
      }
    }

Game Completed
~~~~~~~~~~~~~~

When a player wins a game, and the game is thus completed, the server will
notify all players.  The message indicates the winner's handle and includes a
descriptive comment.  Cancelled and completed games are tracked for a limited
period of time after finishing.

Example message::

    {
      "message": "GAME_COMPLETED",
      "context": {
        "game_id": "f13b405e-36e5-45f3-a351-e45bf487acfe",
        "winner": "nibbler",
        "comment": "Player nibbler won after 46 turns"
      }
    }

Game Idle
~~~~~~~~~

This event is triggered when the `Idle Game Check` determines that a game has
been idle for too long.  The generated message notifies all players that the
game is idle and at risk of being cancelled.

Example message::

    {
      "message": "GAME_IDLE",
      "context": {
        "game_id": "f13b405e-36e5-45f3-a351-e45bf487acfe"
      }
    }

Game Inactive
~~~~~~~~~~~~~

This event is triggered when the `Idle Game Check` determines that an idle game
has exceeded the inactive threshold.  The generated message notifies all
players that the game is inactive and will be cancelled.  The server will then
immediately cancel the game, triggering a `Game Cancelled` event.

Example message::

    {
      "message": "GAME_INACTIVE",
      "context": {
        "game_id": "f13b405e-36e5-45f3-a351-e45bf487acfe"
      }
    }

Game Obsolete
~~~~~~~~~~~~~

This event is triggered when the `Obsolete Game Check` determines that a
finished game has exceeded the game history retention threshold.  The server
will stop tracking the game in the backend data store.  No message is
generated.

Game Player Quit
~~~~~~~~~~~~~~~~

This event is triggered when a player explicitly quits a game.  A player may
quit a game any time after they join, regardless of whether the game has been
started.  This triggers a `Game Player Left` event.

Example message::

    {
      "message": "GAME_PLAYER_QUIT",
      "context": {
        "handle": "leela",
        "game_id": "f13b405e-36e5-45f3-a351-e45bf487acfe"
      }
    }


Game Player Left
~~~~~~~~~~~~~~~~

This event is triggered when a player leaves a game, either by quitting or by
being disconnected.  If the advertiser leaves the game, this triggers a `Game
Cancelled Event`.  For other players, leaving will trigger a `Game Player
Change` event and might potentially result in a `Game Cancelled` event if the
game is no longer viable.  If the game has already been started and continues
to be viable, future moves for this player will be chosen programmatically.  If
the player is in the middle of their turn, this will happen immediately.

Game Player Move
~~~~~~~~~~~~~~~~

This event is triggered when a player chooses their move.  In turn, it
triggers a `Game Move` event. 

Game Programmatic Move Event
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are several different circumstances where we might need to choose a
programmatic move for a player.  The first is that the player itself is
programmatic - the advertiser chose to start the game before a full set of
human players joined.  Every move for a programmatic player must be chosen
programmatically.  However, we also choose a move programmatically for any
player that has quit or been disconnected from an in-progress game.  Once the
move has been chosen programmatically, this triggers a `Game Move` event.

Game Move
~~~~~~~~~

This event is triggered when a move has been chosen, either by a player or
progammatically.  The move is executed.  If the player has won the game, then a
`Game Completed` event is triggered.  Otherwise a `Game State Change` and a
`Game Next Turn` event are both triggered.  This event also resets the game's
last active timestamp and marks the game as active.

Game Next Turn
~~~~~~~~~~~~~~

This event is triggered by the `Game Move` event if the game has not been
completed by the executed move.  If the next turn is for a programmatic player,
the `Game Programmatic Move` event is triggered.  If the next turn is for a
human player, then one of two things happens. If the player is still playing
the game, then a `Game Player Turn` event is triggered.  If the player is not
playing the game (if they quit, were disconnected, or even unregistered) then a
`Game Programmatic Move` event is triggered instead.

Game Player Change
~~~~~~~~~~~~~~~~~~

This event is triggered when a player joins or leaves a game, or when a game
starts.  Players start in the ``JOINED`` state and move to the ``PLAYING`` state
when the game starts.  A player might leave a game because they ``QUIT``, or
because they were ``DISCONNECTED``.  The message is sent to all players in the
game.  Note that player colors are not assigned until after the game has been
started, so the ``player_color`` value may be ``null``.

Example message::

    {
      "message": "GAME_PLAYER_CHANGE",
      "context": {
        "game_id": "f13b405e-36e5-45f3-a351-e45bf487acfe",
        "comment": "Player nibbler (YELLOW) quit the game.",
        "players": [
          {
            "handle": "leela",
            "player_color": "RED",
            "player_type": "HUMAN",
            "player_state": "JOINED"  
          },
          {
            "handle": "nibbler",
            "player_color": "YELLOW",
            "player_type": "HUMAN",
            "player_state": "QUIT"
          },
          {
            "handle": "Legolas",
            "player_color": "BLUE",
            "player_type": "PROGRAMMATIC",
            "player_state": "JOINED"
          },
          {
            "handle": "bender",
            "player_color": "GREEN",
            "player_type": "HUMAN",
            "player_state": "DISCONNECTED"
          }
        ]
      }
    }

Game State Change
~~~~~~~~~~~~~~~~~

When triggered, this event notifies a player about the current state of a game.
The event can be triggered when a player requests the current state via the
`Request Game State` request, or can be triggered when the state of the game
has changed.  Among other things, the state of the game is considered to have
changed when the game starts, when a player executes a move, when a player wins
the game, or when the game is cancelled or is terminated due to inactivity.

Each player's view of the game is different; for instance, in an ``ADULT`` mode
game, a player can only see their own cards, not the cards held by other
players.  In an ``ADULT`` mode game, there is no explict message when the
player draws a card to fill their hand.  Instead, the state change event simply
reflects the new hand.  

The ``recent_history`` attribute describes the 10 most recent actions that
occurred in game play, in order from oldest to newest.  There will always be an
``action``, but the ``color`` and ``card`` are optional, since some game
actions don't involve a player or don't involve playing a card.  If you want to
track the most recent player turn, look for the latest history item that has
both a color and a card.

Example message::

    {
      "message": "GAME_STATE_CHANGE",
      "context": {
        "game_id": "f13b405e-36e5-45f3-a351-e45bf487acfe",
        "recent_history": [
          {
            "action": "Game Started",
            "color": null,
            "card": null,
            "timestamp": "2020-05-14T13:53:35,334+00:00"
          },
          {
            "action": "Turn is forfeit; discarded card 12",
            "color": "RED",
            "card": "CARD_12",
            "timestamp": "2020-05-14T13:53:37.012+00:00"
          }
        ],
        "player": {
          "color": "RED",
          "turns": 16,
          "hand": [ "CARD_APOLOGIES", "CARD_1" ],
          "pawns": [
            {
              "color": "RED",
              "id": "0",
              "start": false,
              "home": false,
              "safe": null,
              "square": 32
            },
            {
              "color": "RED",
              "id": "1",
              "start": false,
              "home": false,
              "safe": 3,
              "square": null
            },
            {
              "color": "RED",
              "id": "2",
              "start": false,
              "home": false,
              "safe": null,
              "square": 45
            },
            {
              "color": "RED",
              "id": "3",
              "start": true,
              "home": false,
              "safe": null,
              "square": null
            }
          ]
        },
        "opponents": [
          {
            "color": "GREEN",
            "turns": 15,
            "hand": [ ],
            "pawns": [
              {
                "color": "GREEN",
                "id": "0",
                "start": true,
                "home": false,
                "safe": null,
                "square": null
              },
              {
                "color": "GREEN",
                "id": "1",
                "start": false,
                "home": true,
                "safe": null,
                "square": null
              },
              {
                "color": "GREEN",
                "id": "2",
                "start": false,
                "home": false,
                "safe": 4,
                "square": null
              },
              {
                "color": "GREEN",
                "id": "3",
                "start": false,
                "home": false,
                "safe": null,
                "square": 19
              }
            ]
          }
        ]
      }
    }

Game Player Turn
~~~~~~~~~~~~~~~~

When the game play engine determines that it is a player's turn to execute a
move, the server will notify the player.  The message will contain all of the
information needed for the player to choose and execute a legal move.  In
response, the player must send back an `Execute Move` request with the id of
its chosen move.  (The player may also defer to the server's judgement and
issue an `Execute Optimal Move` request instead.) In a ``STANDARD`` mode game,
all moves will be for a single card, and that is the card that the player has
drawn.  In an ``ADULT`` mode game, legal moves will span all of the cards in
the player's hand and so the drawn card will be unset.  The player should
assume that the state of the game board matches what was received in the most
recent `Game State Change` message.

Example message::

    {
      "message": "GAME_PLAYER_TURN",
      "context": {
        "handle": "leela",
        "game_id": "f13b405e-36e5-45f3-a351-e45bf487acfe",
        "drawn_card": "CARD_APOLOGIES",
        "moves": {
          "a9fff13fbe5e46feaeda87382bf4c3b8": {
            "move_id": "a9fff13fbe5e46feaeda87382bf4c3b8",
            "card": "CARD_APOLOGIES",
            "actions": [
              {
                "start": {
                  "color": "RED",
                  "id": "1",
                  "start": false,
                  "home": false,
                  "safe": 3,
                  "square": null
                },
                "end": {
                  "color": "RED",
                  "id": "1",
                  "start": false,
                  "home": false,
                  "safe": null,
                  "square": 10
                }
              },
              {
                "start": {
                  "color": "YELLOW",
                  "id": "3",
                  "start": false,
                  "home": false,
                  "safe": null,
                  "square": 10
                },
                "end": {
                  "color": "YELLOW",
                  "id": "3",
                  "start": false,
                  "home": false,
                  "safe": null,
                  "square": 11
                }
              }
            ],
            "side_effects": [
              {
                "start": {
                  "color": "BLUE",
                  "id": "2",
                  "start": false,
                  "home": false,
                  "safe": null,
                  "square": 32
                },
                "end": {
                  "color": "BLUE",
                  "id": "2",
                  "start": true,
                  "home": false,
                  "safe": null,
                  "square": null
                }
              },
              {
                "start": {
                  "color": "GREEN",
                  "id": "0",
                  "start": false,
                  "home": true,
                  "safe": null,
                  "square": null
                },
                "end": {
                  "color": "GREEN",
                  "id": "0",
                  "start": false,
                  "home": false,
                  "safe": null,
                  "square": 12
                }
              }
            ]
          }
        }
      }
    }


