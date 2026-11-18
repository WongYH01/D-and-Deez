"""Story director: the story tools, the Director block and the Ending conditions.

Story tools take bible slugs, validate against the Turn's state tree and change only the tree
(ADR 0002). Progress (for Stall detection) is a Beat advanced or a Clue revealed; moving and
Clock ticks are not progress.
Every rule cites the design document's Story design section (Story design §N).
"""

from __future__ import annotations

from d_and_deez.engine import GameState, ToolError
from d_and_deez.models import Beat, Campaign, Clock, Clue

STALL_TURNS = 8  # Story design §4
ENDINGS = ("victory", "defeat", "fallen_hero")  # Retired is the player's, never Claude's


# --- story position ---------------------------------------------------------------

def _campaign(state: GameState) -> Campaign:
    camp = state.campaign
    if camp.bible is None:
        raise ToolError("This Campaign has no bible, so there is no story to track.")
    if camp.status != "active":
        raise ToolError(f"The Campaign has ended ({camp.ending}).")
    return camp


def _acts(camp: Campaign) -> int:
    return len(camp.bible["acts"])


def _main(camp: Campaign) -> Clock:
    return next(c for c in camp.clocks if c.is_main)


def _main_full(camp: Campaign) -> bool:
    main = _main(camp)
    return main.filled >= main.segments


def _final_resolved(camp: Campaign) -> bool:
    """The final Beat is resolved once every Beat of the last Act is."""
    return all(b.status == "resolved" for b in camp.beats if b.act == _acts(camp))


def _clues(camp: Campaign) -> list[Clue]:
    return [c for s in camp.secrets for c in s.clues]


def _unmet(camp: Campaign, beat: Beat) -> list[str]:
    done = {b.slug for b in camp.beats if b.status == "resolved"} | \
        {s.slug for s in camp.secrets if s.learned_turn is not None}
    return [r for r in beat.requires if r not in done]


def _find(items, slug: str, kind: str, valid: list[str]):
    for x in items:
        if x.slug == slug.strip():
            return x
    raise ToolError(f"Unknown {kind} {slug!r}. Valid: {', '.join(valid) or 'none'}.")


def _progress(state: GameState) -> None:
    state.campaign.last_progress_turn = state.turn


def end(camp: Campaign, ending: str) -> None:
    camp.status = "complete"
    camp.ending = ending


def ending_met(state: GameState) -> str | None:
    """Which Ending condition holds now, if any (Defeat is checked first). Story design §6."""
    camp = state.campaign
    if camp.bible is None or camp.status != "active":
        return None
    if _main_full(camp) and not _final_resolved(camp):
        return "defeat"
    if state.character.dead:
        return "fallen_hero"
    if _final_resolved(camp) and not _main_full(camp):
        return "victory"
    return None


# --- story tools (Story design §4; Ending checks §6) ---------------------------------

def t_move_to(state: GameState, location: str) -> dict:
    camp = _campaign(state)
    locations = camp.bible["locations"]
    loc = next((x for x in locations if x["slug"] == location.strip()), None)
    if loc is None:
        raise ToolError(f"Unknown Location {location!r}. Valid: {', '.join(x['slug'] for x in locations)}. "
                        "Places you invent are not Locations and need no move_to.")
    camp.current_location = loc["slug"]
    return {"location": loc["slug"], "name": loc["name"]}


def t_advance_beat(state: GameState, beat: str, outcome: str) -> dict:
    camp = _campaign(state)
    open_now = [b.slug for b in camp.beats if b.act == camp.current_act and b.status == "open"]
    b = _find(camp.beats, beat, "Beat", open_now)
    if b.act != camp.current_act:
        raise ToolError(f"Beat {b.slug} belongs to Act {b.act}; the current Act is {camp.current_act}. "
                        f"Open Beats: {', '.join(open_now)}.")
    if b.status == "resolved":
        raise ToolError(f"Beat {b.slug} is already resolved. Open Beats: {', '.join(open_now) or 'none'}.")
    if _main_full(camp):
        raise ToolError("The Main clock is full: the antagonist's plan has succeeded. Call end_campaign with 'defeat'.")
    unmet = _unmet(camp, b)
    if unmet:
        raise ToolError(f"Beat {b.slug} requires {', '.join(unmet)} first.")
    b.status, b.resolved_turn = "resolved", state.turn
    _progress(state)
    out = {"beat": b.slug, "outcome": outcome, "resolved": True}
    if all(x.status == "resolved" for x in camp.beats if x.act == camp.current_act):
        if camp.current_act < _acts(camp):
            camp.current_act += 1
            out["act_opened"] = {"act": camp.current_act, "goal": camp.bible["acts"][camp.current_act - 1]["goal"]}
        else:
            out["victory_condition_met"] = True
            out["note"] = "The final Beat is resolved: call end_campaign with 'victory', then narrate the epilogue."
    return out


