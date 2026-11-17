"""Terminal loop: `pidm-play --template rogue --setting "dark fantasy" --tone grim`.

Sets up a Campaign (a generated bible, or `--bible PATH` to load a hand-written one), shows the
spoiler-free premise, then plays Turns from stdin until the Campaign ends.
"""

from __future__ import annotations

import argparse
import os
import sys

from pidm.campaign import ATTEMPTS, Setup, SetupError, load_bible, retire, start_campaign
from pidm.claude import AnthropicClient, plan_client
from pidm.db import open_db
from pidm.orchestrator import CampaignEnded, TurnOrchestrator
from pidm.templates import TEMPLATES

ENDINGS = {"victory": "Victory", "defeat": "Defeat", "fallen_hero": "Fallen hero", "retired": "Retired"}


def format_roll(p: dict) -> str:
    line = f"  [{p['purpose']}] {p['expr']} = {p['total']}"
    if p.get("dice"):
        line += f" {p['dice']}"
    if p.get("target") is not None:
        line += f" vs {p['target']}"
    if p.get("outcome"):
        line += f": {p['outcome']}"
    return line


def emit(event: str, payload: dict) -> None:
    if event == "roll":
        print(format_roll(payload), flush=True)
    elif event == "narration_delta":
        print(payload["text"], end="", flush=True)
    elif event == "turn_done":
        print("\n", flush=True)
        if payload.get("ending"):
            print(f"*** The Campaign has ended: {ENDINGS[payload['ending']]}. ***", flush=True)
    elif event == "error":
        print(f"\n! {payload['message']} ({payload['detail']})\n", flush=True)


def _ask(prompt: str) -> str | None:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None


def _setup(factory, args) -> int | None:
    """Start a Campaign and return its Session id, or None if the player accepts no premise."""
    setup = Setup(setting=args.setting, tone=args.tone, length=args.length, lines=args.lines, veils=args.veils,
                  hook=args.hook)
    if args.bible:
        return start_campaign(factory, setup, args.template, args.name, bible=load_bible(args.bible)).id
    client = plan_client()
    for attempt in range(1, ATTEMPTS + 1):
        print("Planning the Campaign...", flush=True)
        sess = start_campaign(factory, setup, args.template, args.name, client=client)
        print(f"\n{sess.campaign.name}\n{sess.campaign.premise}\n")
        answer = _ask("Play this story? [Y/n] ")
        if answer is None:
            return None
        if answer.lower() in ("", "y", "yes"):
            return sess.id
        if attempt < ATTEMPTS:
            print("Planning another story.")
    print("No premise accepted.")
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pidm-play", description="Play Pi Dungeon Master in the terminal.")
    ap.add_argument("--template", choices=sorted(TEMPLATES), required=True)
    ap.add_argument("--name", help="Character name (default: the Template's)")
    ap.add_argument("--setting", default="high fantasy",
                    help="high fantasy, dark fantasy, sword and sorcery, pirate isles, or a free-text fantasy premise")
    ap.add_argument("--tone", choices=["heroic", "grim", "comedic", "mystery-heavy"], default="heroic")
    ap.add_argument("--length", choices=["one-shot", "short"], default="one-shot")
    ap.add_argument("--lines", default="", help="Topics never shown")
    ap.add_argument("--veils", default="", help="Topics kept off-screen")
    ap.add_argument("--hook", default="", help="The Character's two-line backstory hook")
    ap.add_argument("--bible", metavar="PATH", help="Load a hand-written Campaign bible and skip generation")
    ap.add_argument("--db", default=os.environ.get("PIDM_DB", "data/pidm.sqlite"), help="SQLite file")
    args = ap.parse_args(argv)

    os.makedirs(os.path.dirname(os.path.abspath(args.db)), exist_ok=True)
    factory = open_db(args.db)
    try:
        session_id = _setup(factory, args)
    except SetupError as e:
        print(f"Setup failed: {e}", file=sys.stderr)
        return 1
    if session_id is None:
        return 0
    orch = TurnOrchestrator(factory, AnthropicClient(), round_cap=int(os.environ.get("PIDM_ROUND_CAP", "4")))
    print("Type your action and press Enter; 'retire' to end the Campaign, 'quit' to stop.\n")
    ended = []

    def play(event: str, payload: dict) -> None:
        emit(event, payload)
        if event == "turn_done" and payload.get("ending"):
            ended.append(payload["ending"])

    try:
        orch.run_opening(session_id, play)
        while not ended:
            action = _ask("> ")
            if action is None or action.lower() in ("quit", "exit"):
                return 0
            if action.lower() == "retire":
                if (_ask("Retire your Character and end this Campaign for good? [y/N] ") or "").lower() in ("y", "yes"):
                    retire(factory, session_id)
                    print("Your Character hangs up their sword. The Campaign has ended: Retired.")
                    return 0
                continue
            if action:
                orch.run_turn(session_id, action, play)
    except CampaignEnded:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
