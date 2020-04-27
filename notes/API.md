# Apologies Server Design 

## Periodic Checks

Periodic checks need somewhere to run.  The initial design is for a single
server that does not horizontally scale, so there is an obvious place to run
these checks. A future design that is intended to horizontally scale will need
a separate scheduling component.

### Idle Game Check

On a periodic basis, the server will check how long it has been since the most
recent activity for each tracked game.  A game which exceeds the idle threshold
will be marked as idle, triggering an _Game Idle_ event.  A game which remains
idle and exceeds the inactive threshold will be terminated, triggering a _Game
Inactive_ event.  

### Idle Player

On a periodic basis, the server will check how long it has been since the most
recent activity for each registered player.  A player which exceeds the idle
threshold but is not disconnected will be marked as idle, triggering an _Player
Idle_ event.  A player which exceeds the idle threshold and is disconnected, or
which was already idle and exceeds the inactive threshold, will be terminated,
triggering a _Player Inactive_ event.

### Obsolete Game

On a periodic basis, the server will check how long it has been since each
completed or cancelled game has finished.  A game which exceeds the game
history retention threshold will be marked as obsolete, triggering a _Game
Obsolete_ event.

## Client Requests

All client requests, except the original _Register Player_ request, must
contain an `Authorization` header including the player id returned from the
_Player Registered_ event:

```
Authorization: Player d669c200-74aa-4deb-ad91-2f5c27e51d74
```

In all cases, if the request is syntactically invalid, if the arguments are
illegal, or if the request fails for some other reason, a _Request Failed_
event will be generated, containing as much context as possible.

### Register Player

A player registers by providing a handle to be known by.  This triggers a
_Player Registered_ event.  All registered players are public, meaning that
their handle is visible via the _Registered Players_ event.  There is no
authentication as part of the registration process. Any player can choose any
handle that is not currently in use.  The system may reject new user
registrations if the handle is already in use or if the user registration limit
has been reached, triggering a _Request Failed_ event with context.  Successful
registration initializes the player's last active timestamp and marks the
player as active.  

Example request:

```json
{
  "message": "REGISTER_PLAYER",
  "context": {
    "handle": "leela"
  }
}
```

### Reregister Player

If a player has become disconnected, but still has access to its player id from
the _Registration Completed_ event, it may re-register and get access to its
existing handle by providing the player id in the `Authentication` header as
for any other request.  This works as long as there has not yet been a _Player
Inactive_ event generated for the player.  Behavior is equivalent to the
_Register Player_ request.  Successful re-registration resets the player's last
active timestamp and marks the player as active and connected.

Example request:

```json
{
  "message": "REREGISTER_PLAYER"
}
```

### Unregister Player

A player may unregister at any time.  Once unregistered, the player's handle is
available to be registered by another player.  If the player is currently
playing a game, unregistering will trigger a _Game Player Change_ event for
players in that game and might potentially result in a _Game Cancelled_ event
if the game is no longer viable.

Example request:

```json
{
  "message": "UNREGISTER_PLAYER"
}
```

### List Players

Any registered player may request a list of currently registered players.  This
triggers the _Registered Players_ event for the sender only.  Receipt of this
message resets the sender's last active timestamp and marks the sender as
active.

Example request:

```json
{
  "message": "LIST_PLAYERS"
}
```

### Advertise Game

A registered player may advertise exactly one game, triggering a _Game
Advertised_ event.  The advertised game may be for 2-4 players, and may be
"public" (anyone can join) or "private" (only invited players may join).  Even
though anyone can join a public game, it may also have a list of invited
players.  A _Game Invitation_ event is triggered for each invited player.  A
player may only advertise a game if it is not already playing another game.
The list of invited players is not validated; it can include any handle, even
the handle of a player which is not currently registered.  The player which
advertises a game will immediately be marked as having joined that game,
triggering a _Game Joined_ event.  The system may reject an advertised game if
it is invalid or if the system-wide game limit has been reached. Receipt of
this message resets the sender's last active timestamp and marks the sender as
active.

Example requests:

