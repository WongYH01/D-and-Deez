"""Seam 1: attacks, action economy, Encounters and monster turns through the tool dispatcher.

Template numbers (from pidm.templates): Fighter Bram Str 16, Dex 14, AC 19, HP 12, longsword +5 / 1d8+3.
Rogue Pip Dex 17, AC 14, HP 10, shortsword +5 / 1d6+3. Barbarian Grusk Str 17, Con 15, AC 13, HP 14,
greataxe +5 / 1d12+3. Monster Stat blocks are the imported SRD 5.1 records.
"""


def fight(g, *monsters, char_init=20, monster_inits=None, surprise="none"):
    """Start an Encounter; the Character acts first unless told otherwise."""
    inits = monster_inits or [1] * sum(m[1] if isinstance(m, tuple) else 1 for m in monsters)
    g.script(char_init, *inits)
    specs = [{"monster": m[0], "count": m[1]} if isinstance(m, tuple) else {"monster": m} for m in monsters]
    return g.ok("start_encounter", monsters=specs, surprise=surprise)


# --- start_encounter ------------------------------------------------------------

def test_start_encounter_names_combatants_and_rolls_initiative_each(make_game):
    # R4: initiative per Combatant; unique names.
    g = make_game("fighter")
    r = fight(g, ("goblin", 2), "wolf", char_init=10, monster_inits=[15, 3, 12])
    # Goblin 1: 15+2, Wolf 1: 12+2, Bram: 10+2, Goblin 2: 3+2.
    assert [(e["name"], e["initiative"]) for e in r["order"]] == [
        ("Goblin 1", 17), ("Wolf 1", 14), ("Bram", 12), ("Goblin 2", 5)]
    assert r["next_step"].startswith("A Combatant acts first")
    g.commit()
    assert [c.name for c in g.state.encounter.combatants] == ["Goblin 1", "Goblin 2", "Wolf 1"]
    assert g.combatant("Wolf 1").hp == 11 and g.combatant("Goblin 1").ac == 15


def test_initiative_tie_goes_to_the_character(make_game):
    # R9. Bram Dex +2 rolls 10 = 12; goblin Dex +2 rolls 10 = 12.
    g = make_game("fighter")
    r = fight(g, "goblin", char_init=10, monster_inits=[10])
    assert r["order"][0]["name"] == "Bram"


def test_unknown_monster_and_second_encounter_are_rejected(make_game):
    g = make_game("fighter")
    assert "Unknown monster" in g.call("start_encounter", monsters=[{"monster": "dragon"}])["error"]
    fight(g, "goblin")
    assert "already active" in g.call("start_encounter", monsters=[{"monster": "goblin"}])["error"]


# --- attack ---------------------------------------------------------------------

def test_attack_hits_rolls_damage_and_kills_monster_at_0_hp(make_game):
    # §4.8, §4.19, §4.28 / R4.
    g = make_game("fighter")
    fight(g, "goblin")
    g.script(10, 5)
    r = g.ok("attack", target="Goblin 1", weapon="longsword")
    assert (r["attack_total"], r["hit"], r["damage"]) == (15, True, 8)
    assert r["target_status"] == "dead"
    assert [x.outcome for x in g.last_rolls] == ["hit", None]
    g.commit()
    assert g.combatant("Goblin 1").status == "dead"


def test_natural_one_misses(make_game):
    # §4.9, §4.20
    g = make_game("fighter")
    fight(g, "bandit-captain")
    g.script(1)
    r = g.ok("attack", target="Bandit Captain 1", weapon="longsword")
    assert not r["hit"]


def test_critical_hit_doubles_weapon_dice(make_game):
    g = make_game("fighter")
    fight(g, "bandit-captain")
    g.script(20, 6, 7)
    r = g.ok("attack", target="Bandit Captain 1", weapon="longsword")
    assert r["critical"] and r["damage"] == 6 + 7 + 3


