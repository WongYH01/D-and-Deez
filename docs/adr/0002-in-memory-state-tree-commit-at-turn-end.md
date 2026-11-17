# In-memory state tree, committed at the end of a Turn

Each Turn loads the Campaign's game state into an in-memory tree of Python objects; tools validate and change only that tree, and the changed parts, the turn row and its Rolls are written in one short transaction when the Turn ends. On failure the tree is discarded and only a failed turn row is saved. We chose this over writing each tool's change straight to SQLite (which leaves partial state on a failed API call) and over a change set layered on SQLite (which forces every tool to query the database and pending changes together). The cost: a crash mid-Turn loses that Turn, and the player retypes the action.

The tree is a SQLAlchemy ORM session opened with `autoflush=False`: tools change ORM objects, `commit()` writes the changed ones, and `rollback()` discards a failed Turn. With autoflush off, nothing reaches SQLite, and no write lock is held, while Claude is being called.
