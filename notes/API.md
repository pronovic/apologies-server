# Apologies Server Events and Flow

## Periodic Checks

One problem with periodic checks like this is that we need to know where
to run them.  If there's only one server that doesn't horizontally scale,
then it's no problem at all.  But, if we want to be able to horizontally
scale, then these jobs need to run on exactly one node.  Not sure how to
handle that.

### Idle Game Check

On a periodic basis, the server will check how long it has been since the most
recent activity for each tracked game.  A game which exceeds the idle threshold
will be marked as idle, triggering an Game Idle event.  A game which remains
idle and exceeds the inactive threshold will be terminated, triggering a Game
Inactive event.  

### Idle Player

On a periodic basis, the server will check how long it has been since the most
recent activity for each registered player.  A player which exceeds the idle
threshold but is not disconnected will be marked as idle, triggering an Player
Idle event.  A player which exceeds the idle threshold and is disconnected, or
which was already idle and exceeds the inactive threshold, will be terminated,
triggering a Player Inactive event.

### Obsolete Game

On a periodic basis, the server will check how long it has been since each
completed or cancelled game has finished.  A game which exceeds the game
history retention threshold will be marked as obsolete, triggering a Game
Obsolete event.

## Client Requests

### Register

A player registers by providing a handle to be known by.  The server returns a
player identifier.  All registered players are public, meaning that their
handle is visible via the List Players request.  There is no authentication as
part of the registration process. Any player can choose any handle that is not
currently in use.  The system may reject new user registrations if the user
registration limit has been reached.  Successful registration initializes the
player's last active timestamp and marks the player as active.  Upon
registration, if there any advertised, private games waiting to start which
invite the new player's handle, then a Game Available event is triggered to the
new player.

Request:

```json
{
  "handle": "leela"
}
```

Response: **200 OK**

```json
{
  "player_id": "8fc4a03b-3e4d-438c-a3fc-b6913e829ab3"
}
```

### Reregister

If a player has become disconnected, but still has access to its player id, it
may re-register and get access to its existing handle.  This marks the player
as active, and the player will start receiving events again.  However, a
disconnected player may not re-join a game that it was playing when
disconnected.  Receipt of this message resets the sender's last active
timestamp and marks the sender as active and connected.

Request:

```json
{
  "player_id": "8fc4a03b-3e4d-438c-a3fc-b6913e829ab3"
}
```

Response: **200 OK**

```json
{
  "player_id": "8fc4a03b-3e4d-438c-a3fc-b6913e829ab3"
}
```

### Unregister

A player unregisters by providing its player id.  Once unregistered, the
player's handle is available to be registered by another player.  If the player
is currently playing a game, unregistering will trigger a Player Left Game
event.

Request:

```json
{
  "player_id": "8fc4a03b-3e4d-438c-a3fc-b6913e829ab3"
}
```

Response: **200 OK**


### List Players

Any registered player may request a list of currently registered players,
potentially filtering or sorting that list according to their preferences.  The
returned information will include the each registered player's handle, the
registration date, and current status (connected/disconnected, active/idle,
waiting/joined/playing).  Receipt of this message resets the sender's last
active timestamp and marks the sender as active.

Request:

```json
{
  "player_id": "8fc4a03b-3e4d-438c-a3fc-b6913e829ab3"
}
```

Response: **200 OK**

```json
[
  {
    "handle": "leela",
    "registration_date": "2020-04-23 08:42:31,443",
    "last_active_date": "2020-04-23 08:53:19,116",
    "connection_state": "CONNECTED",
    "activity_state": "ACTIVE",
    "play_state": "JOINED"
    "game_id": null
  },
  {
    "handle": "nibbler",
    "registration_date": "2020-04-23 09:10:00,116",
    "last_active_date": "2020-04-23 09:13:02,221",
    "connection_state": "DISCONNECTED",
    "activity_state": "IDLE",
    "play_state": "PLAYING",
    "game_id": "166a930b-66f0-4e5a-8611-bbbf0a441b3e"
  },
  {
    "handle": "hermes",
    "registration_date": "2020-04-23 10:13:03,441",
    "last_active_date": "2020-04-23 10:13:03,441",
    "connection_state": "CONNECTED",
    "activity_state": "ACTIVE",
    "play_state": "WAITING",
    "game_id": null
  },
]
```