def test_unknown_target_lists_valid_names(make_game):
    g = make_game("fighter")
    fight(g, ("goblin", 2))
    r = g.call("attack", target="Goblin", weapon="longsword")
    assert "Valid names: character, Goblin 1, Goblin 2" in r["error"]


def test_weapon_must_be_carried(make_game):
    g = make_game("fighter")
    fight(g, "goblin")
    assert "no rapier" in g.call("attack", target="Goblin 1", weapon="rapier")["error"]


def test_attack_rejected_when_not_the_characters_turn(make_game):
    g = make_game("fighter")
    fight(g, "goblin", char_init=1, monster_inits=[20])
    assert "resolve_npc_turns" in g.call("attack", target="Goblin 1", weapon="longsword")["error"]


def test_only_one_attack_per_turn_at_level_1(make_game):
    # R9 action economy.
    g = make_game("fighter")
    fight(g, "bandit-captain")
    g.script(2).ok("attack", target="Bandit Captain 1", weapon="longsword")
    assert "no attacks left" in g.call("attack", target="Bandit Captain 1", weapon="longsword")["error"]


def test_extra_attack_and_action_surge_at_level_5(make_game):
    # §9.2 Extra Attack; Action Surge grants a full second Attack action (R9).
    g = make_game("fighter")
    g.ok("grant_xp", amount=6500, reason="test")
    fight(g, "bandit-captain")
    g.script(2).ok("attack", target="Bandit Captain 1", weapon="longsword")
    assert g.script(2).ok("attack", target="Bandit Captain 1", weapon="longsword")["attacks_left"] == 0
    assert "no attacks left" in g.call("attack", target="Bandit Captain 1", weapon="longsword")["error"]
    assert g.ok("use_feature", name="action_surge")["actions_left"] == 1
    g.script(2).ok("attack", target="Bandit Captain 1", weapon="longsword")
    g.script(2).ok("attack", target="Bandit Captain 1", weapon="longsword")
    assert "no attacks left" in g.call("attack", target="Bandit Captain 1", weapon="longsword")["error"]
    assert "spent" in g.call("use_feature", name="action_surge")["error"]


def test_champion_crits_on_19_from_level_3(make_game):
    # §9.2 Improved Critical.
    g = make_game("fighter")
    g.ok("grant_xp", amount=900, reason="test")
    fight(g, "bandit-captain")
    g.script(19, 1, 1)
    r = g.ok("attack", target="Bandit Captain 1", weapon="longsword")
    assert r["critical"] and r["damage"] == 5


def test_cover_adds_to_target_ac(make_game):
    # §4.17, R3: half cover +2.
    g = make_game("fighter")
    fight(g, "goblin")
    g.script(10)
    r = g.ok("attack", target="Goblin 1", weapon="longsword", cover="half")
    assert r["target_ac"] == 17 and not r["hit"]


def test_nonlethal_melee_knocks_out(make_game):
    # §4.29, R4
    g = make_game("fighter")
    fight(g, "goblin")
    r = g.script(15, 8).ok("attack", target="Goblin 1", weapon="longsword", nonlethal=True)
    assert r["target_status"] == "knocked_out"
    assert any(c["name"] == "unconscious" for c in g.combatant("Goblin 1").conditions)


def test_prone_target_gives_melee_advantage_and_auto_crit_on_unconscious(make_game):
    # §5 Prone / Unconscious with R1 (melee counts as within 5 feet).
    g = make_game("fighter")
    fight(g, "bandit-captain")
    g.ok("set_condition", target="Bandit Captain 1", condition="unconscious")
    g.script(3, 12, 2, 2)
    r = g.ok("attack", target="Bandit Captain 1", weapon="longsword")
    assert r["mode"] == "advantage" and r["critical"] and r["damage"] == 7


def test_skeleton_takes_double_bludgeoning(make_game):
    # §4.22 vulnerability.
    g = make_game("fighter")
    fight(g, "skeleton")
    r = g.ok("apply_damage", target="Skeleton 1", amount="3", damage_type="bludgeoning")
    assert r["damage"] == 6 and r["target_hp"] == 7


