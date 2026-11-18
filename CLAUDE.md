# Pi Dungeon Master

Single-player, text-based D&D 5e web app. Claude narrates; the app's code referees rules and plans the story. Design: `docs/Pi Dungeon Master — Design Document.md`.

Tests run on the host in the repo's venv: `.venv/Scripts/pytest` (Windows) or `.venv/bin/pytest`. The Docker image has no test dependencies. Web UI (`src/web`, React + Vite): `npm test` (Vitest) and `npm run dev` there. Add UI components with `npx shadcn@4.23.0 add <name>` in `src/web`, then point the new files' `cn` imports at `@/lib/utils` (the CLI writes `from "cn"`) and check `git status` from the repo root: the CLI edits files outside `src/web`.

Tool registry: the `TOOLS` dict at the end of `src/pidm/tools.py`; story tools live in `src/pidm/story.py`. Test seams and `FakeClaude`: `tests/conftest.py` (seams listed in `CODING_STANDARDS.md`).

Server: `create_app` in `src/pidm/app.py` (Seam 4, tests in `tests/test_server.py`). Recaps: `src/pidm/recap.py`.

Event contract for the UI: payloads in the design document's API surface section; emit order in `TurnOrchestrator._run` (`src/pidm/orchestrator.py`): `roll`*, `narration_delta`, `state_changed`, `turn_done`, or `error` on failure. `running_turn_seq` clears only after `turn_done`, and an event can beat the `POST /action` response.

Check UI changes in a browser with no API key: run `PIDM_FAKE_CLAUDE=1 PIDM_DB=<temp>.sqlite PIDM_BACKUP_DIR=<temp> .venv/Scripts/uvicorn pidm.app:from_env --factory` from the repo root plus `npm run dev` in `src/web`. If port 8000 or 5173 is busy (the Vite proxy targets :8000 only): run `npm run build` in `src/web`, then add `--port 0` to the uvicorn command and read the port from its `Uvicorn running on` log line; it serves the UI at `/`. Stop the servers you start before you finish. After a rebuild, load a new URL (`/?r=1#/play`): a hash change keeps the old bundle. The scripted Turns are described in `src/pidm/devclaude.py`.

## Agent skills

### Issue tracker

Issues and specs live in GitHub Issues for WongYH01/D-and-Deez, via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
