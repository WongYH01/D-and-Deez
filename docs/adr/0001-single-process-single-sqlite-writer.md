# One process, one SQLite writer

The web server, turn orchestrator and background worker run in a single Python process in one container, and every database write goes through one data layer in the engine. We chose this over separate worker processes or a server database because the game has one player on modest hardware, such as a Pi 5: a single writer removes SQLite lock contention and job races without needing Postgres or a job queue. Background jobs run one at a time in the same process for the same reason.

Amended in M4: Turns run on one thread and jobs (bible generation, Recaps) on a second, so a slow job never delays a Turn. Both write only through the data layer, make every Claude call outside a transaction and keep writes short, with `busy_timeout` covering the rare overlap.