### Advertise Game

A registered player may advertise exactly one game.  The advertised game may be
for 2-4 players, and may be "public" (anyone can join) or "private" (only
invited players may join).  Even though anyone can join a public game, it may
also have a list of invited players.  A Game Available event is triggered for
any game with invited players.  A player may only advertise a game if it is not
already playing another game.  The list of invited players is not validated; it
can include any handle, even the handle of a player which is not currently
registered.  The player which advertises a game will immediately be marked as
having joined that game.  The system may reject a game advertisement if the
game limit has been reached.  Receipt of this message resets the sender's last
active timestamp and marks the sender as active.

Request:

```json
{
  "player_id": "8fc4a03b-3e4d-438c-a3fc-b6913e829ab3"
  "name": "Private Game",
  "players": 3,
  "private": true,
  "invited_handles": [ "bender", "hermes", ]
}
```

```json
{
  "player_id": "8fc4a03b-3e4d-438c-a3fc-b6913e829ab3"
  "name": "Public Game",
  "players": 2,
  "private": false
}
```

Response: **200 OK**

```json
{
  "game_id": "8fb16554-ca00-4b65-a191-1c52cb0eae37"
}
```

### List Available Games

A registered player may request a list of available games.  The returned list
will include all public games and any private games the player has been invited
to (by handle), but will be restricted to include only games that have not
started yet.  Receipt of this message resets the sender's last active timestamp
and marks the sender as active.

Request:

```json
{
  "player_id": "8fc4a03b-3e4d-438c-a3fc-b6913e829ab3"
}
```

Response: **200 OK**

```json
[
  {
    "game_id": "8fb16554-ca00-4b65-a191-1c52cb0eae37",
    "name": "Planet Express",
    "advertiser": "leela",
    "players": 4,
    "available": 2,
    "visibility": "PUBLIC",
    "invited": true
  }
]
```

### Join Game

A registered player that is not currently playing or advertising another game
may choose to join any available game returned from the List Available Games
request.  The request will be rejected if the game is no longer being
advertised, if the game has already been started, or if the game is private and
the player has not been invited to join it.  If this player completes the
number of players advertised for the game, then the game will be started
immediately and a Game Started event will be triggered.  Receipt of this
message resets the sender's last active timestamp and marks the sender as
active, and also resets the game's last active timestamp and marks the game as
active.

Request:

```json
{
  "player_id": "8fc4a03b-3e4d-438c-a3fc-b6913e829ab3",
  "game_id": "f13b405e-36e5-45f3-a351-e45bf487acfe"
}
```

Response: **200 OK**

### Quit game

A registered player that is currently playing a game may quit that game, even
if the game is not finished.  This will trigger a Player Left Game event for
the game.  When a player leaves a game, the game might no longer be viable.  In
that case, the game might be cancelled, triggering a Game Cancelled event.  If
the game continues to be viable, the player who quit will simply be ignored for
future turns.  Receipt of this message resets the sender's last active
timestamp and marks the sender as active, and also resets the game's last
active timestamp and marks the game as active.

Request:

```json
{
  "player_id": "8fc4a03b-3e4d-438c-a3fc-b6913e829ab3",
  "game_id": "f13b405e-36e5-45f3-a351-e45bf487acfe"
}
```

Response: **200 OK**

### Start Game

The registered player that advertised a game may start it at any time, triggering
a Game Started event. At the point the game is started, if fewer players have
joined than were requested when advertising the game, the remainder of the
player slots will be filled out with a non-user (programmatic) player managed
by the game engine.  

Request:

```json
{
  "player_id": "8fc4a03b-3e4d-438c-a3fc-b6913e829ab3",
  "game_id": "f13b405e-36e5-45f3-a351-e45bf487acfe"
}
```

Response: **200 OK**

### Cancel Game

The registered player that advertised a game may cancel it at any time, either
before or after the game has started.  A Game Cancelled event will be
triggered.  All players that have joined the game will be notified that the
game has been cancelled.  Receipt of this message resets the sender's last active
timestamp and marks the sender as active.

Request:

```json
{
  "player_id": "8fc4a03b-3e4d-438c-a3fc-b6913e829ab3",
  "game_id": "f13b405e-36e5-45f3-a351-e45bf487acfe"
}
```

Response: **200 OK**

### Execute Move

When a player has been notified that it is their turn, it must choose a move
from among the legal moves provided in the notification, and request to execute
that move by id.  The request will be rejected if the player is not playing the
indicated game, if the game has been cancelled or completed, if it is not
currently the player's turn, or if the player attempts to execute an illegal
move.  When a move has been completed, this triggers one of several other
events depending on the state of the game (potentially a Current State event, a
Your Turn event, a Game Completed event, etc.).  Receipt of this message resets
the sender's last active timestamp and marks the sender as active, and also
resets the game's last active timestamp and marks the game as active.

Request:

```json
{
  "player_id": "8fc4a03b-3e4d-438c-a3fc-b6913e829ab3",
  "move_id": 4
}
```

Response: **200 OK**

### Retrieve Game State

The server will normally push the game state to each player that is associated
with a game. However, at any time a player may request the current game state
to be pushed again, triggering a Current State event.  Receipt of this message
resets the sender's last active timestamp and marks the sender as active, and
also resets the game's last active timestamp and marks the game as active.

Request:

```json
{
  "player_id": "8fc4a03b-3e4d-438c-a3fc-b6913e829ab3",
  "game_id": "f13b405e-36e5-45f3-a351-e45bf487acfe"
}
```

Response: **200 OK**

### Send Message

Any registered player may send a short message to one or more other players,
identified by handle, triggering a Message Received event.  If the recipient's
current status allows the message to be delivered, it will be delivered
immediately.  This facility is intended to provide a chat-type feature, and the
maximum size of a message may be limited.  Receipt of this message resets the
sender's last active timestamp and marks the sender as active.

Request:

```json
{
  "player_id": "8fc4a03b-3e4d-438c-a3fc-b6913e829ab3",
  "recipient_handles": [ "hermes", "nibbler", ],
  "message": "Hello!"
}
```

Response: **200 OK**

## Server Events

### Game Available

If a new private game has been advertised which explicitly invites a player,
and if that player is registered, then the server will notify the player about
the newly-advertised game.  This event is also triggered when a player
registers, and they have been invited to a game which has not yet started.

Published data:

```json
{
  "event": "GAME_AVAILABLE",
  "context": [
    {
      "game_id": "8fb16554-ca00-4b65-a191-1c52cb0eae37",
      "name": "Planet Express",
      "advertiser": "leela",
      "players": 4,
      "available": 2,
      "visibility": "PUBLIC",
      "invited": true
    }
  ]
}
```

### Message Received

When a registered player sends a Send Message request to the server, the server
will notify recipients about the message.  Messages will be delivered to all
registered, connected, and active users, regardless of whether those recipients
are playing a game with the sender.

Published data:

```json
{
  "event": "MESSAGE_RECEIVED",
  "context": {
    "sender_handle": "leela",
    "recipient_handles": [ "hermes", "nibbler", ],
    "message": "Hello!"
  }
}
```

### Current State

Whenever the current state of a game changes, the server will notify all
players in the game about the current state of the game.  Among other things,
the state of the game is considered to have changed when a player joins or
quits the game, when the game starts, when a player executes a move, when a
player wins the game, or when the game is cancelled or is terminated due to
inactivity.  Each player's view of the game is different; for instance, in an
ADULT mode game, a player can only see their own cards, not the cards held by
other players.  