```json
{
  "message": "ADVERTISE_GAME",
  "context": {
    "name": "Leela's Game",
    "mode": "STANDARD",
    "players": 3,
    "visibility": "PUBLIC",
    "invited_handles": [ ]
  }
}
```

```json
{
  "message": "ADVERTISE_GAME",
  "context": {
    "name": "Bender's Game",
    "mode": "ADULT",
    "players": 2,
    "visibility": "PRIVATE"
    "invited_handles": [ "bender", "hermes", ]
  }
}
```

### List Available Games

A registered player may request a list of available games, triggering an
_Available Games_ event.  The result will include all public games and any
private games the player has been invited to (by handle), but will be
restricted to include only games that have not started yet.  Receipt of this
message resets the sender's last active timestamp and marks the sender as
active.

Example request:

```json
{
  "message": "LIST_AVAILABLE_GAMES"
}
```

### Join Game

A registered player that is not currently playing or advertising another game
may choose to join any available game returned from the _Available Games_
event, triggering a _Game Joined_ event.  The request will be rejected with a
_Request Failed_ event if the player has joined another game already, if the
game is no longer being advertised, if the game has already been started, or if
the game is private and the player has not been invited to join it.  If this
player completes the number of players advertised for the game, then the game
will be started immediately and a _Game Started_ event will be triggered.
Receipt of this message resets the sender's last active timestamp and marks the
sender as active, and also resets the game's last active timestamp and marks
the game as active.

Example request:

```json
{
  "message": "JOIN_GAME",
  "context": {
    "game_id": "f13b405e-36e5-45f3-a351-e45bf487acfe"
  }
}
```

### Quit game

A registered player that is currently playing a game may quit that game, even
if the game is not finished.  This will trigger a _Game Player Change_ event for
the game.  When a player leaves a game, the game might no longer be viable.  In
that case, the game might be cancelled, triggering a _Game Cancelled_ event.  If
the game continues to be viable, the player who quit will simply be ignored for
future turns.  Receipt of this message resets the sender's last active
timestamp and marks the sender as active, and also resets the game's last
active timestamp and marks the game as active.

Example request:

```json
{
  "message": "QUIT_GAME"
}
```

### Start Game

The registered player that advertised a game may start it at any time,
triggering a _Game Started_ event. At the point the game is started, if fewer
players have joined than were requested when advertising the game, the
remainder of the player slots will be filled out with a non-user (programmatic)
player managed by the game engine.  

Example request:

```json
{
  "message": "START_GAME"
}
```

### Cancel Game

The registered player that advertised a game may cancel it at any time, either
before or after the game has started.  A _Game Cancelled_ event will be
triggered.  Receipt of this message resets the sender's last active timestamp
and marks the sender as active.

Example request:

```json
{
  "message": "CANCEL_GAME"
}
```

### Execute Move

When a player has been notified that it is their turn via the _Game Player
Turn_ event, it must choose a move from among the legal moves provided in the
event, and request to execute that move by id.  When a move has been completed,
this triggers one of several other events depending on the state of the game
(potentially a _Game State Change_ event, a _Game Player Turn_ event, a _Game
Completed_ event, etc.).  The request will be rejected with a _Request Failed_
event if the player is not playing the indicated game, if the game has been
cancelled or completed, if it is not currently the player's turn, or if the
player attempts to execute an illegal move.  Receipt of this message resets the
sender's last active timestamp and marks the sender as active, and also resets
the game's last active timestamp and marks the game as active.

Example request:

```json
{
  "message": "EXECUTE_MOVE",
  "context": {
    "move_id": "4"
  }
}
```

### Retrieve Game State

The server will normally push the game state to each player that is associated
with a game whenever the state changes. However, at any time a player may
request the current game state to be pushed again, triggering a _Game State
Change_ event for the sender only.  Receipt of this message resets the sender's
last active timestamp and marks the sender as active, and also resets the
game's last active timestamp and marks the game as active.

Example request:

```json
{
  "message": "RETRIEVE_GAME_STATE"
}
```

### Send Message

Any registered player may send a short message to one or more other players,
identified by handle, triggering a _Player Message Received_ event.  If the
recipient's current status allows the message to be delivered, it will be
delivered immediately.  This facility is intended to provide a chat-type
feature, and the maximum size of a message may be limited.  Receipt of this
message resets the sender's last active timestamp and marks the sender as
active.

