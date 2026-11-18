"""Seam 1: caster Templates, spell slots and their recovery through the tool dispatcher (R18)."""

from pidm.tools import snapshot


def slots(g):
    return [(s["level"], s["used"], s["max"]) for s in snapshot(g.state)["character"]["spell_slots"]]


def spend(g, level=1, n=1):
    next(s for s in g.ch.spell_slots if s.level == level).used += n


def test_a_level_1_caster_has_two_first_level_slots(make_game):
    # SRD Wizard and Cleric tables: 2 first-level slots at level 1.
    assert slots(make_game("wizard")) == [(1, 0, 2)]
    assert slots(make_game("cleric")) == [(1, 0, 2)]


def test_a_non_caster_has_no_slots(make_game):
    assert slots(make_game("fighter")) == []


def test_a_long_rest_restores_every_slot(make_game):
    # §6.2 and SRD Spellcasting: a long rest restores all expended slots.
    g = make_game("cleric")
    spend(g, n=2)
    g.ok("rest", kind="long")
    g.commit()
    assert slots(g) == [(1, 0, 2)]


def test_a_short_rest_restores_a_cleric_no_slots(make_game):
    g = make_game("cleric")
    spend(g, n=2)
    g.ok("rest", kind="short")
    assert slots(g) == [(1, 2, 2)]


def test_arcane_recovery_restores_one_slot_once_a_day(make_game):
    # SRD Wizard, Arcane Recovery: once per day after a short rest, slots of combined level up to half
    # the Wizard's level rounded up (1 at level 1); a long rest makes it available again.
    g = make_game("wizard")
    spend(g, n=2)
    r = g.ok("rest", kind="short")
    assert r["arcane_recovery"] == [1] and slots(g) == [(1, 1, 2)]
    g.ok("rest", kind="short")
    assert slots(g) == [(1, 1, 2)]
    g.ok("rest", kind="long")
    spend(g, n=2)
    g.ok("rest", kind="short")
    assert slots(g) == [(1, 1, 2)]


def test_slot_state_survives_a_commit(make_game):
    g = make_game("wizard")
    spend(g)
    g.commit()
    assert slots(g) == [(1, 1, 2)]


def test_levelling_up_grows_the_slots(make_game):
    # SRD Wizard table: level 3 has four 1st-level and two 2nd-level slots.
    g = make_game("wizard")
    spend(g)
    g.ok("grant_xp", amount=900, reason="test")
    g.commit()
    assert slots(g) == [(1, 1, 4), (2, 0, 2)]


def test_template_spells_are_on_the_class_list_in_the_srd_data(make_game):
    # Counts are SRD Wizard and Cleric level 1: 3 cantrips; Wizard spellbook of 6; prepared = ability mod + level
    # (Wizard 3 + 1 = 4; Cleric 3 + 1 = 4, plus the Life domain's bless and cure-wounds).
    from sqlalchemy import select
    from pidm.models import SrdSpell
    for template, cls, prepared in (("wizard", "Wizard", 4), ("cleric", "Cleric", 6)):
        g = make_game(template)
        spells = g.ch.spells
        assert len(spells["cantrips"]) == 3 and len(spells["prepared"]) == prepared
        for slug in sum(spells.values(), []):
            row = g.db.scalar(select(SrdSpell).where(SrdSpell.slug == slug))
            assert row and cls in [c["name"] for c in row.data["classes"]], slug
        assert all(g.db.get(SrdSpell, s).data["level"] == 0 for s in spells["cantrips"])
    assert len(make_game("wizard").ch.spells["spellbook"]) == 6


# --- cast_spell (R19) ----------------------------------------------------------------
# Elara (Wizard) and Aldric (Cleric): Int/Wis 16, proficiency +2: spell attack +5, save DC 13.
# Goblin: AC 15, 7 HP, Dex save +2.

def fight(g, n=1):
    g.script(20, *[1] * n)
    return g.ok("start_encounter", monsters=[{"monster": "goblin", "count": n}])


def test_a_cantrip_attack_rolls_to_hit_and_damage_and_costs_no_slot(make_game):
    g = make_game("wizard")
    fight(g)
    g.script(10, 6)  # 10 + 5 = 15 meets AC 15; Fire Bolt 1d10
    r = g.ok("cast_spell", spell="fire-bolt", targets=["Goblin 1"])
    assert r["results"][0]["hit"] and r["results"][0]["damage"] == 6 and r["slots_left"] == {1: 2}
    assert [x.outcome for x in g.last_rolls] == ["hit", None]


def test_a_spell_attack_that_misses_deals_no_damage(make_game):
    g = make_game("wizard")
    fight(g)
    g.script(9)  # 9 + 5 = 14 < AC 15
    r = g.ok("cast_spell", spell="fire-bolt", targets=["Goblin 1"])["results"][0]
    assert r == {"target": "Goblin 1", "attack_total": 14, "hit": False, "critical": False}


def test_a_critical_spell_attack_doubles_the_damage_dice(make_game):
    g = make_game("wizard")
    fight(g)
    g.script(20, 4, 5)
    r = g.ok("cast_spell", spell="ray-of-frost", targets=["Goblin 1"])["results"][0]
    assert r["critical"] and r["damage"] == 9 and r["target_status"] == "dead"  # 2d8 = 4 + 5