Published data:

```json
{
  "event": "CURRENT_STATE",
  "context": {
  }
}
```

### Your Turn

When the game play engine determines that it is a player's turn to execute a
move, the server will notify the player.  The notification will contain all of
the information needed for the player to choose and execute a move, including
the player's view of the game state, the card the player has pulled from the
deck (if any), and the set of legal moves to choose from.  In response, the
player must send back an Execute Move request with its chosen move.

Published data:

```json
{
  "event": "YOUR_TURN",
  "context": {
  }
}
```

### Game Started

When a game is started, the server will update the state of the game and then
trigger a Current State event to notify all players.  A game may be started
automatically once enough players join, or may be started manually by the
advertising player.  For a game that is started manually, if fewer players have
joined than were requested when advertising the game, the remainder of the
player slots will be filled out by non-user (programmatic) players managed by
the game engine.

### Game Cancelled

When a game is cancelled or must be stopped prior to completion for some other
reason, the server will update the state of the game and then trigger a Current
State event to notify players.  A game may be cancelled explicitly by the
player which advertised it, or might be cancelled by the server if it is no
longer viable, or if it has exceeded the inactive timeout.  Cancelled and
completed games are tracked for a limited period of time after finishing.

Published data:

```json
{
  "event": "GAME_CANCELLED",
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

Published data:

```json
{
  "event": "COMPLETED",
  "context": {
    "reason": "WON",
    "comment": "Player nibbler (YELLOW) won the game after 46 turns"
  }
}
```

### Game Idle

This event is triggered when the Idle Game Check determines that a game has
been idle for too long.  The server will notify all players that the game is
idle and at risk of being cancelled.

Published data:

```json
{
  "event": "GAME_IDLE"
}
```

### Game Inactive

This event is triggered when the Idle Game Check determines that an idle game
has exceeded the inactive threshold.  The server will immediately cancel the
game, triggering a Game Cancelled event.

### Game Obsolete

This event is triggered when the Obsolete Game Check determines that a finished
game has exceeded the game history retention threshold.  The server will stop
tracking the game in the backend data store.

### Player Disconnected

A player may become disconnected from the server without explicitly
unregistering.  In this case, the player will be marked as disconnected and
idle, and a Player Left Game event will be triggered for any game the player
has joined.  No events will be sent to the player as long as it remains in a
disconnected state.  

### Player Idle

This event is triggered when the Idle Player Check determines that a player has
been idle for too long.  The server will notify the player that it is idle and
at risk of being terminated.

Published data:

```json
{
  "event": "PLAYER_IDLE"
}
```

### Player Inactive

This event is triggered when the Idle Player Check determines that a
disconnected player has exceeded the idle threshold, or an idle player has
exceeded the inactive threshold.  The server will immediately unregister the
player.  If the player is still connected, the server will also notify the
player that it is inactive before unregistering it.

Published data:

```json
{
  "event": "PLAYER_INACTIVE"
}
```

### Player Left Game

A player may leave a game by being disconnected, by unregistering, or by
explicitly quitting the game.  Those conditions trigger this event.  When the
event is handled, the player will be removed from the game.  At that point, the
the game might no longer be viable (i.e. a 2-player game with 1 player left is
not viable).  If that is the case, then the Game Cancelled event will be
triggered.  Otherwise, a notification will be sent to all players.  Going
forward, the player which left will be ignored when its turn arrives.

Published data:

```json
{
  "event": "PLAYER_LEFT_GAME",
  "context": {
    "player_handle": "nibbler",
    "player_color": "YELLOW",
    "reason": "QUIT",
    "comment": "Player nibbler (YELLOW) quit the game."
  }
}
```

### Server Shutdown

State is maintained across server restarts.  When a server shuts down, users
remain registered and games remain in-progress.  At shutdown, the server will
publish a notification to all players, so the player has the opportunity to
re-register later when the server comes back up.

```json
{
  "event": "SERVER_SHUTDOWN"
}
```
