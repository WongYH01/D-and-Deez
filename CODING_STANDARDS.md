# Coding standards

Rules a reviewer applies to every diff. Each is a judgement call; cite the rule by its heading.

## Rules cite their source

Every engine rule carries a comment naming what it implements: a section of `docs/rules/srd-5.1-mechanics.md` (`§4.26`) or a ruling (`R7`). The Rulings section at the end of that file overrides the quoted SRD text. A rule with no citation, or a citation that doesn't match the quoted text, is a finding.

## Domain names follow the glossary

Names in code, tool schemas, prompts and error messages use the terms in `GLOSSARY.md` (Turn, Tool round, Character, Combatant, Combat round, Combatant's turn, Roll). The one exception is the tool name `resolve_npc_turns`, fixed by the design document.

## Tools validate before they act

A tool checks every argument against the state tree first, then rolls dice and changes state. An invalid call returns `{"error": ...}` with no Roll recorded and no state changed.

## A Roll is complete when it is recorded

Set a Roll's `target` and `outcome` before calling `dice.record`: recording emits the `roll` event, and what is emitted is what the player sees. Use `d20_test(..., record=False)` when the outcome depends on the result.

## State changes go through the state tree

Tools change ORM objects loaded for the Turn; only the orchestrator commits (ADR 0002). Replace JSON columns (`conditions`, `flags`, `feature_uses`, `Encounter.state`) with a new value instead of mutating them in place, so SQLAlchemy sees the change.

## Engine tests use the two seams

Tests call tools through `dispatch` with scripted dice (Seam 1) or run the orchestrator with a fake Claude client (Seam 2). Expected numbers come from the SRD text or worked dice, never recomputed the way the code does. A test of a rule names the section or ruling it covers.