def test_a_save_spell_deals_full_damage_on_a_failure_and_none_on_a_success(make_game):
    g = make_game("cleric")
    fight(g, 2)
    g.script(5, 3, 15)  # Sacred Flame 1d8 = 5 once; Goblin 1 saves 3+2 = 5 < 13; Goblin 2 saves 17
    r = g.ok("cast_spell", spell="sacred-flame", targets=["Goblin 1", "Goblin 2"])["results"]
    assert [(x["save"]["success"], x["damage"]) for x in r] == [(False, 5), (True, 0)]


def test_a_half_on_save_spell_rolls_damage_once_for_every_target(make_game):
    g = make_game("wizard")
    g.ch.spells = {**g.ch.spells, "prepared": ["burning-hands"]}
    fight(g, 2)
    g.script(2, 3, 4,  # 3d6 = 9
            3,        # Goblin 1: 3+2 = 5 < 13, takes 9 and dies
            15)       # Goblin 2: 17 >= 13, takes half (4)
    r = g.ok("cast_spell", spell="burning-hands", targets=["Goblin 1", "Goblin 2"])
    assert [(x["target"], x["damage"]) for x in r["results"]] == [("Goblin 1", 9), ("Goblin 2", 4)]
    assert r["slots_left"] == {1: 1} and r["results"][0]["target_status"] == "dead"


def test_magic_missile_never_misses(make_game):
    g = make_game("wizard")
    fight(g)
    g.script(1, 2, 3)  # 3d4 + 3 = 9
    r = g.ok("cast_spell", spell="magic-missile", targets=["Goblin 1"])
    assert r["results"][0]["target_status"] == "dead" and r["slots_left"] == {1: 1}


def test_cure_wounds_heals_the_character_with_the_casting_modifier(make_game):
    g = make_game("cleric")
    g.ch.hp_current = 2
    g.script(4)  # 1d8 + Wis 3
    r = g.ok("cast_spell", spell="cure-wounds")
    assert r["healing"]["healed"] == 7 and g.ch.hp_current == 9 and r["slots_left"] == {1: 1}


def test_an_unmodelled_spell_spends_a_slot_and_returns_the_srd_text(make_game):
    g = make_game("wizard")
    r = g.ok("cast_spell", spell="mage-armor")
    assert r["modelled"] is False and "armor" in r["description"].lower() and r["slots_left"] == {1: 1}
    assert g.last_rolls == []


def test_invalid_casts_change_nothing(make_game):
    g = make_game("wizard")
    g.ch.spells = {**g.ch.spells, "prepared": ["magic-missile", "mage-armor"]}
    assert "not a cantrip or prepared" in g.call("cast_spell", spell="burning-hands", targets=["Goblin 1"])["error"]
    assert "No level 2" in g.call("cast_spell", spell="mage-armor", slot_level=2)["error"]
    assert "needs targets" in g.call("cast_spell", spell="magic-missile")["error"]
    fight(g)
    assert "Unknown target" in g.call("cast_spell", spell="magic-missile", targets=["Orc"])["error"]
    spend(g, n=2)
    assert "No level 1" in g.call("cast_spell", spell="mage-armor")["error"]
    assert slots(g) == [(1, 2, 2)] and g.last_rolls == []


def test_casting_uses_the_action_and_a_reaction_spell_uses_the_reaction(make_game):
    g = make_game("wizard")
    fight(g)
    g.ok("cast_spell", spell="shield")
    assert "reaction" in g.call("cast_spell", spell="shield")["error"]
    g.ok("cast_spell", spell="mage-hand")  # the action is still free
    assert "no action left" in g.call("cast_spell", spell="mage-hand")["error"]
    assert slots(g) == [(1, 1, 2)]


def test_a_caster_completes_an_encounter_through_the_orchestrator(factory):
    from sqlalchemy import select
    from pidm.engine import load_state
    from pidm.models import Campaign, Combatant, Session
    from pidm.orchestrator import TurnOrchestrator
    from pidm.templates import create_character
    from conftest import Events, FakeClaude, scripted_rng, text, tool
    with factory() as db:
        camp = Campaign(name="Test", premise="A test.")
        create_character(camp, "wizard")
        sess = Session(campaign=camp)
        db.add(camp)
        db.commit()
        sid = sess.id
    claude = FakeClaude(
        [tool("start_encounter", monsters=[{"monster": "goblin"}])],
        [tool("cast_spell", spell="magic-missile", targets=["Goblin 1"])],
        [tool("end_encounter")],
        text("Three darts of force end the goblin."))
    ev = Events()
    TurnOrchestrator(factory, claude, rng=scripted_rng([20, 1, 1, 2, 3])).run_turn(sid, "I cast magic missile", ev)
    assert "error" not in ev.kinds() and ev.kinds()[-1] == "turn_done"
    with factory() as db:
        state = load_state(db, sid, None)
        assert state.encounter is None and [(s.level, s.used) for s in state.character.spell_slots] == [(1, 1)]
        assert db.scalar(select(Combatant.status)) == "dead"