def test_low_hp_monster_is_flagged_ready_to_flee(make_game):
    g = make_game("fighter")
    fight(g, "bandit-captain")
    r = g.script(49).ok("apply_damage", target="Bandit Captain 1", amount="1d100", damage_type="slashing")
    assert r["ready_to_flee"] and r["target_hp"] == 16


# --- Rogue: Sneak Attack, two-weapon fighting, hide ---------------------------------------

def test_sneak_attack_with_advantage_once_per_turn_and_offhand_without_modifier(make_game):
    # §9.3 Sneak Attack (R8: only via advantage), §4.14 / R14 two-weapon fighting.
    g = make_game("rogue")
    fight(g, "bandit-captain")
    g.ok("set_condition", target="Bandit Captain 1", condition="restrained")
    r = g.script(15, 3, 4, 6).ok("attack", target="Bandit Captain 1", weapon="shortsword")
    assert r["mode"] == "advantage" and r["sneak_attack"] and r["damage"] == 4 + 6 + 3
    r = g.script(14, 2, 3).ok("attack", target="Bandit Captain 1", weapon="dagger", offhand=True)
    assert r["hit"] and not r["sneak_attack"] and r["damage"] == 3
    assert r["bonus_action_used"]


def test_sneak_attack_dice_double_on_a_crit(make_game):
    # §4.20
    g = make_game("rogue")
    fight(g, "bandit-captain")
    g.ok("set_condition", target="Bandit Captain 1", condition="restrained")
    r = g.script(20, 2, 1, 2, 3, 4).ok("attack", target="Bandit Captain 1", weapon="shortsword")
    assert r["critical"] and r["damage"] == 1 + 2 + 3 + 4 + 3


def test_no_sneak_attack_without_advantage(make_game):
    g = make_game("rogue")
    fight(g, "bandit-captain")
    r = g.script(15, 4).ok("attack", target="Bandit Captain 1", weapon="shortsword")
    assert not r["sneak_attack"] and r["damage"] == 7


def test_offhand_needs_a_light_melee_attack_first(make_game):
    g = make_game("rogue")
    fight(g, "bandit-captain")
    assert "Attack action with a light melee weapon first" in g.call(
        "attack", target="Bandit Captain 1", weapon="dagger", offhand=True)["error"]


def test_hide_with_cunning_action_then_attack_with_advantage(make_game):
    # R8: Stealth vs best passive Perception; hidden gives advantage; attacking ends hidden.
    g = make_game("rogue")
    g.ok("grant_xp", amount=300, reason="test")
    fight(g, "goblin", "wolf", monster_inits=[1, 1])
    r = g.script(10).ok("hide")
    assert (r["dc"], r["total"], r["hidden"], r["used"]) == (13, 17, True, "bonus action")
    r = g.script(4, 12, 3, 5).ok("attack", target="Goblin 1", weapon="shortsword")
    assert r["mode"] == "advantage" and r["sneak_attack"]
    assert "hidden" not in g.ch.flags


def test_ranged_attack_spends_ammunition_and_recovers_half(make_game):
    # §12.4 Ammunition, R5.
    g = make_game("rogue")
    fight(g, "bandit-captain")
    g.ok("remove_item", item="arrow", qty=17)
    g.script(2).ok("attack", target="Bandit Captain 1", weapon="shortbow")
    # Captain's turn: three attacks miss.
    g.script(1, 1, 1).ok("resolve_npc_turns")
    g.script(2).ok("attack", target="Bandit Captain 1", weapon="shortbow")
    g.script(1, 1, 1).ok("resolve_npc_turns")
    g.script(2).ok("attack", target="Bandit Captain 1", weapon="shortbow")
    g.script(1, 1, 1).ok("resolve_npc_turns")
    assert "No arrow left" in g.call("attack", target="Bandit Captain 1", weapon="shortbow")["error"]
    r = g.ok("end_encounter")
    assert r["recovered"] == {"arrow": 1}
    g.commit()
    assert next(i.qty for i in g.ch.inventory if i.item_ref == "arrow") == 1


