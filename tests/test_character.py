"""Seam 1: HP, dying, rests, inventory, gold, XP and quests through the tool dispatcher."""


def test_damage_and_heal_capped_at_max(make_game):
    # §4.23
    g = make_game("fighter").script(5, 20)
    g.ok("apply_damage", target="character", amount="1d6", damage_type="slashing")
    r = g.ok("heal", target="character", amount="1d20")
    assert (r["healed"], r["hp"]) == (5, 12)


def test_temp_hp_keep_higher_and_absorb_first(make_game):
    # §4.24, R9
    g = make_game("fighter")
    g.ok("heal", target="character", amount="5", temporary=True)
    assert g.ok("heal", target="character", amount="3", temporary=True)["temp_hp"] == 5
    r = g.ok("apply_damage", target="character", amount="7", damage_type="fire")
    assert r["temp_hp_absorbed"] == 5 and r["hp"] == 10
    g.commit()
    assert (g.ch.temp_hp, g.ch.hp_current) == (0, 10)


def test_instant_death_from_massive_damage(make_game):
    # §4.25: remaining damage >= HP max.
    g = make_game("fighter")
    r = g.ok("apply_damage", target="character", amount="24", damage_type="bludgeoning")
    assert r["instant_death"] and r["dead"]
    assert "dead" in g.call("heal", target="character", amount="5")["error"]


def test_dropping_to_zero_outside_combat_resolves_in_one_step(make_game):
    # R7: death saves until stable, then 1d4 hours, then 1 HP.
    g = make_game("fighter").script(10, 15, 9, 12, 3)
    r = g.ok("apply_damage", target="character", amount="12", damage_type="slashing")
    dying = r["dying"]
    assert dying["result"] == "stable" and dying["hours_unconscious"] == 3
    assert len(dying["death_saves"]) == 4
    g.commit()
    assert g.ch.hp_current == 1 and not any(c["name"] == "unconscious" for c in g.ch.conditions)


def test_dying_outside_combat_can_end_in_death(make_game):
    g = make_game("fighter").script(1, 5)  # natural 1 = two failures, then a third
    r = g.ok("apply_damage", target="character", amount="12", damage_type="slashing")
    assert r["dying"]["result"] == "dead" and g.ch.dead


def test_natural_20_death_save_regains_1_hp(make_game):
    g = make_game("fighter").script(20)
    r = g.ok("apply_damage", target="character", amount="12", damage_type="slashing")
    assert r["dying"]["result"] == "regained 1 HP" and g.ch.hp_current == 1


def test_relentless_endurance_once_per_long_rest(make_game):
    # §10 Relentless Endurance (Half-Orc).
    g = make_game("barbarian")
    r = g.ok("apply_damage", target="character", amount="14", damage_type="slashing")
    assert r["relentless_endurance"] and r["hp"] == 1
    g.script(20)
    r = g.ok("apply_damage", target="character", amount="1", damage_type="slashing")
    assert "relentless_endurance" not in r and r["dying"]["result"] == "regained 1 HP"
    g.ok("rest", kind="long")
    assert g.ok("apply_damage", target="character", amount="14", damage_type="slashing")["relentless_endurance"]


def test_exhaustion_level_4_halves_hp_max_and_6_is_death(make_game):
    g = make_game("fighter")
    for _ in range(4):
        g.ok("set_condition", target="character", condition="exhaustion")
    assert g.ch.hp_current == 6
    g.ok("set_condition", target="character", condition="exhaustion")
    assert g.ok("set_condition", target="character", condition="exhaustion")["dead"]


def test_set_condition_validates_and_reports(make_game):
    g = make_game("fighter")
    assert "Unknown condition" in g.call("set_condition", target="character", condition="sleepy")["error"]
    assert "is not prone" in g.call("set_condition", target="character", condition="prone", on=False)["error"]
    assert "needs an active Encounter" in g.call("set_condition", target="character", condition="prone", duration=2)["error"]


def test_cannot_stand_from_prone_while_grappled(make_game):
    # R2: speed 0 is kept only as "cannot stand from prone".
    g = make_game("fighter")
    g.ok("set_condition", target="character", condition="prone")
    g.ok("set_condition", target="character", condition="grappled")
    assert "speed is 0" in g.call("set_condition", target="character", condition="prone", on=False)["error"]


def test_second_wind_heals_and_recovers_on_short_rest(make_game):
    # §9.2 Second Wind; §6.1 Hit Dice capped at what the Character has.
    g = make_game("fighter")
    g.ok("apply_damage", target="character", amount="8", damage_type="slashing")
    assert g.script(3).ok("use_feature", name="second_wind")["hp"] == 4 + 3 + 1
    assert "spent" in g.call("use_feature", name="second_wind")["error"]
    r = g.script(4).ok("rest", kind="short", hit_dice=3)
    assert (r["hit_dice_spent"], r["healed"], r["hit_dice_left"]) == (1, 4, 0)  # min(3, 1) dice; 1d10 4 + Con 2 capped at 12
    g.script(1).ok("use_feature", name="second_wind")


