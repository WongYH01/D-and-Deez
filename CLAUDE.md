# Pi Dungeon Master

Single-player, text-based D&D 5e web app. Claude narrates; the app's code referees rules and plans the story. Design: `docs/Pi Dungeon Master — Design Document.md`.

Tests run on the host in the repo's venv: `.venv/Scripts/pytest` (Windows) or `.venv/bin/pytest`. The Docker image has no test dependencies.

## Agent skills

### Issue tracker

Issues and specs live in GitHub Issues for WongYH01/D-and-Deez, via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
