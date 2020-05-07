# Configuration

Configuration should be stored on disk, separate from the database.  I think
that this is just easier to comprehend than putting it in the database. The
server can periodically refresh configuration from disk, if necessary.  

- total game limit
- in-progress game limit
- registered player limit
- player idle threshold
- player inactive threshold
- game idle threshold
- game inactive threshold
- game history retention threshold

# State

All of this can be maintained in an SQLLite database, possibly using SQLAlchemy
for ORM.  In theory, I can swap out SQLLite for a real database (like
PostgreSQL) sometime later.  That would make it easier to scale horizontally,
at the eexpense of some other complexity in the application (like, where do
scheduled tasks run).  That's something for another time.

What's not clear is where I would store the engine state (the engine and its
underlying Apologies game) in between turns.  I think that the engine may
require a redesign so that it can be instantiated, used once, then torn down
and reinstantiated later.  

It's also not clear that the callback mechanism really works properly for
asynchronous communication.  I mean, it _can_ work, but I think that it
restricts me to a single server that cannot horizontally scale, because
something has to maintain the state to accept the callback.  Now, for the time
being, I am not horizontally scaling (because I want this to be fairly simple)
but it would be nice if the design did not fundamentally preclude scaling.

If I can think of a different way to structure the engine, as a combination of
state and data stored one place, and execution rules stored elsewhere, that
will let me scale more easily.  Each server can then have an engine (or
multiple engines in a pool, or a new engine for each request) and then the
engine would operate on the state to produce the next output result.

I think that before I try to change the model for the engine, I need to
actually write (or at least stub) large parts of the asynchronous websockets
server, so I know what needs to slot in where.  Then, I can go back and
restructure the Apologies library to support it.  I suspect I can maintain
the original interface and implement it in terms of the new code that also
works for an asynchronous archiecture.

## System State

- list of all games
- total number of games (in any state)
- total number of in-progress games (in ADVERTISED or STARTED state)
- list of all registered players
- total number of registered players

## Game State

- game name
- game id
- total number of players
- number of user players
- number of non-user players
- visibility (PUBLIC/PRIVATE)
- invited players
- advertised date
- started date
- completed date
- last active date
- game state (ADVERTISED/STARTED/COMPLETED)
- activity state (ACTIVE/IDLE/INACTIVE)
- completion reason (WON/CANCELLED/NOT_VIABLE/INACTIVE)
- completion comment
- list players who joined the game
- list of players currently playing the game

## Player State

- handle
- player id
- registration date
- last active date
- connection state (CONNECTED/DISCONNECTED)
- activity state (ACTIVE/IDLE/INACTIVE)
- play state (WAITING/JOINED/PLAYING)
- game id