def test_loading_weapon_fires_once_per_action(make_game):
    # §12.4 Loading, R5: even with Extra Attack.
    g = make_game("fighter")
    g.ok("grant_xp", amount=6500, reason="test")
    fight(g, "bandit-captain")
    g.script(2).ok("attack", target="Bandit Captain 1", weapon="light crossbow")
    assert "loading" in g.call("attack", target="Bandit Captain 1", weapon="light crossbow")["error"]


def test_thrown_weapon_leaves_inventory_and_returns_at_end(make_game):
    # R5
    g = make_game("barbarian")
    fight(g, "bandit-captain")
    g.script(2).ok("attack", target="Bandit Captain 1", weapon="handaxe", thrown=True)
    assert next(i.qty for i in g.ch.inventory if i.item_ref == "handaxe") == 1
    assert g.ok("end_encounter")["recovered"] == {"handaxe": 1}
    assert next(i.qty for i in g.ch.inventory if i.item_ref == "handaxe") == 2


# --- Barbarian: Rage, Reckless, Frenzy ----------------------------------------------

def test_rage_adds_damage_and_halves_physical_damage(make_game):
    # §9.1 Rage.
    g = make_game("barbarian")
    fight(g, "bandit-captain")
    assert g.ok("use_feature", name="rage")["rages_left"] == 1
    r = g.script(15, 6).ok("attack", target="Bandit Captain 1", weapon="greataxe")
    assert r["damage"] == 6 + 3 + 2
    r = g.script(9).ok("apply_damage", target="character", amount="1d10", damage_type="slashing")
    assert r["damage"] == 4 and g.ch.hp_current == 10


def test_rage_ends_if_turn_passes_without_attacking_or_taking_damage(make_game):
    g = make_game("barbarian")
    fight(g, "goblin")
    g.ok("use_feature", name="rage")
    r = g.script(1).ok("resolve_npc_turns")  # goblin misses
    assert r["character_turn_end"]["rage_ended"]
    assert "raging" not in g.ch.flags


def test_reckless_attack_gives_advantage_both_ways(make_game):
    # §9.1 Reckless Attack.
    g = make_game("barbarian")
    g.ok("grant_xp", amount=300, reason="test")
    fight(g, "bandit-captain")
    r = g.script(3, 16, 1).ok("attack", target="Bandit Captain 1", weapon="greataxe", reckless=True)
    assert r["mode"] == "advantage"
    g.script(2, 1, 1, 1, 1, 1).ok("resolve_npc_turns")
    assert all(x.expr.startswith("2d20kh1") for x in g.last_rolls)


def test_frenzy_bonus_attack_and_exhaustion_when_rage_ends(make_game):
    # §9.1 Frenzy, R6.
    g = make_game("barbarian")
    g.ok("grant_xp", amount=900, reason="test")
    assert g.ch.level == 3
    fight(g, "bandit-captain")
    g.ok("use_feature", name="rage", frenzy=True)
    g.script(2).ok("attack", target="Bandit Captain 1", weapon="greataxe")
    assert "no attacks left" in g.call("attack", target="Bandit Captain 1", weapon="greataxe")["error"]
    g.script(1, 1, 1).ok("resolve_npc_turns")
    g.script(2).ok("attack", target="Bandit Captain 1", weapon="greataxe")
    g.script(2).ok("attack", target="Bandit Captain 1", weapon="greataxe")  # frenzy bonus attack
    r = g.ok("end_encounter")
    assert r["rage_ended"] and r["exhaustion"] == 1


# --- monster turns ------------------------------------------------------------------

