# Coding standards

Rules a reviewer applies to every diff. Each is a judgement call; cite the rule by its heading.

## Rules cite their source

Every engine rule carries a comment naming what it implements: a section of `docs/rules/srd-5.1-mechanics.md` (`§4.26`) or a ruling (`R7`). The Rulings section at the end of that file overrides the quoted SRD text. A rule with no citation, or a citation that doesn't match the quoted text, is a finding. New engine behaviour that no section or ruling covers gets a new `Rn` entry in the Rulings section marked "Proposed (issue #N); awaiting owner confirmation", and the PR body lists it.

Story-director behaviour (bible checks, story tools, the Director block, Endings) cites the design document's Story design section instead (`Story design §6`). Behaviour that differs from the originating issue or that section is a finding unless the same change updates the design document and the PR body lists the difference.

## Domain names follow the glossary

Names in code, tool schemas, prompts and error messages use the terms in `GLOSSARY.md` (Turn, Tool round, Character, Combatant, Combat round, Combatant's turn, Roll). The one exception is the tool name `resolve_npc_turns`, fixed by the design document.

## Tools validate before they act

A tool checks every argument against the state tree first, then rolls dice and changes state. An invalid call returns `{"error": ...}` with no Roll recorded and no state changed.

## A Roll is complete when it is recorded

Set a Roll's `target` and `outcome` before calling `dice.record`: recording emits the `roll` event, and what is emitted is what the player sees. Use `d20_test(..., record=False)` when the outcome depends on the result.

## State changes go through the state tree

Tools change ORM objects loaded for the Turn; only the orchestrator commits a Turn (ADR 0002). Work outside a Turn (direct actions such as equip and retire, Session open and close, the bible and Recap jobs) commits its own short transaction, and a direct action that changes game state holds the server's busy lock so it never lands mid-Turn. Replace JSON columns (`conditions`, `flags`, `feature_uses`, `Encounter.state`) with a new value instead of mutating them in place, so SQLAlchemy sees the change.

## Engine tests use the four seams

Tests call tools through `dispatch` with scripted dice (Seam 1), run the orchestrator with a fake Claude client (Seam 2), start a Campaign through `start_campaign` with a fake Claude client that returns bible tool calls (Seam 3), or drive the HTTP API through `TestClient` on an app built by `create_app` with fake Claude clients, a temporary database and backups folder, `inline` work and a test subscriber on the broadcaster (Seam 4). Expected numbers come from the SRD text or worked dice, never recomputed the way the code does. A test of a rule names the section or ruling it covers.

## UI state tolerates any arrival order

The browser sees events, HTTP responses and fetches in whatever order the network delivers them: an event can beat the `POST /action` response that started its Turn, a `GET /state` or `GET /log` response can land after later events, and a reconnect misses events. Trace each change to `src/web` through every order; a reducer test covers each order the code relies on. A state that one unlucky order leaves stuck (input locked forever, a Turn's lines lost) is a finding.
