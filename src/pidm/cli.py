"""Terminal loop: `pidm-play --template rogue`. Creates a throwaway Campaign and plays Turns from stdin."""

from __future__ import annotations

import argparse
import os
import sys

from pidm.claude import AnthropicClient
from pidm.db import open_db
from pidm.models import Campaign, Session
from pidm.orchestrator import TurnOrchestrator
from pidm.templates import TEMPLATES, create_character

PREMISE = (
    "A goblin band, with wolves and an outlaw captain behind it, has been raiding the north road out of the "
    "village of Thornwick. The Character has been hired to find their camp in the ravine woods and end the raids. "
    "Open on the road at dusk, beside a freshly looted wagon."
)
OPENING = "(Begin the session: set the opening scene and ask what I do.)"


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
    elif event == "error":
        print(f"\n! {payload['message']} ({payload['detail']})\n", flush=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pidm-play", description="Play Pi Dungeon Master in the terminal.")
    ap.add_argument("--template", choices=sorted(TEMPLATES), required=True)
    ap.add_argument("--name", help="Character name (default: the Template's)")
    ap.add_argument("--db", default=os.environ.get("PIDM_DB", "data/pidm.sqlite"), help="SQLite file")
    args = ap.parse_args(argv)

    os.makedirs(os.path.dirname(os.path.abspath(args.db)), exist_ok=True)
    factory = open_db(args.db)
    with factory() as db:
        camp = Campaign(name="The North Road", premise=PREMISE)
        ch = create_character(camp, args.template, args.name)
        sess = Session(campaign=camp)
        db.add(camp)
        db.commit()
        session_id, name = sess.id, ch.name
    orch = TurnOrchestrator(factory, AnthropicClient(), round_cap=int(os.environ.get("PIDM_ROUND_CAP", "4")))
    print(f"{name} the {args.template}. Type your action and press Enter; 'quit' to stop.\n")
    orch.run_turn(session_id, OPENING, emit)
    while True:
        try:
            action = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if action.lower() in ("quit", "exit"):
            return 0
        if action:
            orch.run_turn(session_id, action, emit)


if __name__ == "__main__":
    sys.exit(main())