def test_resolve_npc_turns_plays_multiattack_and_stops_at_character(make_game):
    # R4: Multiattack (first option: two scimitar, one dagger).
    g = make_game("fighter")
    fight(g, "bandit-captain")
    g.script(2).ok("attack", target="Bandit Captain 1", weapon="longsword")
    g.script(15, 3, 1, 14, 4, 12)  # scimitar 20 hits AC 19 for 6; scimitar misses; dagger 19 hits for 7; death save
    r = g.ok("resolve_npc_turns")
    attacks = r["turns"][0]["attacks"]
    assert [a["action"] for a in attacks] == ["Scimitar", "Scimitar", "Dagger"]
    assert [a["hit"] for a in attacks] == [True, False, True]
    assert r["character_hp"] == 0  # 12 - 6 - 7: unconscious, not instant death
    assert r["round"] == 2 and "character_turn" in r


def test_monsters_skip_their_first_turn_when_surprised(make_game):
    # §4.2, R10
    g = make_game("fighter")
    fight(g, "goblin", char_init=1, monster_inits=[20], surprise="monsters")
    r = g.ok("resolve_npc_turns")
    assert r["turns"][0]["skipped"] == "surprised"


def test_surprised_character_cannot_act_on_first_turn(make_game):
    g = make_game("fighter")
    r = fight(g, "goblin", surprise="character")
    assert "surprised" in r["character_turn"]
    assert "no attacks left" in g.call("attack", target="Goblin 1", weapon="longsword")["error"]


def test_incapacitated_monster_skips_its_turn(make_game):
    g = make_game("fighter")
    fight(g, "goblin")
    g.ok("set_condition", target="Goblin 1", condition="stunned")
    assert g.ok("resolve_npc_turns")["turns"][0]["skipped"] == "incapacitated"


def test_condition_duration_expires_at_end_of_its_rounds(make_game):
    g = make_game("fighter")
    fight(g, "goblin")
    g.ok("set_condition", target="Goblin 1", condition="poisoned", duration=1)
    r = g.script(1, 1).ok("resolve_npc_turns")  # poisoned goblin misses (disadvantage); then round 2 ends the condition
    assert r["expired_conditions"] == [{"Goblin 1": ["poisoned"]}]


def test_dodge_gives_attackers_disadvantage(make_game):
    # R13
    g = make_game("fighter")
    fight(g, "goblin")
    g.ok("dodge")
    assert "no attacks left" in g.call("attack", target="Goblin 1", weapon="longsword")["error"]
    g.script(18, 2).ok("resolve_npc_turns")
    assert g.state.dice.rolls[-1].expr == "2d20kl1+4" and g.state.dice.rolls[-1].outcome == "miss"


def test_wolf_bite_can_knock_the_character_prone(make_game):
    g = make_game("rogue")
    fight(g, "wolf")
    # bite 19 hits; 2d4 = 4 +2; Str save 3-1 = 2 fails DC 11, and so does the Steady Nerve reroll (R20)
    g.script(15, 2, 2, 3, 3).ok("resolve_npc_turns")
    assert any(c["name"] == "prone" for c in g.ch.conditions)


def test_unconscious_character_makes_death_saves_on_its_turn(make_game):
    # §4.26
    g = make_game("rogue")
    fight(g, "goblin")
    g.script(10).ok("apply_damage", target="character", amount="1d10", damage_type="slashing")
    assert g.ch.hp_current == 0 and any(c["name"] == "unconscious" for c in g.ch.conditions)
    r = g.script(3, 5, 12).ok("resolve_npc_turns")  # goblin misses (adv 3,5 -> 9 vs 14); death save 12
    assert r["character_turn"]["death_save"]["successes"] == 1


def test_damage_at_zero_hp_counts_as_failed_saves_and_crit_counts_two(make_game):
    g = make_game("rogue")
    fight(g, "goblin")
    g.script(10).ok("apply_damage", target="character", amount="1d10", damage_type="slashing")
    g.script(12, 3, 1, 1, 15).ok("resolve_npc_turns")  # melee hit on unconscious = crit: 2 failures; then death save 15
    g.commit()
    assert (g.ch.death_failures, g.ch.death_successes) == (2, 1)


