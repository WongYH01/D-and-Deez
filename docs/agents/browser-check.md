# Browser check

Run this before you commit a UI change. jsdom tests cannot see layout, so an issue criterion about width or layout is met only by this check. The scripted Turns are described in `src/pidm/devclaude.py`.

1. From the repo root, start the server with no API key: `PIDM_FAKE_CLAUDE=1 PIDM_DB=<temp>.sqlite PIDM_BACKUP_DIR=<temp> .venv/Scripts/uvicorn pidm.app:from_env --factory`. Start `npm run dev` in `src/web`.
2. Port 8000 or 5173 busy (the Vite proxy targets :8000 only): run `npm run build` in `src/web`, add `--port 0` to the uvicorn command, and read the port from its `Uvicorn running on` log line. It serves the UI at `/`.
3. Load the page and resize the window to ~375px wide. After a rebuild, load a new URL (`/?r=1#/play`): a hash change keeps the old bundle.
4. Drive the screen into the state the change shows, and look at it.
5. Stop the servers you started.

Done when you have seen the changed UI at ~375px and no server you started is still running. Say so in the commit or the review hand-off; a check you did not run is a Spec finding.
