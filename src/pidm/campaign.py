"""Campaign setup (session zero): generate or load a Campaign bible, validate it, seed the story tables.

The caller (the terminal loop, later the web wizard) shows the premise and decides whether to accept
it; a rejected premise is replaced by a fresh `start_campaign` call.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy.orm import sessionmaker

from pidm.bible import ACTS, Bible, validate
from pidm.claude import ClaudeClient
from pidm.engine import load_state
from pidm.models import Beat, Campaign, Clock, Clue, Secret, Session
from pidm.story import end
from pidm.templates import create_character

PLAN_TOOL = "write_campaign_bible"
ATTEMPTS = 3


class SetupError(Exception):
    pass


@dataclass
class Setup:
    setting: str
    tone: str
    length: str  # one-shot, short
    lines: str = ""
    veils: str = ""
    hook: str = ""


PLAN_SYSTEM = """You plan a hidden Campaign bible for a single-player Dungeons & Dragons 5e game (SRD 5.1, \
fantasy only). The player never sees the bible; they see only its spoiler-free premise. Call the \
write_campaign_bible tool with the whole bible.

Rules the bible must follow (code checks every one):
- One Act for a one-shot, three Acts for a short campaign. Each Act has a goal and 2 to 4 Beats.
- Beats in an Act can be resolved in any order. A Beat may list in `requires` earlier Beats (listed before it) \
or Secrets of its own or an earlier Act that the player must learn first.
- Three Clue Rule: every Secret has at least 3 Clues, spread over at least 2 different Locations, so missing \
one Clue cannot stall the plot. Each Secret belongs to one Act.
- Exactly one Main clock (main: true) tracks the antagonist's plan; it fills if the player delays or fails. \
Side Clocks are optional. Clocks have 4 to 12 segments; a one-shot's Main clock is usually 6, a short \
campaign's 8 to 12.
- Every slug is unique and every slug reference resolves (Clue to Secret and Location, Secret to Act, \
`requires` to Beats or Secrets, start_location to a Location).
- Endings: a Victory (the final Beat is resolved before the Main clock fills) and a Defeat (the Main clock \
fills first).
- The opening scene starts mid-action at start_location, ties to the Character's backstory hook and ends on \
a question.
- Never include anything on the Lines list; keep anything on the Veils list off-screen.
"""


def _request(setup: Setup) -> str:
    return (f"Setting: {setup.setting}\nTone: {setup.tone}\nLength: {setup.length} ({ACTS[setup.length]} Act(s))\n"
            f"Lines (never shown): {setup.lines or 'none'}\nVeils (off-screen only): {setup.veils or 'none'}\n"
            f"Character backstory hook: {setup.hook or 'none'}")


def _generate(client: ClaudeClient, setup: Setup) -> Bible:
    tools = [{"name": PLAN_TOOL, "description": "Submit the complete Campaign bible.",
              "input_schema": Bible.model_json_schema()}]
    messages: list[dict] = [{"role": "user", "content": _request(setup)}]
    errors: list[str] = []
    for _ in range(ATTEMPTS):
        reply = client.send(system=PLAN_SYSTEM, messages=messages, tools=tools, tools_enabled=True, on_text=None,
                            force_tool=PLAN_TOOL)
        call = next((b for b in reply.content if b["type"] == "tool_use" and b["name"] == PLAN_TOOL), None)
        bible, errors = validate(call["input"] if call else None, setup.length)
        if bible:
            return bible
        feedback = "The bible failed these checks; call write_campaign_bible again with a corrected bible:\n- " + \
            "\n- ".join(errors)
        messages = messages + [
            {"role": "assistant", "content": reply.content},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": call["id"], "content": feedback,
                                          "is_error": True}] if call else feedback}]
    raise SetupError(f"No valid Campaign bible after {ATTEMPTS} attempts: {'; '.join(errors)}")


def _seed(bible: Bible, setup: Setup) -> Campaign:
    camp = Campaign(name=bible.title, premise=bible.premise, setting=setup.setting, tone=setup.tone,
                    length=setup.length, lines=setup.lines, veils=setup.veils, bible=bible.model_dump(),
                    current_act=1, current_location=bible.start_location, last_progress_turn=0)
    acts = {a.slug: n for n, a in enumerate(bible.acts, 1)}
    for n, act in enumerate(bible.acts, 1):
        camp.beats += [Beat(slug=b.slug, act=n, goal=b.goal, requires=b.requires, status="open") for b in act.beats]
    for s in bible.secrets:
        camp.secrets.append(Secret(slug=s.slug, act=acts[s.act], revelation=s.revelation, clues=[
            Clue(slug=c.slug, description=c.description, location=c.location)
            for c in bible.clues if c.secret == s.slug]))
    camp.clocks += [Clock(slug=c.slug, name=c.name, segments=c.segments, filled=0, consequence=c.consequence,
                          is_main=c.main, visible=False) for c in bible.clocks]
    return camp


def start_campaign(factory: sessionmaker, setup: Setup, template: str, name: str | None, *,
                   client: ClaudeClient | None = None, bible: dict | None = None) -> Session:
    """Generate (or load) and validate a bible, then seed the Campaign, its story, the Character and a Session."""
    if bible is None:
        b = _generate(client, setup)
    else:
        b, errors = validate(bible, setup.length)
        if errors:
            raise SetupError(f"Invalid Campaign bible: {'; '.join(errors)}")
    camp = _seed(b, setup)
    create_character(camp, template, name)
    sess = Session(campaign=camp)
    with factory() as db:
        db.add(camp)
        db.commit()
    return sess


def load_bible(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def retire(factory: sessionmaker, session_id: int) -> None:
    """The player ends the Campaign: no Claude call and no epilogue."""
    with factory() as db:
        end(load_state(db, session_id, None).campaign, "retired")
        db.commit()