Example request:

```json
{
  "message": "SEND_MESSAGE",
  "context": {
    "message": "Hello!",
    "recipient_handles": [ "hermes", "nibbler" ]
  }
}
```

## Server Events

Each server event is associated with a particular situation on the back end.
When triggered, some server events generate a message to one or more players.
Other events only change internal server state, or trigger other events.

### Server Shutdown

State is maintained across server restarts.  When a server shuts down, users
remain registered and games remain in-progress.  At shutdown, the server will
send a message to all players, so each player has the opportunity to
re-register later when the server comes back up.

```json
{
  "message": "SERVER_SHUTDOWN"
}
```

### Request Failed

This event is triggered if a player request is syntactically invalid, if the
arguments are illegal, or if the request fails for some other reason.   The
message provides context to the sender, telling them what happened.

Example message:

```json
{
  "message": "REQUEST_FAILED",
  "context": {
    "reason": "USER_LIMIT",
    "comment": "The registered user limit has been reached; please try again later"
  }
}
```

### Registered Players

This event returns information about all registered players.  Returned
information includes each player's handle, their registration date, and current
status.

Example message:

```json
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
```

### Available Games

This event notifies a player about games that the player may join.  The result
will include all public games and any private games the player has been invited
to (by handle), but will be restricted to include only games that have not
started yet. 

Example message:

```json
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
        "invited": true
      }
    ]
  }
}
```

### Player Registered

This event is triggered when a player successfully registers their handle.

Example message:

```json
{
  "message": "PLAYER_REGISTERED",
  "context": {
    "player_id": "8fc4a03b-3e4d-438c-a3fc-b6913e829ab3",
  }
}
```

### Player Disconnected

A player may become disconnected from the server without explicitly
unregistering.  In this case, the player will be marked as disconnected and
idle, and a _Game Player Change_ event will be triggered for any game the
player has joined.  No events will be sent to the player as long as it remains
in a disconnected state.  


### Player Idle

This event is triggered when the _Idle Player Check_ determines that a player
has been idle for too long.  This notifies the player that it is idle and at
risk of being terminated.

Example message:

```json
{
  "message": "PLAYER_IDLE"
}
```

### Player Inactive

This event is triggered when the _Idle Player Check_ determines that a
disconnected player has exceeded the idle threshold, or an idle player has
exceeded the inactive threshold.  The server will immediately unregister the
player.  If the player is still connected, the server will also notify the
player that it is inactive before unregistering it.

Example message:

```json
{
  "message": "PLAYER_INACTIVE"
}
```

### Player Message Received

When a registered player sends a _Send Message_ request to the server, the
server will notify recipients about the message.  Messages will be delivered to
all registered and connected users, regardless of whether those recipients are
playing a game with the sender.

Example message:

```json
{
  "message": "PLAYER_MESSAGE_RECEIVED",
  "context": {
    "sender_handle": "leela",
    "recipient_handles": [ "hermes", "nibbler", ],
    "message": "Hello!"
  }
}
```

### Game Advertised

This event is triggered when a new game is advertised.  The message is sent to the 
player that advertised the game.

```json
{
  "message": "GAME_ADVERTISED",
  "context": {
    "game_id": "8fb16554-ca00-4b65-a191-1c52cb0eae37",
    "name": "Leela's Game",
    "mode": "STANDARD",
    "advertiser_handle": "leela",
    "players": 3,
    "visibility:": "PUBLIC",
    "invited_handles": [ "bender", "hermes", ]
  }
}
```

### Game Invitation

This event notifies a player about a newly-advertised game that the player has been
invited to.  

Example message:

```json
{
  "message": "GAME_INVITATION",
  "context": {
    "game_id": "8fb16554-ca00-4b65-a191-1c52cb0eae37",
    "name": "Planet Express",
    "mode": "ADULT",
    "advertiser_handle": "leela",
    "players": 4,
    "visibility": "PUBLIC",
  }
}
```

### Game Joined

This event is triggered when a player joins a game.  A player may explicitly
join a game via the _Join Game_ request, or may implicitly join a game when
advertising it.

