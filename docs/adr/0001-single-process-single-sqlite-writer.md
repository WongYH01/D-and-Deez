# One process, one SQLite writer

The web server, turn orchestrator and background worker run in a single Python process in one container, and every database write goes through one data layer in the engine. We chose this over separate worker processes or a server database because the game has one player on a Raspberry Pi 5: a single writer removes SQLite lock contention and job races without needing Postgres or a job queue. Background jobs run one at a time in the same process for the same reason.
