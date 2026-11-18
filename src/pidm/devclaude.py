"""Scripted Claude clients for checking the web UI by hand with no API key: `PIDM_FAKE_CLAUDE=1` (see `from_env`).

Campaign creation (the setup wizard at `#/setup`) gets the test fixture bible, so Regenerate shows the same premise.

Each Turn answers by the player's action:
- an action containing "fail" fails the Turn (an `error` event, then Retry);
- an action containing "roll" makes a Perception check first (a `roll` line);
- anything else gets a short Narration.
Every call waits `PIDM_FAKE_DELAY` seconds (default 1) so the thinking indicator and the locked input show.
"""

from __future__ import annotations

import itertools
import json
import os
import time
from pathlib import Path
from typing import Literal

from pidm.claude import ClaudeError, Reply, Usage
from pidm.prompts import OPENING, RESUME

# shortcut: reads the bible from tests/, so dev mode runs from a repo checkout only, not the Docker image.
BIBLE = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "one_shot_bible.json"
ACTION = "Player action: "
_ids = itertools.count(1)


def _text(t: str) -> Reply:
    return Reply(content=[{"type": "text", "text": t}], stop_reason="end_turn", usage=Usage(100, 20, 0))


def _tool(name: str, args: dict) -> Reply:
    return Reply(content=[{"type": "tool_use", "id": f"toolu_dev_{next(_ids)}", "name": name, "input": args}],
                 stop_reason="tool_use", usage=Usage(100, 20, 0))


class DevClaude:
    def __init__(self, role: Literal["turn", "plan", "recap"]):
        self.role = role
        self.delay = float(os.environ.get("PIDM_FAKE_DELAY", "1"))

    def send(self, *, system, messages, tools, tools_enabled, on_text=None, force_tool=None) -> Reply:
        time.sleep(self.delay)
        if self.role == "plan":
            return _tool(force_tool, json.loads(BIBLE.read_text(encoding="utf-8")))
        if self.role == "recap":
            return _text("The hero arrived and looked around.")
        reply = self._turn(messages[-1]["content"], tools_enabled)
        if on_text:  # the Narration-only call streams; the rest arrives whole, as with the real client
            for b in reply.content:
                if b["type"] == "text":
                    on_text(b["text"])
        return reply

    def _turn(self, last: str | list[dict], tools_enabled: bool) -> Reply:
        if isinstance(last, list) and last[0]["type"] == "tool_result":
            return _text("The check is settled. What do you do next?")
        prompt = last if isinstance(last, str) else last[0]["text"]
        action = prompt.rpartition(ACTION)[2] if ACTION in prompt else ""
        if action in (OPENING, RESUME):
            return _text("(Dev Narration) Fog rolls over the Reed Shore. A bell tolls once. What do you do?")
        action = action.lower()
        if "fail" in action:
            raise ClaudeError("Dev client: a scripted failure.")
        if "roll" in action and tools_enabled:
            return _tool("skill_check", {"skill": "perception", "dc": 12})
        return _text(f'(Dev Narration) "{action}": the fog shifts around you. What do you do?')