```json
{
  "message": "GAME_JOINED",
  "context": {
    "game_id": "f13b405e-36e5-45f3-a351-e45bf487acfe"
  }
}
```

### Game Started

This event is triggered when a game is started.  A game may be started
automatically once enough players join, or may be started manually by the
advertising player.  This event also triggers a _Game Player Change_
event that updates the player states.

Example message:

```json
{
  "message": "GAME_STARTED"
}
```

### Game Cancelled

When a game is cancelled or must be stopped prior to completion for some other
reason, the server will trigger this event to notify players.  A game may be
cancelled explicitly by the player which advertised it, or might be cancelled
by the server if it is no longer viable, or if it has exceeded the inactive
timeout.  Cancelled and completed games are tracked for a limited period of
time after finishing.

Example message:

```json
{
  "message": "GAME_CANCELLED",
  "context": {
    "reason": "NOT_VIABLE",
    "comment": "Player nibbler (YELLOW) left the game, and it is no longer viable"
  }
}
```

### Game Completed

When a player wins a game, and the game is thus completed, the server will
notify all players.  Cancelled and completed games are tracked for a limited
period of time after finishing.

Example message:

```json
{
  "message": "GAME_COMPLETED",
  "context": {
    "comment": "Player nibbler (YELLOW) won the game after 46 turns"
  }
}
```

### Game Idle

This event is triggered when the _Idle Game Check_ determines that a game has
been idle for too long.  The generated message notifies all players that the
game is idle and at risk of being cancelled.

Example message:

```json
{
  "message": "GAME_IDLE"
}
```

### Game Inactive

This event is triggered when the _Idle Game Check_ determines that an idle game
has exceeded the inactive threshold.  The server will immediately cancel the
game, triggering a _Game Cancelled_ event.

### Game Obsolete

This event is triggered when the _Obsolete Game Check_ determines that a
finished game has exceeded the game history retention threshold.  The server
will stop tracking the game in the backend data store.  No message is
generated.

### Game Player Change

This event is triggered when a player joins or leaves a game, or when a game
starts.  Players start in the `JOINED` state and move to the `PLAYING` state
when the game starts.  A player might leave a game because they `QUIT`, or
because they were `DISCONNECTED`.  The message is sent to all players in the
game.

Example message:

```json
{
  "message": "GAME_PLAYER_CHANGE",
  "context": {
    "comment": "Player nibbler (YELLOW) quit the game."
    "players": {
      "RED": {
        "handle": "leela",
        "player_type": "HUMAN",
        "player_state": "JOINED"  
      },
      "YELLOW": {
        "handle": "nibbler",
        "player_type": "HUMAN",
        "player_state": "QUIT"
      },
      "BLUE": {
        "handle": null,
        "player_type": "PROGRAMMATIC",
        "player_state": "JOINED"
      },
      "GREEN": {
        "handle": "bender",
        "player_type": "HUMAN",
        "player_state": "DISCONNECTED"
      }
    }
  }
}
```

### Game State Change

When triggered, this event notifies one or more players about the current state
of a game.  The event can be triggered when a player requests the current state
via the _Request Game State_ request, or can be triggered when the state of
the game has changed.  Among other things, the state of the game is considered
to have changed when the game starts, when a player executes a move, when a
player wins the game, or when the game is cancelled or is terminated due to
inactivity.  Each player's view of the game is different; for instance, in an
`ADULT` mode game, a player can only see their own cards, not the cards held by
other players.  

Example message:

```json
{
  "message": "GAME_STATE_CHANGE",
  "context": {
    // TBD
  }
}
```

### Game Player Turn

When the game play engine determines that it is a player's turn to execute a
move, the server will notify the player.  The message will contain all of
the information needed for the player to choose and execute a move, including
the player's view of the game state, the card the player has pulled from the
deck (if any), and the set of legal moves to choose from.  In response, the
player must send back an _Execute Move_ request with its chosen move.

Example message:

```json
{
  "message": "GAME_PLAYER_TURN",
  "context": {
    // TBD
  }
}
```

vim: set ft=markdown ts=2 sw=2:
