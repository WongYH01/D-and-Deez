"""Seam 1: checks, saves and contests through the tool dispatcher."""


def test_skill_check_uses_ability_mod_and_proficiency(make_game):
    # §2.1, §2.3: Fighter Athletics = Str +3 + proficiency +2.
    g = make_game("fighter").script(10)
    r = g.ok("skill_check", skill="athletics", dc=15)
    assert (r["bonus"], r["total"], r["success"]) == (5, 15, True)
    roll = g.last_rolls[0]
    assert (roll.expr, roll.total, roll.target, roll.outcome) == ("d20+5", 15, 15, "success")


def test_expertise_doubles_proficiency(make_game):
    # §9.3 Expertise, R6: Rogue Stealth = Dex +3 + 2 x 2.
    g = make_game("rogue").script(5)
    assert g.ok("skill_check", skill="Stealth", dc=12)["total"] == 12


def test_thieves_tools_use_expertise(make_game):
    g = make_game("rogue").script(8)
    assert g.ok("skill_check", skill="thieves' tools", dc=15)["total"] == 15


def test_plain_ability_check_has_no_proficiency(make_game):
    g = make_game("fighter").script(10)
    assert g.ok("skill_check", skill="strength", dc=10)["bonus"] == 3


def test_lucky_rerolls_a_natural_one(make_game):
    # §10 Lucky, R9: always reroll and use the new roll.
    g = make_game("rogue").script(1, 14)
    r = g.ok("skill_check", skill="acrobatics", dc=15)
    assert r["total"] == 14 + 5
    assert g.last_rolls[0].dice == [1, 14]


def test_chain_mail_gives_stealth_disadvantage(make_game):
    # §12.2 Stealth column.
    g = make_game("fighter").script(17, 4)
    r = g.ok("skill_check", skill="stealth", dc=10)
    assert r["total"] == 4 + 2
    assert g.last_rolls[0].expr == "2d20kl1+2"


def test_exhaustion_gives_disadvantage_on_checks(make_game):
    g = make_game("fighter")
    g.ok("set_condition", target="character", condition="exhaustion", on=True)
    g.script(18, 3)
    assert g.ok("skill_check", skill="athletics", dc=10)["total"] == 8


def test_advantage_and_disadvantage_cancel(make_game):
    # §2.7: one d20 when both apply.
    g = make_game("fighter").script(12)
    g.ok("skill_check", skill="athletics", dc=10, advantage=True, disadvantage=True)
    assert g.last_rolls[0].dice == [12]


def test_unknown_skill_is_rejected_without_rolling(make_game):
    g = make_game("fighter")
    r = g.call("skill_check", skill="juggling", dc=10)
    assert "Unknown skill" in r["error"]
    assert g.last_rolls == []


def test_missing_argument_is_rejected(make_game):
    g = make_game("fighter")
    assert "dc" in g.call("skill_check", skill="athletics")["error"]


def test_saving_throw_applies_damage_and_condition_on_failure(make_game):
    # §3: save bonus = mod + proficiency for class saves; effect applies on failure.
    g = make_game("fighter").script(5, 5, 4, 4)  # the failed 5 is rerolled (R20) to another 5
    r = g.ok("saving_throw", target="character", ability="constitution", dc=13,
             effect={"damage": "2d4", "damage_type": "poison", "condition": "poisoned"})
    assert r["total"] == 5 + 4 and not r["success"]
    assert r["damage"]["damage"] == 8
    g.commit()
    assert g.ch.hp_current == 12 - 8
    assert [c["name"] for c in g.ch.conditions] == ["poisoned"]


def test_saving_throw_half_damage_on_success(make_game):
    g = make_game("fighter").script(15, 3, 4)
    r = g.ok("saving_throw", target="character", ability="dex", dc=12,
             effect={"damage": "2d4", "damage_type": "fire", "half_on_success": True})
    assert r["success"] and r["damage"]["damage"] == 3  # 7 halved, rounded down (R11)


def test_paralyzed_creature_auto_fails_dex_saves(make_game):
    g = make_game("fighter")
    g.ok("set_condition", target="character", condition="paralyzed")
    r = g.ok("saving_throw", target="character", ability="dex", dc=5)
    assert r["auto_fail"] and not r["success"]


def test_rage_gives_advantage_on_strength_saves(make_game):
    g = make_game("barbarian")
    g.ok("use_feature", name="rage")
    g.script(3, 15)
    r = g.ok("saving_throw", target="character", ability="str", dc=10)
    assert r["total"] == 15 + 5


def test_contest_higher_total_wins_and_tie_changes_nothing(make_game):
    # §2.2
    g = make_game("rogue")
    g.script(10, 1).ok("start_encounter", monsters=[{"monster": "wolf"}])
    g.script(6, 13)  # Pip stealth 6+7 = 13; wolf perception 13+3 = 16
    r = g.ok("contest", a="character", skill_a="stealth", b="Wolf 1", skill_b="perception")
    assert r["winner"] == "Wolf 1"
    g.script(12, 16)  # 19 vs 19
    assert g.ok("contest", a="character", skill_a="stealth", b="Wolf 1", skill_b="perception")["winner"] is None


def test_grapple_win_applies_grappled_and_escape_clears(make_game):
    # §4.15, R9 (defender's better skill), R15.
    g = make_game("fighter")
    g.script(20, 1).ok("start_encounter", monsters=[{"monster": "goblin"}])
    g.script(10, 5)  # Athletics 10+5=15 vs goblin Acrobatics (Dex +2) 5+2=7
    r = g.ok("contest", a="character", b="Goblin 1", effect="grapple")
    assert r["winner"] == "character" or r["winner"] == g.ch.name
    assert r["effect_applied"] == "Goblin 1 is grappled"
    assert any(c["name"] == "grappled" for c in g.combatant("Goblin 1").conditions)


def test_shove_prone_replaces_an_attack(make_game):
    g = make_game("fighter")
    g.script(20, 1).ok("start_encounter", monsters=[{"monster": "goblin"}])
    g.script(10, 5).ok("contest", a="character", b="Goblin 1", effect="shove_prone")
    assert any(c["name"] == "prone" for c in g.combatant("Goblin 1").conditions)
    r = g.call("attack", target="Goblin 1", weapon="longsword")
    assert "no attacks left" in r["error"]


def test_escape_needs_the_character_to_be_grappled(make_game):
    g = make_game("fighter")
    g.script(20, 1).ok("start_encounter", monsters=[{"monster": "bandit"}])
    assert "Only a grappled" in g.call("contest", a="character", b="Bandit 1", effect="escape")["error"]
    g.ok("set_condition", target="character", condition="grappled")
    g.script(15, 2)
    r = g.ok("contest", a="character", b="Bandit 1", effect="escape")
    assert r["effect_applied"] == "the Character escaped the grapple"
    assert g.ch.conditions == []


def test_roll_tool_and_invalid_expression(make_game):
    g = make_game("fighter").script(3, 4)
    assert g.ok("roll", expr="2d6+1", purpose="falling rocks")["total"] == 8
    assert "Invalid dice" in g.call("roll", expr="2d6+", purpose="x")["error"]
