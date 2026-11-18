"""Seam 1: the story tools (move_to, advance_beat, reveal_clue, tick_clock, end_campaign) against a bible."""

from __future__ import annotations

from d_and_deez.story import director_block

from conftest import fixture_bible


def three_act_bible():
    b = fixture_bible()
    b["acts"] = [{"slug": f"act{n}", "goal": f"Goal {n}",
                  "beats": [{"slug": f"act{n}.b{i}", "goal": f"Beat {n}.{i}", "requires": []} for i in (1, 2)]}
                 for n in (1, 2, 3)]
    b["secrets"] = [{"slug": f"secret.s{n}", "act": f"act{n}", "revelation": f"Revelation {n}"} for n in (1, 2, 3)]
    b["clues"] = [{"slug": f"clue.s{n}.{i}", "secret": f"secret.s{n}", "description": f"Clue {n}.{i}", "location": loc}
                  for n in (1, 2, 3) for i, loc in enumerate(["loc.shore", "loc.mill", "loc.village"], 1)]
    return b


def test_move_to_accepts_only_bible_locations(make_game):
    g = make_game(bible=fixture_bible())
    assert g.ok("move_to", location="loc.mill") == {"location": "loc.mill", "name": "The abandoned tide mill"}
    err = g.call("move_to", location="the old well")["error"]
    assert "Unknown Location 'the old well'" in err and "loc.shore, loc.village, loc.mill, loc.chapel" in err
    assert g.commit().campaign.current_location == "loc.mill"


def test_an_unknown_beat_lists_the_open_beats(make_game):
    g = make_game(bible=fixture_bible())
    err = g.call("advance_beat", beat="act1.dragon", outcome="slain")["error"]
    assert err == "Unknown Beat 'act1.dragon'. Valid: act1.ferryman, act1.undercroft, act1.bell."


def test_requires_gate_a_beat_until_its_secret_is_learned(make_game):
    g = make_game(bible=fixture_bible())
    assert g.call("advance_beat", beat="act1.undercroft", outcome="in")["error"] == \
        "Beat act1.undercroft requires secret.sluice first."
    g.ok("reveal_clue", clue="clue.sluice.2")
    assert g.ok("advance_beat", beat="act1.undercroft", outcome="Through the sluice.")["resolved"]
    assert g.call("advance_beat", beat="act1.undercroft", outcome="again")["error"].startswith(
        "Beat act1.undercroft is already resolved.")


def test_beats_resolve_in_any_order_and_the_last_reports_victory(make_game):
    g = make_game(bible=fixture_bible())
    g.ok("reveal_clue", clue="clue.sluice.1")
    g.ok("reveal_clue", clue="clue.rope.1")
    r = g.ok("advance_beat", beat="act1.undercroft", outcome="in")
    assert "victory_condition_met" not in r
    g.ok("advance_beat", beat="act1.bell", outcome="The rope is cut.")
    r = g.ok("advance_beat", beat="act1.ferryman", outcome="Osric was found alive.")
    assert r["victory_condition_met"] and "end_campaign" in r["note"]


def test_resolving_an_acts_last_beat_opens_the_next_act(make_game):
    g = make_game(bible=three_act_bible())
    assert "act_opened" not in g.ok("advance_beat", beat="act1.b1", outcome="x")
    err = g.call("advance_beat", beat="act2.b1", outcome="x")["error"]
    assert err.startswith("Beat act2.b1 belongs to Act 2; the current Act is 1.")
    assert g.ok("advance_beat", beat="act1.b2", outcome="x")["act_opened"] == {"act": 2, "goal": "Goal 2"}
    assert g.ok("advance_beat", beat="act2.b1", outcome="x")["resolved"]
    assert g.commit().campaign.current_act == 2


def test_the_first_clue_of_a_secret_learns_it_wherever_the_clue_is_placed(make_game):
    g = make_game(bible=fixture_bible())  # the Character starts at loc.shore; clue.rope.2 is at the mill
    r = g.ok("reveal_clue", clue="clue.rope.2")
    assert r == {"clue": "clue.rope.2", "secret": "secret.rope", "secret_learned": True,
                 "text": "A hymn carved into the mill's beams: 'Braided from the drowned, cut only by the moon's own metal.'",
                 "revelation": "The bell is rung by a rope braided from the hair of the drowned; cut it with silver "
                               "and the bell can never ring."}
    r = g.ok("reveal_clue", clue="clue.rope.1")
    assert r["secret_learned"] is False and "revelation" not in r
    assert g.call("reveal_clue", clue="clue.rope.1")["error"] == "Clue clue.rope.1 is already revealed."


def test_a_clue_of_a_later_act_is_rejected(make_game):
    g = make_game(bible=three_act_bible())
    assert g.call("reveal_clue", clue="clue.s2.1")["error"] == \
        "Clue clue.s2.1 belongs to Act 2; the current Act is 1."
    err = g.call("reveal_clue", clue="clue.nope")["error"]
    assert err == "Unknown Clue 'clue.nope'. Valid: clue.s1.1, clue.s1.2, clue.s1.3."