def test_uncanny_dodge_halves_the_first_hit_each_round(make_game):
    # §9.3, R9
    g = make_game("rogue")
    g.ok("grant_xp", amount=6500, reason="test")
    fight(g, "bandit-captain")
    hp = g.ch.hp_current
    g.script(15, 5, 15, 5, 1).ok("resolve_npc_turns")  # two scimitar hits for 8 each; dagger misses
    assert g.ch.hp_current == hp - 4 - 8


# --- end_encounter --------------------------------------------------------------

def test_end_encounter_reports_xp_for_defeated(make_game):
    g = make_game("fighter")
    fight(g, "goblin")
    g.script(10, 5).ok("attack", target="Goblin 1", weapon="longsword")
    r = g.ok("end_encounter")
    assert r["defeated"] == ["Goblin 1"] and r["xp_for_defeated"] == 50
    g.commit()
    assert g.state.encounter is None


def test_knocked_out_monster_can_be_healed_awake(make_game):
    # §4.29: a knocked-out creature is a prisoner, not dead.
    g = make_game("fighter")
    fight(g, "goblin")
    g.script(15, 8).ok("attack", target="Goblin 1", weapon="longsword", nonlethal=True)
    r = g.ok("heal", target="Goblin 1", amount="2")
    assert r["hp"] == 2 and g.combatant("Goblin 1").status == "active"


def test_surprised_rogue_has_no_reaction_before_its_first_turn(make_game):
    # §4.2, R10: no Uncanny Dodge while surprised.
    g = make_game("rogue")
    g.ok("grant_xp", amount=6500, reason="test")
    hp = g.ch.hp_current
    fight(g, "bandit-captain", char_init=2, monster_inits=[20], surprise="character")
    g.script(15, 5, 1, 1, 1).ok("resolve_npc_turns")  # one scimitar hit for 8, then misses
    assert g.ch.hp_current == hp - 8


def test_monster_damage_roll_records_its_dice(make_game):
    g = make_game("fighter")
    fight(g, "wolf")
    g.script(2).ok("attack", target="Wolf 1", weapon="longsword")
    g.script(18, 3, 2, 15).ok("resolve_npc_turns")  # bite hits; 2d4 = 3, 2; Str save 15 passes
    dmg = next(x for x in g.last_rolls if "damage" in x.purpose)
    assert (dmg.dice, dmg.total) == ([3, 2], 7)


def test_reckless_not_allowed_after_a_grapple(make_game):
    # §9.1: Reckless is chosen on the first attack of the turn; a grapple replaces an attack.
    g = make_game("barbarian")
    g.ok("grant_xp", amount=6500, reason="test")
    fight(g, "bandit-captain")
    g.script(15, 2).ok("contest", a="character", b="Bandit Captain 1", effect="grapple")
    assert "first attack" in g.call("attack", target="Bandit Captain 1", weapon="greataxe", reckless=True)["error"]


# --- Encounters belong to the Campaign (M4) ----------------------------------------

def test_an_encounter_started_in_one_session_continues_in_the_next(make_game):
    # A fight carries over when a Session closes (design: Data model, "One open session").
    from datetime import datetime, timezone
    from pidm.models import Session

    g = make_game("fighter")
    fight(g, "goblin", char_init=1, monster_inits=[20])  # Goblin 1 (22) acts before Bram (3)
    g.state.session.ended_at = datetime.now(timezone.utc)
    nxt = Session(campaign=g.state.campaign)
    g.db.add(nxt)
    g.db.commit()
    g.session_id = nxt.id
    g.commit()
    assert g.state.session.id == nxt.id and g.state.encounter is not None
    g.script(2)  # the goblin's scimitar: 2+4 = 6 misses AC 19
    r = g.ok("resolve_npc_turns")
    assert r["turns"][0]["attacks"][0]["hit"] is False and r["character_turn"] == {"turn": "character"}
