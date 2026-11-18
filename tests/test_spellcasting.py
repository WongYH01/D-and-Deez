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