def test_tick_clock_takes_one_to_three_segments_and_a_full_clock_returns_its_consequence(make_game):
    g = make_game(bible=fixture_bible())
    assert g.call("tick_clock", clock="clock.suspicion", segments=4, reason="x")["error"] == "segments must be 1 to 3."
    assert g.call("tick_clock", clock="clock.suspicion", segments=0, reason="x")["error"] == "segments must be 1 to 3."
    assert "Valid: clock.tide, clock.suspicion" in g.call("tick_clock", clock="clock.doom", segments=1, reason="x")["error"]
    assert g.ok("tick_clock", clock="clock.suspicion", segments=3, reason="seen")["filled"] == "3/4"
    r = g.ok("tick_clock", clock="clock.suspicion", segments=3, reason="seen again")
    assert (r["filled"], r["full"], r["consequence"]) == ("4/4", True, "Three cultists ambush the Character in the fog.")
    r = g.ok("tick_clock", clock="clock.suspicion", segments=1, reason="more")
    assert r["filled"] == "4/4" and r["note"] == "Already full; the tick is ignored."
    assert "defeat_condition_met" not in r


def test_filling_the_main_clock_meets_defeat_and_blocks_beats(make_game):
    g = make_game(bible=fixture_bible())
    g.ok("tick_clock", clock="clock.tide", segments=3, reason="dawdling")
    assert g.call("end_campaign", ending="defeat")["error"].startswith("The defeat Ending needs the Main clock is full")
    r = g.ok("tick_clock", clock="clock.tide", segments=3, reason="the tide turns")
    assert r["defeat_condition_met"] and r["filled"] == "6/6"
    assert "Call end_campaign with 'defeat'" in g.call("advance_beat", beat="act1.ferryman", outcome="x")["error"]
    assert g.call("end_campaign", ending="victory")["error"].startswith("The victory Ending needs")
    assert g.ok("end_campaign", ending="defeat")["ending"] == "defeat"
    camp = g.commit().campaign
    assert (camp.status, camp.ending) == ("complete", "defeat")


def test_victory_needs_the_final_beat_resolved(make_game):
    g = make_game(bible=fixture_bible())
    assert g.call("end_campaign", ending="victory")["error"].startswith("The victory Ending needs")
    g.ok("reveal_clue", clue="clue.sluice.1")
    g.ok("reveal_clue", clue="clue.rope.1")
    for beat in ("act1.ferryman", "act1.undercroft", "act1.bell"):
        g.ok("advance_beat", beat=beat, outcome="done")
    assert "Main clock" in g.call("tick_clock", clock="clock.tide", segments=1, reason="late")["error"]
    assert g.ok("end_campaign", ending="victory")["ending"] == "victory"
    assert g.call("end_campaign", ending="victory")["error"] == "The Campaign has ended (victory)."


def test_fallen_hero_needs_a_dead_character_and_retired_is_not_claudes(make_game):
    g = make_game(bible=fixture_bible())
    assert g.call("end_campaign", ending="fallen_hero")["error"].startswith("The fallen_hero Ending needs")
    assert "must be one of" in g.call("end_campaign", ending="retired")["error"]
    g.script(1, 1, 5)  # §4.26: a natural 1 counts as two failures (the reroll, R20, is a 1 too), then a third
    g.ok("apply_damage", target="character", amount="12", damage_type="slashing")
    assert g.ch.dead and g.ch.death_failures == 3
    assert g.ok("end_campaign", ending="fallen_hero")["ending"] == "fallen_hero"


def test_moving_and_clock_ticks_do_not_reset_the_stall_counter(make_game):
    g = make_game(bible=fixture_bible()).at_turn(5)
    g.ok("move_to", location="loc.mill")
    g.ok("tick_clock", clock="clock.suspicion", segments=1, reason="noticed")
    assert "Turns since progress: 5" in director_block(g.state)
    g.ok("reveal_clue", clue="clue.sluice.1")
    assert "Turns since progress: 0" in director_block(g.state)
    g.at_turn(7).ok("advance_beat", beat="act1.ferryman", outcome="found")
    g.at_turn(9)
    assert "Turns since progress: 2" in director_block(g.state)


def test_story_tools_need_a_bible(make_game):
    g = make_game()
    assert g.call("move_to", location="loc.mill")["error"] == "This Campaign has no bible, so there is no story to track."


def test_the_stall_nudge_still_names_a_clue_once_every_secret_is_learned(make_game):
    g = make_game(bible=fixture_bible())
    g.ok("reveal_clue", clue="clue.sluice.3")  # both Secrets learned at Turn 0, at the shore
    g.ok("reveal_clue", clue="clue.rope.1")
    g.at_turn(8)
    assert "STALL: the plot has not moved for 8 Turns. Bring Clue clue.sluice.1" in director_block(g.state)
