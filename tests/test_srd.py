"""M2 rules grounding through Seam 1: lookup_srd, lookup_rule and Encounters built from imported Stat blocks."""

from __future__ import annotations

import json
from importlib import resources


def _has_key(value, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_has_key(v, key) for v in value.values())
    if isinstance(value, list):
        return any(_has_key(v, key) for v in value)
    return False


def test_lookup_srd_returns_a_monster_without_url_image_or_timestamp(make_game):
    g = make_game()
    r = g.ok("lookup_srd", kind="monster", slug="owlbear")
    assert r["name"] == "Owlbear"
    assert r["hit_points"] == 59 and r["armor_class"][0]["value"] == 13
    for key in ("url", "image", "updated_at"):
        assert not _has_key(r, key)


def test_lookup_srd_normalises_slugs_for_every_kind(make_game):
    g = make_game()
    assert g.ok("lookup_srd", kind="monster", slug="Bandit Captain")["name"] == "Bandit Captain"
    assert g.ok("lookup_srd", kind="monster", slug="bandit_captain")["name"] == "Bandit Captain"
    assert g.ok("lookup_srd", kind="spell", slug="Cure Wounds")["level"] == 1
    assert g.ok("lookup_srd", kind="item", slug="longsword")["damage"]["damage_dice"] == "1d8"
    assert g.ok("lookup_srd", kind="item", slug="bag-of-holding")["name"] == "Bag of Holding"  # a magic item


def test_lookup_srd_miss_lists_similar_names(make_game):
    g = make_game()
    err = g.call("lookup_srd", kind="monster", slug="red dragon")["error"]
    assert "adult-red-dragon" in err and "young-red-dragon" in err
    assert len(err.split("Similar: ")[1].split(", ")) <= 5
    assert "error" in g.call("lookup_srd", kind="vehicle", slug="cart")


def test_lookup_rule_returns_grappling_with_its_heading_path(make_game):
    g = make_game()
    sections = g.ok("lookup_rule", query="grapple")["sections"]
    assert len(sections) == 3
    grappling = next(s for s in sections if s["section"] == "Making an Attack > Melee Attacks > Grappling")
    assert "Strength (Athletics) check" in grappling["body"]
    assert g.ok("lookup_rule", query="xyzzy")["sections"] == []


def test_encounter_with_a_non_fixture_monster_uses_its_stat_block(make_game):
    # Owlbear: HP 59, AC 13, Multiattack (Beak +7, 1d10+5; Claws +7, 2d8+5). Fighter Bram AC 19, HP 12.
    g = make_game("fighter")
    g.script(1, 20)
    g.ok("start_encounter", monsters=[{"monster": "owlbear"}])
    g.script(15, 4, 1)  # beak 22 hits for 9; claws miss
    r = g.ok("resolve_npc_turns")
    attacks = r["turns"][0]["attacks"]
    assert [(a["action"], a["hit"]) for a in attacks] == [("Beak", True), ("Claws", False)]
    assert attacks[0]["attack_total"] == 22 and r["character_hp"] == 3
    g.commit()
    assert (g.combatant("Owlbear 1").hp, g.combatant("Owlbear 1").ac) == (59, 13)


def test_monster_without_a_usable_attack_cannot_join_an_encounter(make_game):
    # R16: the shrieker has no attack action.
    g = make_game()
    assert "no attack action" in g.call("start_encounter", monsters=[{"monster": "shrieker"}])["error"]
    g.commit()
    assert g.state.encounter is None


def test_grapple_against_an_imported_monster_checks_size(make_game):
    # §4.15, R15. Ogre: Large, Str 19 (+4), Dex 8. Hill giant: Huge. Fighter Bram: Medium, Athletics +5.
    g = make_game("fighter")
    g.script(20, 1).ok("start_encounter", monsters=[{"monster": "ogre"}])
    r = g.script(15, 2).ok("contest", a="character", b="Ogre 1", effect="grapple")
    assert (r["total_a"], r["total_b"], r["effect_applied"]) == (20, 6, "Ogre 1 is grappled")
    g.ok("end_encounter")
    g.script(20, 1).ok("start_encounter", monsters=[{"monster": "hill-giant"}])
    assert "more than one size larger" in g.call("contest", a="character", b="Hill Giant 1", effect="grapple")["error"]


def test_damage_given_as_a_choice_uses_the_first_option(make_game):
    # R16. Guard Spear: +3 to hit, 1d6+1 one-handed (first option) or 1d8+1 two-handed. Fighter Bram AC 19, HP 12.
    g = make_game("fighter")
    g.script(1, 20).ok("start_encounter", monsters=[{"monster": "guard"}])
    r = g.script(18, 6).ok("resolve_npc_turns")
    assert r["turns"][0]["attacks"][0]["hit"] and r["character_hp"] == 5
    assert g.last_rolls[-1].expr == "1d6+1"


def test_multiattack_skips_parts_the_engine_cannot_resolve(make_game):
    # R16. Roper: four Tendrils (grapple, no damage), Reel (ability), one Bite (+7, 4d8+4). Only the Bite is rolled.
    # Hydra: "as many bites as it has heads" is played as one Bite (+8, 1d10+5).
    g = make_game("fighter")
    g.script(1, 20).ok("start_encounter", monsters=[{"monster": "roper"}])
    r = g.script(1).ok("resolve_npc_turns")
    assert [a["action"] for a in r["turns"][0]["attacks"]] == ["Bite"]
    g.ok("end_encounter")
    g.script(1, 20).ok("start_encounter", monsters=[{"monster": "hydra"}])
    r = g.script(1).ok("resolve_npc_turns")
    assert [a["action"] for a in r["turns"][0]["attacks"]] == ["Bite"]


def test_every_srd_monster_plays_through_the_engine(make_game):
    # R4, R16: every imported Stat block either fights without crashing or is refused at start_encounter.
    monsters = json.loads(resources.files("pidm.data").joinpath("5e-SRD-Monsters.json").read_text(encoding="utf-8"))
    refused = set()
    for i, m in enumerate(monsters):
        g = make_game(("fighter", "rogue", "barbarian")[i % 3]).random(i)
        if "error" in g.call("start_encounter", monsters=[{"monster": m["index"]}]):
            refused.add(m["index"])
        else:
            name = g.state.encounter.combatants[0].name
            for _ in range(3):
                g.call("resolve_npc_turns")
                g.call("contest", a="character", b=name, effect="grapple")
                g.call("attack", target=name, weapon="unarmed")
            g.call("end_encounter")
        g.close()
    assert refused == {"frog", "rug-of-smothering", "sea-horse", "shrieker", "vampire-mist"}
