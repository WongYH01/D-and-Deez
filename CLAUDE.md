# Pi Dungeon Master

Single-player, text-based D&D 5e web app. Claude narrates; the app's code referees rules and plans the story. Design: `docs/Pi Dungeon Master — Design Document.md`.

Every instruction to run `code-review` means `mattpocock-skills:code-review` (Standards and Spec axes); the bare `code-review` is the built-in one. Give it the issue number and the commit your work started from, so it reviews only your change. Commit first: it diffs `<start>...HEAD`, so uncommitted work gives an empty diff.

Tests run on the host in the repo's venv: `.venv/Scripts/pytest` (Windows) or `.venv/bin/pytest`. The Docker image has no test dependencies. Web UI (`src/web`, React + Vite): `npm test` (Vitest), `npm run typecheck` and `npm run dev` there; run them with `npm --prefix src/web <script>` so the shell stays in the repo root. UI tests have no jest-dom matchers: assert with `toBeTruthy()` and DOM properties (`.id`, `.textContent`). UI test stubs for `fetch` and `EventSource`: `src/web/src/test/server.ts`. Add UI components with `npx shadcn@4.23.0 add <name>` in `src/web`, then point the new files' `cn` imports at `@/lib/utils` (the CLI writes `from "cn"`) and check `git status` from the repo root: the CLI edits files outside `src/web`.

Change every file with Edit or Write, including a one-line fix or a rename across files, and never with a `python - <<E` or `sed` script: a heredoc turns a `\n` in your text into a real newline (a syntax error), drops a `\` line continuation silently and writes CRLF on Windows.

After editing `dependencies` in `pyproject.toml`, run `.venv/Scripts/pip install -e .[dev]`.

New table: model in `src/pidm/models.py`, hand-written migration in `src/pidm/migrations/versions`, seeding in `_seed` and `clear_story` (`src/pidm/campaign.py`, which lists every Campaign-owned table), context in `user_message` (`src/pidm/prompts.py`). A table keyed by a child row, such as the `scene_vec` virtual table (created by its migration, written in `src/pidm/recall.py`), is not Campaign-owned and stays out of `clear_story`. The session factory has autoflush off, so a query misses rows added earlier in the Turn: read the Campaign's relationship lists and `flush()` after adding.

A mechanic the SRD does not spell out gets a numbered ruling in `docs/rules/srd-5.1-mechanics.md` (mark it Proposed until the owner confirms) and is cited as `R<n>` in code comments.

Tool registry: the `TOOLS` dict at the end of `src/pidm/tools.py`; story tools live in `src/pidm/story.py`. A new Character action reuses `_require_turn`, `_use_action`, `_use_bonus`, `_character_save`, `_combatant_save`, `d20_test` and `ask_roll`. Test seams and `FakeClaude`: `tests/conftest.py` (seams listed in `CODING_STANDARDS.md`).

Server: `create_app` in `src/pidm/app.py` (Seam 4, tests in `tests/test_server.py`; the `server` and `make_server` fixtures and the `create`, `start` and `act` helpers, where `act()` runs the Turn synchronously, are in `tests/conftest.py`). `fixture_bible` in `tests/conftest.py`: the Main clock is `clock.tide` (6 segments, so two 3-segment ticks fill it); it is raw JSON without model defaults, so compare a saved bible with `Bible.model_validate(fixture_bible()).model_dump()`. The opening and resume Turns are committed Turns whose `player_text` is `OPENING` or `RESUME`: exclude them when asking whether the player acted. Recaps: `src/pidm/recap.py`. Jobs (recaps, replans) run on the job thread in queue order, and the next Session's opening waits behind them while holding `busy`: a job never takes `busy` (it would deadlock), and `src/pidm/replan.py` explains why a job never overlaps a Turn.

Event contract for the UI: payloads in the design document's API surface section; emit order in `TurnOrchestrator._run` (`src/pidm/orchestrator.py`): `roll`*, `narration_delta`, `state_changed`, `turn_done`, or `error` on failure. Endings: `ending_met` and `end` in `src/pidm/story.py`; `_run` applies Defeat and Fallen hero after the Narration, and a Victory waits for Claude's `end_campaign`. `running_turn_seq` clears only after `turn_done`, and an event can beat the `POST /action` response. The context (`build` in `_run`) is built once per Turn: a `move_to` changes the next Turn's context, so a test asserts on the first request of the next `act()`.

Check UI changes in a browser with no API key before you commit; jsdom tests cannot see layout, so an issue criterion about width or layout is met only by this check (resize the window to ~375px wide): run `PIDM_FAKE_CLAUDE=1 PIDM_DB=<temp>.sqlite PIDM_BACKUP_DIR=<temp> .venv/Scripts/uvicorn pidm.app:from_env --factory` from the repo root plus `npm run dev` in `src/web`. If port 8000 or 5173 is busy (the Vite proxy targets :8000 only): run `npm run build` in `src/web`, then add `--port 0` to the uvicorn command and read the port from its `Uvicorn running on` log line; it serves the UI at `/`. Stop the servers you start before you finish. After a rebuild, load a new URL (`/?r=1#/play`): a hash change keeps the old bundle. The scripted Turns are described in `src/pidm/devclaude.py`.

## Agent skills

### Issue tracker

Issues and specs live in GitHub Issues for WongYH01/D-and-Deez, via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