def test_long_rest_restores_hp_hit_dice_features_and_one_exhaustion(make_game):
    # §6.2: half the total Hit Dice (minimum 1), R11.
    g = make_game("barbarian")
    g.ok("use_feature", name="rage")
    g.ok("set_condition", target="character", condition="exhaustion")
    g.ok("apply_damage", target="character", amount="5", damage_type="fire")
    g.script(4).ok("rest", kind="short", hit_dice=1)
    g.ok("apply_damage", target="character", amount="5", damage_type="fire")
    r = g.ok("rest", kind="long")
    assert (r["hp"], r["hit_dice_regained"], r["exhaustion"]) == (14, 1, 0)
    g.commit()
    assert g.ch.feature_uses == {} and "raging" not in g.ch.flags


def test_no_rest_during_an_encounter(make_game):
    g = make_game("fighter").script(20, 1)
    g.ok("start_encounter", monsters=[{"monster": "goblin"}])
    assert "during an Encounter" in g.call("rest", kind="short")["error"]


def test_items_add_and_remove_and_reject_missing(make_game):
    g = make_game("fighter")
    assert g.ok("add_item", item="Potion of Healing", qty=2)["qty"] == 2
    assert g.ok("remove_item", item="potion of healing")["qty"] == 1
    assert "has 0 rope_of_climbing" in g.call("remove_item", item="rope of climbing")["error"]
    assert "has 1 potion_of_healing" in g.call("remove_item", item="potion of healing", qty=5)["error"]
    g.commit()
    assert next(i.qty for i in g.ch.inventory if i.item_ref == "potion_of_healing") == 1


def test_gold_cannot_go_negative(make_game):
    g = make_game("fighter")
    assert g.ok("adjust_gold", amount=10, reason="loot")["gold"] == 25
    assert "only 25 gp" in g.call("adjust_gold", amount=-30, reason="sword")["error"]


def test_xp_levels_up_with_average_hp_and_template_asi_up_to_5(make_game):
    # §8.1, §8.2 (Fighter fixed 6 + Con 2), §8.3 / R6 (+2 Str at 4), R6 (XP stored past 5).
    g = make_game("fighter")
    r = g.ok("grant_xp", amount=300, reason="goblins")
    assert r["levels_gained"] == [2] and r["hp_max"] == 20 and g.ch.hit_dice == 2
    r = g.ok("grant_xp", amount=20000, reason="dragon")
    assert r["levels_gained"] == [3, 4, 5] and r["level"] == 5 and r["xp"] == 20300
    assert g.ch.str_score == 18 and g.ch.hp_max == 12 + 8 * 4


def test_quests_created_and_updated(make_game):
    g = make_game("fighter")
    g.ok("update_quest", title="Find the missing miller")
    r = g.ok("update_quest", quest_id=1, status="completed", note="Found him in the cellar")
    assert r["status"] == "completed" and r["notes"] == ["Found him in the cellar"]
    assert "No quest 2" in g.call("update_quest", quest_id=2, status="failed")["error"]
    g.commit()
    assert [(q.title, q.status) for q in g.state.campaign.quests] == [("Find the missing miller", "completed")]


def test_invalid_call_changes_nothing(make_game):
    g = make_game("fighter")
    for args in ({"target": "nobody", "amount": "5", "damage_type": "fire"},
                 {"target": "character", "amount": "5", "damage_type": "laser"},
                 {"target": "character", "amount": "5d", "damage_type": "fire"},
                 {"target": "character", "amount": 5, "damage_type": "fire"}):
        assert "error" in g.call("apply_damage", **args)
    assert "Unknown tool" in g.call("cast_spell")["error"]
    g.commit()
    assert g.ch.hp_current == 12 and g.dice.rolls == []


def test_short_rest_spends_the_hit_dice_asked_for(make_game):
    # §6.1: capped only by the Hit Dice the Character has.
    g = make_game("fighter")
    g.ok("grant_xp", amount=300, reason="test")
    r = g.script(3, 4).ok("rest", kind="short", hit_dice=2)
    assert (r["hit_dice_spent"], r["hit_dice_left"]) == (2, 0)


def test_saving_throw_effect_cannot_knock_the_character_unconscious(make_game):
    g = make_game("fighter")
    r = g.call("saving_throw", target="character", ability="con", dc=10, effect={"condition": "unconscious"})
    assert "only at 0 HP" in r["error"] and g.dice.rolls == []
