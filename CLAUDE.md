# Pi Dungeon Master

Single-player, text-based D&D 5e web app. Claude narrates; the app's code referees rules and plans the story. Design: `docs/Pi Dungeon Master — Design Document.md`.

Tests run on the host in the repo's venv: `.venv/Scripts/pytest` (Windows) or `.venv/bin/pytest`. The Docker image has no test dependencies. Web UI (`src/web`, React + Vite): `npm test` (Vitest) and `npm run dev` there.

Tool registry: the `TOOLS` dict at the end of `src/pidm/tools.py`; story tools live in `src/pidm/story.py`. Test seams and `FakeClaude`: `tests/conftest.py` (seams listed in `CODING_STANDARDS.md`).

Server: `create_app` in `src/pidm/app.py` (Seam 4, tests in `tests/test_server.py`). Recaps: `src/pidm/recap.py`.

## Agent skills

### Issue tracker

Issues and specs live in GitHub Issues for WongYH01/D-and-Deez, via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