def t_reveal_clue(state: GameState, clue: str) -> dict:
    camp = _campaign(state)
    clues = _clues(camp)
    hidden = [c.slug for c in clues if c.secret.act == camp.current_act and c.revealed_turn is None]
    c = _find(clues, clue, "Clue", hidden)
    if c.secret.act != camp.current_act:
        raise ToolError(f"Clue {c.slug} belongs to Act {c.secret.act}; the current Act is {camp.current_act}.")
    if c.revealed_turn is not None:
        raise ToolError(f"Clue {c.slug} is already revealed.")
    c.revealed_turn = state.turn
    learned = c.secret.learned_turn is None
    if learned:
        c.secret.learned_turn = state.turn
    _progress(state)
    return {"clue": c.slug, "text": c.description, "secret": c.secret.slug, "secret_learned": learned,
            **({"revelation": c.secret.revelation} if learned else {})}


def t_tick_clock(state: GameState, clock: str, segments: int, reason: str) -> dict:
    camp = _campaign(state)
    if not 1 <= segments <= 3:
        raise ToolError("segments must be 1 to 3.")
    ck = _find(camp.clocks, clock, "Clock", [c.slug for c in camp.clocks])
    out = {"clock": ck.slug, "name": ck.name, "reason": reason}
    if ck.filled >= ck.segments:
        return {**out, "filled": f"{ck.filled}/{ck.segments}", "full": True, "consequence": ck.consequence,
                "note": "Already full; the tick is ignored."}
    if ck.is_main and _final_resolved(camp):
        raise ToolError("The final Beat is resolved: call end_campaign with 'victory' instead of ticking the Main clock.")
    ck.filled = min(ck.segments, ck.filled + segments)
    out["filled"] = f"{ck.filled}/{ck.segments}"
    if ck.filled >= ck.segments:
        out.update(full=True, consequence=ck.consequence)
        if ck.is_main:
            out["defeat_condition_met"] = True
            out["note"] = "The Main clock is full: call end_campaign with 'defeat', then narrate the epilogue."
    return out


def t_end_campaign(state: GameState, ending: str) -> dict:
    camp = _campaign(state)
    met = ending_met(state)
    if ending != met:
        why = {"victory": "the final Beat is resolved and the Main clock is not full",
               "defeat": "the Main clock is full and the final Beat is not resolved",
               "fallen_hero": "the Character is dead"}[ending]
        raise ToolError(f"The {ending} Ending needs {why}; that does not hold. Keep playing.")
    end(camp, ending)
    return {"ending": ending, "note": "The Campaign is over. Narrate the epilogue."}


# --- Director block (Story design §4; ENDING line §6) -----------------------------------

def director_block(state: GameState) -> str | None:
    """Plain-text story state for Claude every Turn; None for a Campaign without a bible."""
    camp = state.campaign
    if camp.bible is None:
        return None
    act = camp.bible["acts"][camp.current_act - 1]
    names = {x["slug"]: x["name"] for x in camp.bible["locations"]}
    lines = [f"Act {camp.current_act} of {_acts(camp)}: {act['goal']}",
             f"Location: {camp.current_location} ({names.get(camp.current_location, '?')})",
             "Open Beats:"]
    for b in camp.beats:
        if b.act == camp.current_act and b.status == "open":
            unmet = _unmet(camp, b)
            lines.append(f"- {b.slug}: {b.goal}" + (f" (requires {', '.join(unmet)})" if unmet else ""))
    clues = [c for c in _clues(camp) if c.secret.act == camp.current_act and c.secret.learned_turn is None]
    here = [c for c in clues if c.location == camp.current_location]
    lines.append("Clues here:" if here else "Clues here: none")
    lines += [f"- {c.slug}: {c.description}" for c in here]
    learned = [s for s in camp.secrets if s.learned_turn is not None]
    lines.append("Learned Secrets:" if learned else "Learned Secrets: none")
    lines += [f"- {s.slug}: {s.revelation}" for s in learned]
    lines.append("Clocks: " + "; ".join(f"{c.name} {c.filled}/{c.segments} ({c.slug}{', main' if c.is_main else ''})"
                                        for c in camp.clocks))
    since = state.turn - camp.last_progress_turn
    lines.append(f"Turns since progress: {since}")
    if since >= STALL_TURNS:
        # shortcut: no nudge once every Clue of the Act is revealed; add a Beat nudge if play shows it stalls there.
        elsewhere = sorted((c for c in _clues(camp) if c.secret.act == camp.current_act and c.revealed_turn is None
                            and c.location != camp.current_location),
                           key=lambda c: c.secret.learned_turn is not None)  # Clues of unlearned Secrets first
        if elsewhere:
            c = elsewhere[0]
            lines.append(f"STALL: the plot has not moved for {since} Turns. Bring Clue {c.slug} ({c.description}) "
                         "to the player this Turn, e.g. a messenger arrives or an ambush, then call reveal_clue.")
    met = ending_met(state)
    if met:
        lines.append(f"ENDING: the {met} condition is met. Call end_campaign with '{met}', then narrate the epilogue.")
    return "\n".join(lines)
