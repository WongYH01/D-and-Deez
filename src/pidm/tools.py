"""Tool dispatcher: one entry point that validates a tool call against the state tree and runs it.

An invalid call returns {"error": ...} and changes nothing: every tool validates its
arguments before it rolls or changes state.
"""

from __future__ import annotations

import difflib
from typing import Any, Callable

from sqlalchemy import select

from pidm import rules, srd
from pidm.dice import DiceError, Roll, parse
from pidm.engine import (
    GameState, ToolError, add_condition, armor_class, ask_roll, can_act, change_exhaustion, character_check_modes,
    check_bonus, d20_test, death_save, end_rage, equipped_armor, expire_conditions, has, heal_character,
    hp_max, hurt_character, hurt_combatant, incapacitated, lucky, m_check_bonus, m_mod, m_save_bonus, mod,
    passive_perception, prof, prone_rider, resolve_dying, ready_to_flee, remove_condition, resist_character, save_bonus,
    set_flag,
)
from pidm.models import Combatant, Encounter, InventoryItem, Quest, SpellSlot, SrdItem, SrdMonster, SrdSpell
from pidm.memory import KINDS, t_add_fact, t_retire_fact, t_write_note
from pidm.scenes import t_end_scene
from pidm.story import ENDINGS, t_advance_beat, t_end_campaign, t_move_to, t_reveal_clue, t_tick_clock

CHARACTER = "character"


# --- targets -----------------------------------------------------------------

def _is_character(state: GameState, name: str) -> bool:
    return name.strip().lower() in (CHARACTER, state.character.name.lower())


def _combatant(state: GameState, name: str, *, alive=True) -> Combatant:
    enc = state.encounter
    if enc is None:
        raise ToolError(f"No active Encounter, so there is no Combatant named {name!r}. Valid targets: 'character'.")
    for c in enc.combatants:
        if c.name.lower() == name.strip().lower():
            if alive and c.status != "active":
                raise ToolError(f"{c.name} is {c.status.replace('_', ' ')}.")
            return c
    valid = [c.name for c in enc.combatants if c.status == "active" or not alive]
    raise ToolError(f"Unknown target {name!r}. Valid names: {', '.join(['character'] + valid)}.")


def _target(state: GameState, name: str):
    return state.character if _is_character(state, name) else _combatant(state, name)


# --- inventory ---------------------------------------------------------------

def _item(state: GameState, ref: str) -> InventoryItem | None:
    return next((it for it in state.character.inventory if it.item_ref == ref and it.qty > 0), None)


def _take(state: GameState, ref: str, qty: int) -> None:
    it = _item(state, ref)
    it.qty -= qty
    if it.qty == 0:
        state.character.inventory.remove(it)


def _give(state: GameState, ref: str, qty: int) -> int:
    it = next((i for i in state.character.inventory if i.item_ref == ref), None)
    if it is None:
        it = InventoryItem(item_ref=ref, qty=0, equipped=False)
        state.character.inventory.append(it)
    it.qty += qty
    return it.qty


# --- the Character's turn economy (§4.4-§4.7, R9) ------------------------------------

def _econ(enc: Encounter) -> dict:
    return dict(enc.state.get("economy", {}))


def _set_state(enc: Encounter, **kw) -> None:
    enc.state = {**enc.state, **kw}


def _is_character_turn(state: GameState, enc: Encounter) -> bool:
    order = enc.state["order"]
    return order[enc.state["active_index"]]["kind"] == CHARACTER


def _require_turn(state: GameState) -> tuple[Encounter, dict]:
    enc = state.encounter
    if enc is None:
        raise ToolError("No active Encounter.")
    if not _is_character_turn(state, enc):
        raise ToolError(f"It is {enc.active_combatant}'s turn, not the Character's. Call resolve_npc_turns first.")
    can_act(state.character)
    return enc, _econ(enc)


def _attacks_per_action(state: GameState) -> int:
    ch = state.character
    # Extra Attack at 5th level (§9.1, §9.2).
    return 2 if ch.level >= 5 and ch.char_class in ("fighter", "barbarian") else 1


def _use_action(econ: dict) -> None:
    if econ["actions_used"] >= econ["actions_allowed"]:
        raise ToolError("The Character has no action left this turn.")
    econ["actions_used"] += 1
    econ["attacks_left"] = 0


def _use_bonus(econ: dict) -> None:
    if econ["bonus_used"]:
        raise ToolError("The Character has already used its bonus action this turn (§4.5).")
    econ["bonus_used"] = True


def _attack_slot(state: GameState, econ: dict, *, allow_frenzy: bool) -> str:
    """Spend one attack: from the current Attack action, a new Attack action, or Frenzy's bonus attack."""
    if econ["attacks_left"] > 0:
        econ["attacks_left"] -= 1
        return f"action{econ['actions_used']}"
    if econ["actions_used"] < econ["actions_allowed"]:
        econ["actions_used"] += 1
        econ["attacks_left"] = _attacks_per_action(state) - 1
        return f"action{econ['actions_used']}"
    ch = state.character
    if allow_frenzy and ch.flags.get("frenzy") and ch.flags.get("frenzy_ok") and not econ["bonus_used"]:
        econ["bonus_used"] = True  # Frenzy: one melee weapon attack as a bonus action (§9.1)
        return "bonus"
    raise ToolError("The Character has no attacks left this turn (§4.7 Attack, §9 Extra Attack, R9).")


def _begin_character_turn(state: GameState, enc: Encounter) -> dict:
    ch = state.character
    surprised = CHARACTER in enc.state.get("surprised", [])
    econ = {"surprised": surprised, "actions_used": 0, "actions_allowed": 0 if surprised else 1, "attacks_left": 0,
            "bonus_used": surprised, "reaction_used": surprised, "sneak_used": False, "loading_fired": [],
            "light_weapon": None, "reckless": False, "attacks_made": 0, "action_surge_used": False}
    out: dict = {"turn": "character"}
    if surprised:
        _set_state(enc, surprised=[n for n in enc.state["surprised"] if n != CHARACTER])
        out["surprised"] = "The Character is surprised and can't act this turn; call resolve_npc_turns."
    set_flag(ch, dodging=None, reckless=None)  # Dodge and Reckless last until the start of the next turn (§4.7, §9.1)
    if ch.flags.get("raging"):
        set_flag(ch, frenzy_ok=True if ch.flags.get("frenzy") else None)
    if ch.hp_current == 0 and not ch.dead and not ch.stable:
        out["death_save"] = death_save(state)  # §4.26: at the start of each turn at 0 HP
    _set_state(enc, economy=econ)
    return out


def _end_character_turn(state: GameState) -> dict:
    ch = state.character
    out: dict = {}
    econ = _econ(state.encounter)
    if econ.get("surprised"):
        # §4.2: a surprised creature can't react until its first turn ends.
        _set_state(state.encounter, economy={**econ, "surprised": False, "reaction_used": False})
    if ch.flags.get("raging"):
        rounds = ch.flags.get("rage_rounds", srd.RAGE_ROUNDS) - 1
        # §9.1: Rage ends after 1 minute, or if the turn ends without attacking or taking damage.
        if rounds <= 0 or not ch.flags.get("rage_kept"):
            out.update(end_rage(ch))
        else:
            set_flag(ch, rage_rounds=rounds, rage_kept=None)
    return out


def _advance(state: GameState, enc: Encounter) -> dict | None:
    order = enc.state["order"]
    idx = (enc.state["active_index"] + 1) % len(order)
    expired: dict = {}
    if idx == 0:
        enc.round += 1
        for ent in [state.character, *enc.combatants]:
            gone = expire_conditions(ent, enc.round)
            if gone:
                expired[ent.name] = gone
    _set_state(enc, active_index=idx)
    enc.active_combatant = order[idx]["name"]
    return expired or None


# --- monster turns (R4) --------------------------------------------------------

def _damage(action: dict) -> list[dict]:
    """The action's damage entries; a choice of damage uses its first option (R16)."""
    return [d["from"]["options"][0] if "from" in d else d for d in action.get("damage", [])]


def _count(count) -> int:
    """Attacks a Multiattack part makes (R16)."""
    # shortcut: a non-numeric Multiattack count ("Number of Heads", "1d4") plays as one attack; model it if a playtest needs it.
    return int(count) if str(count).isdigit() else 1


def _resolvable(action: dict) -> bool:
    """An attack the engine can roll: attack bonus and damage (R4, R16)."""
    return "attack_bonus" in action and bool(action.get("damage"))


def _monster_attacks(data: dict) -> list[dict]:
    """Multiattack if the stat block has one (first option), else its best single attack (R4)."""
    actions = {a["name"]: a for a in data.get("actions", [])}
    multi = actions.get("Multiattack")
    plan: list[tuple[str, int]] = []
    if multi:
        if multi.get("actions"):
            plan = [(a["action_name"], _count(a["count"])) for a in multi["actions"]]
        elif multi.get("action_options"):
            opt = multi["action_options"]["from"]["options"][0]
            items = opt["items"] if opt["option_type"] == "multiple" else [opt]
            plan = [(a["action_name"], _count(a["count"])) for a in items]
    out = []
    for name, count in plan:
        if name in actions and _resolvable(actions[name]):
            out += [actions[name]] * count
    if out:
        return out
    attacks = [a for a in data.get("actions", []) if _resolvable(a)]

    def avg(a):
        total = 0
        for d in _damage(a):
            for sign, n, sides in parse(d["damage_dice"]):
                total += sign * (n * (sides + 1) / 2 if sides else n)
        return total

    return [max(attacks, key=avg)] if attacks else []


def _monster_turn(state: GameState, c: Combatant) -> dict:
    ch = state.character
    data = state.monster(c.monster_ref)
    enc = state.encounter
    log: dict = {"combatant": c.name, "attacks": []}
    if c.status != "active":
        log["skipped"] = c.status
        return log
    if c.name in enc.state.get("surprised", []):
        _set_state(enc, surprised=[n for n in enc.state["surprised"] if n != c.name])
        log["skipped"] = "surprised"  # §4.2
        return log
    if incapacitated(c):
        log["skipped"] = "incapacitated"  # §5 Incapacitated
        return log
    if has(c, "prone") and not has(c, "grappled"):
        remove_condition(c, "prone")  # stands up; speed 0 prevents it (R2)
        log["stood_up"] = True
    econ = _econ(enc)
    for action in _monster_attacks(data):
        if ch.dead:
            break
        log["attacks"].append(_monster_attack(state, c, action, econ))
    _set_state(enc, economy=econ)
    return log


def _monster_attack(state: GameState, c: Combatant, action: dict, econ: dict) -> dict:
    ch = state.character
    melee = action.get("desc", "").startswith("Melee")  # R1: melee attacks are within 5 feet
    adv = dis = False
    if has(ch, "prone"):
        adv, dis = (adv or melee), (dis or not melee)  # §5 Prone
    if ch.flags.get("reckless"):
        adv = True  # Reckless Attack (§9.1)
    if any(has(ch, n) for n in ("blinded", "restrained", "paralyzed", "stunned", "unconscious", "petrified")):
        adv = True  # §5: attacks against these conditions have advantage
    if ch.flags.get("dodging") and not incapacitated(ch):
        dis = True  # Dodge (§4.7, R13)
    if ch.flags.get("hidden") or has(ch, "invisible"):
        dis = True  # §4.10 unseen target
    if any(has(c, n) for n in ("poisoned", "blinded", "prone", "restrained")):
        dis = True  # §5: the attacker's own conditions
    if any(x["name"] == "frightened" and x.get("source") in (None, ch.name) for x in c.conditions):
        dis = True  # §5 Frightened, source in sight
    ac = armor_class(ch)
    roll, nat = d20_test(state, action["attack_bonus"], f"{c.name} attacks {ch.name} ({action['name']})",
                         advantage=adv, disadvantage=dis, record=False)
    roll.target = ac
    crit = nat == 20  # §4.9
    hit = crit or (nat != 1 and roll.total >= ac)
    if hit and melee and (has(ch, "paralyzed") or has(ch, "unconscious")):
        crit = True  # §5 auto-crit within 5 feet
    roll.outcome = "critical hit" if crit and hit else "hit" if hit else "miss"
    state.dice.record(roll)
    out: dict = {"action": action["name"], "attack_total": roll.total, "hit": hit, "critical": crit and hit}
    if not hit:
        return out
    total = 0
    for d in _damage(action):
        dtype = d["damage_type"]["index"]
        rolled, amount = state.dice.evaluate(d["damage_dice"], double_dice=crit)  # §4.20 on a crit
        amount = max(0, amount)
        state.dice.record(Roll(
            f"{c.name} {action['name']} damage ({dtype})", d["damage_dice"] + (" (crit)" if crit else ""),
            rolled, amount))
        total += resist_character(ch, amount, dtype)
    if (ch.char_class == "rogue" and ch.level >= 5 and not econ.get("reaction_used")
            and not incapacitated(ch) and ch.hp_current > 0):
        total //= 2  # Uncanny Dodge on the first hit each round (§9.3, R9, R11)
        econ["reaction_used"] = True
        out["uncanny_dodge"] = True
    out.update(hurt_character(state, total, critical=crit))
    rider = prone_rider(action.get("desc", ""))
    if rider and not ch.dead and not has(ch, "prone"):
        dc, ability = rider
        out["save"] = _character_save(state, ability, dc, f"{ch.name} {ability.upper()} save vs {c.name} {action['name']}")
        if not out["save"]["success"]:
            add_condition(ch, "prone", source=c.name)
            out["knocked_prone"] = True
    return out


# --- saves -----------------------------------------------------------------------

def _character_save(state: GameState, ability: str, dc: int, purpose: str, *, advantage=False,
                    disadvantage=False, against: str | None = None) -> dict:
    ch = state.character
    if ability in ("str", "dex") and any(has(ch, n) for n in srd.AUTO_FAIL_STR_DEX):
        state.dice.record(Roll(purpose, "auto-fail", [], 0, dc, "failure"))
        return {"success": False, "auto_fail": True}  # §5
    adv, dis = advantage, disadvantage
    if ability == "str" and ch.flags.get("raging"):
        adv = True  # Rage (§9.1)
    if ability == "dex" and ch.flags.get("dodging") and not incapacitated(ch):
        adv = True  # Dodge (§4.7, R13)
    if (ability == "dex" and ch.char_class == "barbarian" and ch.level >= 2
            and not any(has(ch, n) for n in ("blinded", "deafened")) and not incapacitated(ch)):
        adv = True  # Danger Sense (§9.1)
    if against == "frightened" and ch.race == "lightfoot_halfling":
        adv = True  # Brave (§10)
    if ch.exhaustion >= 3:
        dis = True  # §5 exhaustion 3
    if ability == "dex" and has(ch, "restrained"):
        dis = True  # §5 Restrained
    ask_roll(state, purpose, save_bonus(ch, ability), dc, adv, dis)
    roll, _ = d20_test(state, save_bonus(ch, ability), purpose, advantage=adv, disadvantage=dis,
                       is_lucky=lucky(ch), target=dc)
    return {"success": roll.outcome == "success", "total": roll.total}


def _combatant_save(state: GameState, c: Combatant, ability: str, dc: int, purpose: str, *, advantage=False,
                    disadvantage=False) -> dict:
    if ability in ("str", "dex") and any(has(c, n) for n in srd.AUTO_FAIL_STR_DEX):
        state.dice.record(Roll(purpose, "auto-fail", [], 0, dc, "failure"))
        return {"success": False, "auto_fail": True}  # §5
    dis = disadvantage or (ability == "dex" and has(c, "restrained"))
    roll, _ = d20_test(state, m_save_bonus(state.monster(c.monster_ref), ability), purpose,
                       advantage=advantage, disadvantage=dis, target=dc)
    return {"success": roll.outcome == "success", "total": roll.total}


def _ability(name: str) -> str:
    a = srd.ABILITY_NAMES.get(name.lower(), name.lower())
    if a not in srd.ABILITIES:
        raise ToolError(f"Unknown ability {name!r}.")
    return a


def _condition_name(name: str) -> str:
    n = name.strip().lower()
    if n not in srd.CONDITIONS:
        raise ToolError(f"Unknown condition {name!r}. SRD conditions: {', '.join(srd.CONDITIONS)}.")
    return n


def _until(state: GameState, duration: int | None) -> int | None:
    enc = state.encounter
    if not duration:
        return None
    if enc is None:
        raise ToolError("A duration in Combat rounds needs an active Encounter; omit duration outside combat.")
    return enc.round + duration - 1


# === tools =======================================================================

def t_roll(state: GameState, expr: str, purpose: str) -> dict:
    try:
        parse(expr)
    except DiceError as e:
        raise ToolError(str(e))
    r = state.dice.roll(expr, purpose)
    return {"expr": expr, "dice": r.dice, "total": r.total}


def t_skill_check(state: GameState, skill: str, dc: int, advantage: bool = False, disadvantage: bool = False) -> dict:
    ch = state.character
    key = srd.item_ref(skill)
    bonus, ability = check_bonus(ch, key)
    can_act(ch)
    adv, dis = character_check_modes(ch, ability, key)
    purpose = f"{ch.name} {key.replace('_', ' ')} check"
    ask_roll(state, purpose, bonus, dc, adv or advantage, dis or disadvantage)
    roll, _ = d20_test(state, bonus, purpose, advantage=adv or advantage,
                       disadvantage=dis or disadvantage, is_lucky=lucky(ch), target=dc)
    return {"skill": key, "bonus": bonus, "total": roll.total, "dc": dc, "success": roll.outcome == "success"}


def t_saving_throw(state: GameState, target: str, ability: str, dc: int, advantage: bool = False,
                   disadvantage: bool = False, effect: dict | None = None) -> dict:
    ab = _ability(ability)
    who = _target(state, target)
    effect = effect or {}
    cond = _condition_name(effect["condition"]) if effect.get("condition") else None
    dmg = effect.get("damage")
    dtype = effect.get("damage_type", "bludgeoning")
    if dtype not in srd.DAMAGE_TYPES:
        raise ToolError(f"Unknown damage type {dtype!r}.")
    if dmg is not None:
        try:
            parse(str(dmg))
        except DiceError as e:
            raise ToolError(str(e))
    until = _until(state, effect.get("duration"))
    if who is state.character and cond == "unconscious":
        raise ToolError("The Character falls unconscious only at 0 HP; use damage instead.")
    if who is state.character:
        if who.dead:
            raise ToolError(f"{who.name} is dead.")
        res = _character_save(state, ab, dc, f"{who.name} {ab.upper()} saving throw", advantage=advantage,
                              disadvantage=disadvantage, against=cond)
    else:
        res = _combatant_save(state, who, ab, dc, f"{who.name} {ab.upper()} saving throw",
                              advantage=advantage, disadvantage=disadvantage)
    out = {"target": who.name, "ability": ab, "dc": dc, **res}
    if dmg is not None and (not res["success"] or effect.get("half_on_success")):
        amount = state.dice.roll(str(dmg), f"{who.name} {dtype} damage").total
        if res["success"]:
            amount //= 2  # half on a success, rounded down (R11)
        amount = max(0, amount)
        if who is state.character:
            out["damage"] = hurt_character(state, resist_character(who, amount, dtype))
        else:
            out["damage"] = hurt_combatant(state, who, amount, dtype)
    if cond and not res["success"] and not getattr(who, "dead", False) and getattr(who, "status", "active") == "active":
        if who is state.character and cond == "exhaustion":
            out["exhaustion"] = change_exhaustion(who, 1)
        else:
            add_condition(who, cond, until)
            out["condition_applied"] = cond
    return out


def _contest_bonus(state: GameState, who, skill: str) -> tuple[int, bool, bool, bool]:
    """(bonus, advantage, disadvantage, lucky) for one side of a contest (§2.2)."""
    key = srd.item_ref(skill)
    if who is state.character:
        bonus, ability = check_bonus(who, key)
        adv, dis = character_check_modes(who, ability, key)
        return bonus, adv, dis, lucky(who)
    data = state.monster(who.monster_ref)
    dis = has(who, "poisoned") or has(who, "frightened")  # §5 Poisoned, Frightened
    return m_check_bonus(data, key), False, dis, False


def _best_skill(state: GameState, who) -> str:
    """R9: the defender (or escaper) uses its better of Athletics and Acrobatics."""
    a = _contest_bonus(state, who, "athletics")[0]
    b = _contest_bonus(state, who, "acrobatics")[0]
    return "athletics" if a >= b else "acrobatics"


def t_contest(state: GameState, a: str, b: str, skill_a: str | None = None, skill_b: str | None = None,
              effect: str | None = None) -> dict:
    who_a, who_b = _target(state, a), _target(state, b)
    if who_a is who_b:
        raise ToolError("A contest needs two different participants.")
    econ = enc = None
    if effect in ("grapple", "shove_prone"):
        if who_a is not state.character or who_b is state.character:
            raise ToolError("Grapple and shove are made by the Character against a Combatant (R4, R15).")
        size_a = srd.SIZES.index(state.character.size)
        size_b = srd.SIZES.index(state.monster(who_b.monster_ref)["size"].lower())
        if size_b > size_a + 1:
            raise ToolError(f"{who_b.name} is more than one size larger than the Character (§4.15).")
        skill_a, skill_b = "athletics", _best_skill(state, who_b)
        if state.encounter:
            enc, econ = _require_turn(state)
            _attack_slot(state, econ, allow_frenzy=False)  # replaces one attack (§4.15, §4.16)
            econ["attacks_made"] += 1
        else:
            can_act(state.character)
    elif effect == "escape":
        if who_a is not state.character or not has(who_a, "grappled"):
            raise ToolError("Only a grappled Character can escape (a = 'character').")
        skill_a, skill_b = _best_skill(state, who_a), "athletics"  # §4.15 Escaping a Grapple
        if state.encounter:
            enc, econ = _require_turn(state)
            _use_action(econ)
    elif effect is not None:
        raise ToolError("effect must be grapple, shove_prone or escape.")
    elif not skill_a or not skill_b:
        raise ToolError("skill_a and skill_b are required for a contest without an effect.")
    ba, adv_a, dis_a, luck_a = _contest_bonus(state, who_a, skill_a)
    bb, adv_b, dis_b, luck_b = _contest_bonus(state, who_b, skill_b)
    if enc is not None:
        _set_state(enc, economy=econ)
    if who_a is state.character:  # one prompt, for the Character's side only
        ask_roll(state, f"{who_a.name} {skill_a} (contest)", ba, None, adv_a, dis_a, versus=who_b.name)
    elif who_b is state.character:
        ask_roll(state, f"{who_b.name} {skill_b} (contest)", bb, None, adv_b, dis_b, versus=who_a.name)
    ra, _ = d20_test(state, ba, f"{who_a.name} {skill_a} (contest)", advantage=adv_a, disadvantage=dis_a, is_lucky=luck_a, record=False)
    rb, _ = d20_test(state, bb, f"{who_b.name} {skill_b} (contest)", advantage=adv_b, disadvantage=dis_b, is_lucky=luck_b, record=False)
    winner = who_a.name if ra.total > rb.total else who_b.name if rb.total > ra.total else None  # tie: no change (§2.2)
    ra.outcome = "win" if winner == who_a.name else "tie" if winner is None else "loss"
    rb.outcome = "win" if winner == who_b.name else "tie" if winner is None else "loss"
    state.dice.record(ra)
    state.dice.record(rb)
    out = {"a": who_a.name, "total_a": ra.total, "b": who_b.name, "total_b": rb.total, "winner": winner}
    if winner == who_a.name:
        if effect == "grapple":
            add_condition(who_b, "grappled", source=state.character.name)
            out["effect_applied"] = f"{who_b.name} is grappled"
        elif effect == "shove_prone":
            add_condition(who_b, "prone")
            out["effect_applied"] = f"{who_b.name} is prone"
        elif effect == "escape":
            remove_condition(who_a, "grappled")
            out["effect_applied"] = "the Character escaped the grapple"
    return out


def t_attack(state: GameState, target: str, weapon: str, cover: str | None = None, reckless: bool = False,
             nonlethal: bool = False, offhand: bool = False, thrown: bool = False) -> dict:
    ch = state.character
    enc, econ = _require_turn(state)
    c = _combatant(state, target)
    ref = srd.item_ref(weapon)
    unarmed = ref in ("unarmed", "unarmed_strike", "fist", "fists")
    if unarmed:
        w = {"damage": "1", "damage_type": "bludgeoning", "category": "simple", "kind": "melee", "properties": set(), "ammo": None}
        ref = "unarmed_strike"
    else:
        if ref not in srd.WEAPONS:
            raise ToolError(f"{weapon!r} is not an SRD weapon. Weapons carried: {', '.join(i.item_ref for i in ch.inventory if i.item_ref in srd.WEAPONS)}.")
        if _item(state, ref) is None:
            raise ToolError(f"The Character has no {ref}.")
        w = srd.WEAPONS[ref]
    props = w["properties"]
    if thrown and "thrown" not in props:
        raise ToolError(f"{ref} has no thrown property.")
    thrown = thrown or (w["kind"] == "ranged" and "thrown" in props)  # darts are always thrown
    ranged = w["kind"] == "ranged" or thrown
    if nonlethal and ranged:
        raise ToolError("Only a melee attack can knock a creature out (§4.29).")
    if cover not in (None, "none", "half", "three_quarters"):
        raise ToolError("cover must be half or three_quarters.")
    if reckless and (ch.char_class != "barbarian" or ch.level < 2):
        raise ToolError("Reckless Attack needs a level 2+ Barbarian (§9.1).")
    if reckless and econ["attacks_made"] > 0 and not econ["reckless"]:
        raise ToolError("Reckless Attack must be chosen on the first attack of the turn (§9.1).")
    ammo = w.get("ammo") if "ammunition" in props else None
    if ammo and _item(state, ammo) is None:
        raise ToolError(f"No {ammo} left to fire from the {ref} (§12.4 Ammunition, R5).")
    if offhand:
        if "light" not in props or w["kind"] != "melee":
            raise ToolError("The off-hand weapon must be a light melee weapon (§4.14, R14).")
        if not econ["light_weapon"]:
            raise ToolError("Two-weapon fighting needs an Attack action with a light melee weapon first (§4.14).")
        if econ["light_weapon"] == ref and _item(state, ref).qty < 2:
            raise ToolError("Two-weapon fighting needs a different light weapon in the other hand (§4.14).")
        _use_bonus(econ)
        slot = "bonus"
    else:
        frenzy_ok = not ranged and w["kind"] == "melee"
        slot = _attack_slot(state, econ, allow_frenzy=frenzy_ok)
    if "loading" in props:
        if slot in econ["loading_fired"]:
            raise ToolError(f"The {ref} has the loading property: one shot per action or bonus action (§12.4, R5).")
        econ["loading_fired"] = econ["loading_fired"] + [slot]

    # Ability (§2.10, §4.8): Str for melee and thrown melee weapons, Dex for ranged; finesse takes the higher (R9).
    if "finesse" in props:
        ability = "str" if mod(ch, "str") >= mod(ch, "dex") else "dex"
    else:
        ability = "dex" if w["kind"] == "ranged" else "str"
    ability_mod = mod(ch, ability)
    proficient = unarmed or w["category"] in srd.CLASSES[ch.char_class]["weapons"] or ref in srd.CLASSES[ch.char_class]["weapons"]
    bonus = ability_mod + (prof(ch) if proficient else 0)

    if reckless:
        econ["reckless"] = True
        set_flag(ch, reckless=True)
    melee = not ranged  # R1
    adv = dis = False
    if ch.flags.get("hidden") or has(ch, "invisible"):
        adv = True  # §4.10, R8
    if econ["reckless"] and melee and ability == "str":
        adv = True  # §9.1
    if any(has(c, n) for n in ("blinded", "restrained", "paralyzed", "stunned", "unconscious", "petrified")):
        adv = True  # §5: attacks against these conditions have advantage
    if has(c, "prone"):
        adv, dis = (adv or melee), (dis or ranged)  # §5 Prone with R1
    if any(has(ch, n) for n in ("poisoned", "blinded", "prone", "restrained")) or ch.exhaustion >= 3:
        dis = True  # §5: the attacker's own conditions; exhaustion 3
    if any(x["name"] == "frightened" and x.get("source") in (None, c.name) for x in ch.conditions):
        dis = True  # §5 Frightened, source in sight
    if has(c, "invisible"):
        dis = True  # §5 Invisible
    if "heavy" in props and ch.size == "small":
        dis = True  # §12.4 Heavy
    cover_bonus = {"half": 2, "three_quarters": 5}.get(cover or "", 0)  # §4.17, R3
    ac = c.ac + cover_bonus
    crit_on = 19 if ch.char_class == "fighter" and ch.subclass == "champion" and ch.level >= 3 else 20  # §9.2
    purpose = f"{ch.name} attacks {c.name} with {ref.replace('_', ' ')}"
    ask_roll(state, purpose, bonus, None, adv, dis, versus=c.name)  # AC stays hidden from the player
    roll, nat = d20_test(state, bonus, purpose, advantage=adv, disadvantage=dis, is_lucky=lucky(ch), record=False)
    roll.target = ac
    hit = nat >= crit_on or (nat != 1 and roll.total >= ac)  # §4.9
    crit = hit and nat >= crit_on
    if hit and melee and (has(c, "paralyzed") or has(c, "unconscious")):
        crit = True  # §5 auto-crit within 5 feet
    roll.outcome = "critical hit" if crit else "hit" if hit else "miss"
    state.dice.record(roll)
    mode = "advantage" if adv and not dis else "disadvantage" if dis and not adv else "normal"

    # Commit the action's costs.
    econ["attacks_made"] += 1
    if slot.startswith("action") and "light" in props and w["kind"] == "melee" and not offhand:
        econ["light_weapon"] = ref
    if ch.flags.get("hidden"):
        set_flag(ch, hidden=None)  # attacking reveals the Character (§4.10, R8)
    if ch.flags.get("raging"):
        set_flag(ch, rage_kept=True)
    if ammo:
        _take(state, ammo, 1)
        spent = dict(enc.state.get("ammo_spent", {}))
        spent[ammo] = spent.get(ammo, 0) + 1
        _set_state(enc, ammo_spent=spent)
    if thrown:
        _take(state, ref, 1)
        tw = dict(enc.state.get("thrown", {}))
        tw[ref] = tw.get(ref, 0) + 1
        _set_state(enc, thrown=tw)

    out: dict = {"target": c.name, "weapon": ref, "attack_total": roll.total, "target_ac": ac, "mode": mode,
                 "hit": hit, "critical": crit}
    if hit:
        dice_expr = w["damage"]
        dmg_mod = min(ability_mod, 0) if offhand else ability_mod  # §4.14
        if ch.flags.get("raging") and melee and ability == "str":
            dmg_mod += srd.RAGE_DAMAGE  # §9.1
        parts = [dice_expr]
        sneak = (ch.char_class == "rogue" and not econ["sneak_used"] and mode == "advantage"
                 and ("finesse" in props or w["kind"] == "ranged"))  # §9.3, R8
        if sneak:
            parts.append(srd.SNEAK_ATTACK[ch.level])
            econ["sneak_used"] = True
        dice_vals: list[int] = []
        total = 0
        for p in parts:
            dv, t = state.dice.evaluate(p, double_dice=crit)  # §4.20: crits double every damage die
            dice_vals += dv
            total += t
        if crit and ch.race == "half_orc" and melee and not unarmed:
            dv, t = state.dice.evaluate("1d" + dice_expr.split("d")[1])  # Savage Attacks (§10)
            dice_vals += dv
            total += t
        total = max(0, total + dmg_mod)  # §4.19: never negative
        expr = "+".join(parts) + (f"{dmg_mod:+d}" if dmg_mod else "")
        state.dice.record(Roll(
            f"{ch.name} {ref.replace('_', ' ')} damage" + (" (critical)" if crit else ""), expr, dice_vals, total))
        out["sneak_attack"] = sneak
        out.update(hurt_combatant(state, c, total, w["damage_type"], melee=melee, nonlethal=nonlethal))
    _set_state(enc, economy=econ)
    out["attacks_left"] = econ["attacks_left"] + (econ["actions_allowed"] - econ["actions_used"]) * _attacks_per_action(state)
    out["bonus_action_used"] = econ["bonus_used"]
    return out


def t_apply_damage(state: GameState, target: str, amount: str, damage_type: str, critical: bool = False) -> dict:
    who = _target(state, target)
    if damage_type not in srd.DAMAGE_TYPES:
        raise ToolError(f"Unknown damage type {damage_type!r}. Use one of {', '.join(srd.DAMAGE_TYPES)}.")
    try:
        parse(str(amount))
    except DiceError as e:
        raise ToolError(str(e))
    if who is state.character and who.dead:
        raise ToolError(f"{who.name} is already dead.")
    n = max(0, state.dice.roll(str(amount), f"{who.name} takes {damage_type} damage").total)
    if who is state.character:
        return {"target": who.name, **hurt_character(state, resist_character(who, n, damage_type), critical=critical)}
    return {"target": who.name, **hurt_combatant(state, who, n, damage_type)}


def t_heal(state: GameState, target: str, amount: str, temporary: bool = False) -> dict:
    who = state.character if _is_character(state, target) else _combatant(state, target, alive=False)
    if who is not state.character and who.status == "dead":
        raise ToolError(f"{who.name} is dead.")
    try:
        parse(str(amount))
    except DiceError as e:
        raise ToolError(str(e))
    if who is state.character:
        if who.dead:
            raise ToolError(f"{who.name} is dead and can't regain hit points (§4.23).")
        n = max(0, state.dice.roll(str(amount), f"{who.name} {'temporary HP' if temporary else 'healing'}").total)
        if temporary:
            who.temp_hp = max(who.temp_hp, n)  # temp HP don't stack; keep the higher (§4.24, R9)
            return {"target": who.name, "temp_hp": who.temp_hp}
        return {"target": who.name, **heal_character(who, n)}
    if temporary:
        raise ToolError("Temporary HP can only be given to the Character.")
    n = max(0, state.dice.roll(str(amount), f"{who.name} healing").total)
    before = who.hp
    who.hp = min(who.hp_max, who.hp + n)
    if who.status == "knocked_out" and who.hp > 0:
        who.status = "active"
        remove_condition(who, "unconscious")
    return {"target": who.name, "healed": who.hp - before, "hp": who.hp}


def t_set_condition(state: GameState, target: str, condition: str, on: bool = True, duration: int | None = None) -> dict:
    who = _target(state, target)
    cond = _condition_name(condition)
    until = _until(state, duration) if on else None
    if who is state.character:
        if who.dead:
            raise ToolError(f"{who.name} is dead.")
        if cond == "exhaustion":
            return {"target": who.name, **change_exhaustion(who, 1 if on else -1)}  # §5: one level at a time
        if cond == "unconscious":
            raise ToolError("The Character falls unconscious only at 0 HP; use apply_damage.")
        if cond == "prone" and not on and (has(who, "grappled") or has(who, "restrained")):
            raise ToolError("The Character's speed is 0, so it can't stand up from prone (R2).")
    if on:
        add_condition(who, cond, until)
        if who is state.character and cond in srd.INCAPACITATING:
            set_flag(who, dodging=None)  # Dodge ends when incapacitated (R13)
    else:
        if not has(who, cond):
            raise ToolError(f"{who.name} is not {cond}.")
        if cond == "unconscious" and getattr(who, "status", "") == "knocked_out":
            raise ToolError(f"{who.name} is knocked out at 0 HP; heal it to wake it.")
        remove_condition(who, cond)
    return {"target": who.name, "conditions": [c["name"] for c in who.conditions]}


def t_use_feature(state: GameState, name: str, frenzy: bool = False) -> dict:
    ch = state.character
    feat = srd.item_ref(name)
    can_act(ch)
    enc = state.encounter
    econ = None
    if enc is not None:
        enc, econ = _require_turn(state)
    uses = dict(ch.feature_uses)
    if feat == "rage":
        if ch.char_class != "barbarian":
            raise ToolError("Only a Barbarian can Rage.")
        if ch.flags.get("raging"):
            raise ToolError("The Character is already raging.")
        if uses.get("rage", 0) >= srd.RAGES[ch.level]:
            raise ToolError("No rages left; finish a long rest first (§9.1).")
        armor = equipped_armor(ch)
        if armor and srd.ARMOR[armor]["category"] == "heavy":
            raise ToolError("Rage gives no benefit in heavy armor (§9.1).")
        if frenzy and (ch.subclass != "berserker" or ch.level < 3):
            raise ToolError("Frenzy needs a level 3+ Berserker (§9.1).")
        if econ is not None:
            _use_bonus(econ)
        uses["rage"] = uses.get("rage", 0) + 1
        set_flag(ch, raging=True, frenzy=True if frenzy else None, rage_rounds=srd.RAGE_ROUNDS, rage_kept=None, frenzy_ok=None)
        out = {"feature": "rage", "raging": True, "frenzy": bool(frenzy), "rages_left": srd.RAGES[ch.level] - uses["rage"]}
    elif feat == "second_wind":
        if ch.char_class != "fighter":
            raise ToolError("Only a Fighter has Second Wind.")
        if uses.get("second_wind"):
            raise ToolError("Second Wind is spent until a short or long rest (§9.2).")
        if econ is not None:
            _use_bonus(econ)
        uses["second_wind"] = 1
        n = state.dice.roll(f"1d10+{ch.level}", f"{ch.name} Second Wind").total
        out = {"feature": "second_wind", **heal_character(ch, n)}
    elif feat == "action_surge":
        if ch.char_class != "fighter" or ch.level < 2:
            raise ToolError("Action Surge needs a level 2+ Fighter (§9.2).")
        if uses.get("action_surge"):
            raise ToolError("Action Surge is spent until a short or long rest (§9.2).")
        if econ is None:
            raise ToolError("Action Surge only matters on the Character's turn in an Encounter.")
        if econ["action_surge_used"]:
            raise ToolError("Action Surge can be used only once per turn.")
        uses["action_surge"] = 1
        econ["actions_allowed"] += 1  # a full second Attack action, Extra Attack included (R9)
        econ["action_surge_used"] = True
        out = {"feature": "action_surge", "actions_left": econ["actions_allowed"] - econ["actions_used"]}
    else:
        raise ToolError(f"Unknown feature {name!r}. Usable features: rage, second_wind, action_surge. "
                        "Sneak Attack, Extra Attack and Relentless Endurance apply automatically.")
    ch.feature_uses = uses
    if econ is not None:
        _set_state(enc, economy=econ)
    return out


def t_hide(state: GameState) -> dict:
    ch = state.character
    enc, econ = _require_turn(state)
    cunning = ch.char_class == "rogue" and ch.level >= 2 and not econ["bonus_used"]
    if cunning:
        econ["bonus_used"] = True  # Cunning Action (§9.3)
    else:
        _use_action(econ)
    watchers = [c for c in enc.combatants if c.status == "active" and not incapacitated(c)]
    dc = max((passive_perception(state.monster(c.monster_ref)) for c in watchers), default=0)
    bonus, _ = check_bonus(ch, "stealth")
    adv, dis = character_check_modes(ch, "dex", "stealth")
    _set_state(enc, economy=econ)
    roll, _ = d20_test(state, bonus, f"{ch.name} hides (Stealth vs passive Perception)", advantage=adv,
                       disadvantage=dis, is_lucky=lucky(ch), target=dc)
    hidden = roll.outcome == "success"
    if hidden:
        set_flag(ch, hidden=True)  # R8
    return {"hidden": hidden, "total": roll.total, "dc": dc, "used": "bonus action" if cunning else "action"}


def t_dodge(state: GameState) -> dict:
    enc, econ = _require_turn(state)
    _use_action(econ)
    _set_state(enc, economy=econ)
    set_flag(state.character, dodging=True)  # R13
    return {"dodging": True}


def t_start_encounter(state: GameState, monsters: list, surprise: str = "none") -> dict:
    if state.encounter is not None:
        raise ToolError("An Encounter is already active; end it first.")
    ch = state.character
    can_act(ch)
    if surprise not in ("none", "character", "monsters"):
        raise ToolError("surprise must be none, character or monsters.")
    if not monsters:
        raise ToolError("List at least one monster.")
    groups = []
    for m in monsters:
        ref = srd.slug(m["monster"]).replace("_", "-")
        count = int(m.get("count", 1))
        if not 1 <= count <= 10:
            raise ToolError("count must be between 1 and 10.")
        data = state.monster(ref)  # raises for an unknown monster
        if not any(_resolvable(a) for a in data.get("actions", [])):  # R16
            raise ToolError(f"{data['name']} has no attack action the engine can resolve; pick another monster.")
        groups.append((ref, count))
    enc = Encounter(status="active", round=1, state={})
    state.session.encounters.append(enc)
    entries = []
    # Initiative: a Dexterity check per Combatant (§4.3, R4); ties go to the Character (R9).
    bonus = mod(ch, "dex")
    adv, dis = character_check_modes(ch, "dex", None)
    r, _ = d20_test(state, bonus, f"{ch.name} initiative", advantage=adv, disadvantage=dis, is_lucky=lucky(ch))
    entries.append((r.total, 1, 99, ch.name, CHARACTER))
    seen: dict[str, int] = {}
    for ref, count in groups:
        data = state.monster(ref)
        for _ in range(count):
            seen[data["name"]] = seen.get(data["name"], 0) + 1
            name = f"{data['name']} {seen[data['name']]}"
            r, _ = d20_test(state, m_mod(data, "dex"), f"{name} initiative")
            c = Combatant(name=name, monster_ref=ref, hp=data["hit_points"], hp_max=data["hit_points"],
                          ac=data["armor_class"][0]["value"], initiative=r.total, conditions=[], status="active")
            enc.combatants.append(c)
            entries.append((r.total, 0, data["dexterity"], name, "combatant"))
    entries.sort(key=lambda e: (-e[0], -e[1], -e[2]))
    order = [{"name": e[3], "kind": e[4], "initiative": e[0]} for e in entries]
    surprised = [CHARACTER] if surprise == "character" else [c.name for c in enc.combatants] if surprise == "monsters" else []
    # Before its first turn a surprised Character has no reaction (§4.2, R10).
    enc.state = {"order": order, "active_index": 0, "surprised": surprised, "ammo_spent": {}, "thrown": {},
                 "economy": {"reaction_used": surprise == "character"}}
    enc.active_combatant = order[0]["name"]
    out = {"order": order, "round": 1, "active": enc.active_combatant}
    if order[0]["kind"] == CHARACTER:
        out["character_turn"] = _begin_character_turn(state, enc)
    else:
        out["next_step"] = "A Combatant acts first: call resolve_npc_turns."
    return out


def t_resolve_npc_turns(state: GameState) -> dict:
    enc = state.encounter
    if enc is None:
        raise ToolError("No active Encounter.")
    ch = state.character
    out: dict = {"turns": []}
    if _is_character_turn(state, enc):
        out["character_turn_end"] = _end_character_turn(state)
        exp = _advance(state, enc)
        if exp:
            out.setdefault("expired_conditions", []).append(exp)
    for _ in range(200):  # guard; an order has at most 11 entries
        entry = enc.state["order"][enc.state["active_index"]]
        if entry["kind"] == CHARACTER:
            out["character_turn"] = _begin_character_turn(state, enc)
            if ch.dead:
                out["character_dead"] = True
            break
        if ch.dead:
            out["character_dead"] = True
            break
        c = next(x for x in enc.combatants if x.name == entry["name"])
        out["turns"].append(_monster_turn(state, c))
        exp = _advance(state, enc)
        if exp:
            out.setdefault("expired_conditions", []).append(exp)
    out["round"] = enc.round
    out["character_hp"] = ch.hp_current
    out["fleeing_ready"] = [c.name for c in enc.combatants if ready_to_flee(c)]
    out["combatants_left"] = [c.name for c in enc.combatants if c.status == "active"]
    return out


def t_end_encounter(state: GameState) -> dict:
    enc = state.encounter
    if enc is None:
        raise ToolError("No active Encounter.")
    ch = state.character
    out: dict = {"recovered": {}}
    for ammo, n in enc.state.get("ammo_spent", {}).items():
        back = n // 2  # recover half, rounded down (§12.4, R5)
        if back:
            _give(state, ammo, back)
            out["recovered"][ammo] = back
    for ref, n in enc.state.get("thrown", {}).items():
        _give(state, ref, n)  # thrown weapons recovered (R5)
        out["recovered"][ref] = out["recovered"].get(ref, 0) + n
    out.update(end_rage(ch))
    set_flag(ch, hidden=None, dodging=None, reckless=None)
    for c in list(ch.conditions):
        if c.get("until_round") is not None:
            remove_condition(ch, c["name"])
    enc.status = "ended"
    xp = sum(state.monster(c.monster_ref).get("xp", 0) for c in enc.combatants if c.status != "active")
    out["defeated"] = [c.name for c in enc.combatants if c.status != "active"]
    out["xp_for_defeated"] = xp
    if ch.hp_current == 0 and not ch.dead and not ch.stable:
        out["dying"] = resolve_dying(state)  # R7 once the fight is over
    return out


def t_rest(state: GameState, kind: str, hit_dice: int = 0) -> dict:
    ch = state.character
    if state.encounter is not None:
        raise ToolError("The Character can't rest during an Encounter.")
    if ch.dead:
        raise ToolError(f"{ch.name} is dead.")
    uses = dict(ch.feature_uses)
    if kind == "short":
        if hit_dice < 0:
            raise ToolError("hit_dice can't be negative.")
        spend = min(hit_dice, ch.hit_dice)  # capped at what the Character has (§6.1)
        healed = 0
        die = srd.CLASSES[ch.char_class]["hit_die"]
        for _ in range(spend):
            n = max(0, state.dice.roll(f"1d{die}{mod(ch, 'con'):+d}", f"{ch.name} spends a Hit Die").total)
            healed += heal_character(ch, n)["healed"]
        ch.hit_dice -= spend
        for f in ("second_wind", "action_surge"):
            uses.pop(f, None)  # recover on a short or long rest (§9.2)
        out = {"kind": "short", "hit_dice_spent": spend, "healed": healed, "hp": ch.hp_current, "hit_dice_left": ch.hit_dice}
        if ch.char_class == "wizard" and not uses.get("arcane_recovery"):
            # R18 Arcane Recovery (SRD Wizard): once per day, slots of combined level up to half the Wizard's level
            # rounded up, none 6th or higher. shortcut: the engine picks the highest slots that fit, never asks.
            budget, got = (ch.level + 1) // 2, []
            for s in sorted(ch.spell_slots, key=lambda s: -s.level):
                while s.used and s.level <= budget:
                    s.used -= 1
                    budget -= s.level
                    got.append(s.level)
            if got:
                uses["arcane_recovery"] = 1
                out["arcane_recovery"] = got
        ch.feature_uses = uses
        return out
    if kind != "long":
        raise ToolError("kind must be short or long.")
    if ch.hp_current < 1:
        raise ToolError("A long rest needs at least 1 HP at its start (§6.2).")
    ch.temp_hp = 0  # §4.24
    regained = min(ch.level - ch.hit_dice, max(1, ch.level // 2))  # §6.2, R11
    ch.hit_dice += regained
    ch.feature_uses = {}
    for s in ch.spell_slots:
        s.used = 0  # a long rest restores every slot (R18)
    set_flag(ch, raging=None, frenzy=None, rage_rounds=None, hidden=None)
    exh = change_exhaustion(ch, -1)["exhaustion"] if ch.exhaustion else 0  # §5, §6.2
    ch.hp_current = hp_max(ch)
    ch.death_successes = ch.death_failures = 0
    return {"kind": "long", "hp": ch.hp_current, "hit_dice_regained": regained, "hit_dice_left": ch.hit_dice, "exhaustion": exh}


def _qty(qty: int) -> int:
    if qty < 1:
        raise ToolError("qty must be at least 1.")
    return qty


def t_add_item(state: GameState, item: str, qty: int = 1) -> dict:
    ref = srd.item_ref(item)
    if not ref:
        raise ToolError("item name is empty.")
    return {"item": ref, "qty": _give(state, ref, _qty(qty))}


def t_remove_item(state: GameState, item: str, qty: int = 1) -> dict:
    ref = srd.item_ref(item)
    it = _item(state, ref)
    have = it.qty if it else 0
    if have < _qty(qty):
        raise ToolError(f"The Character has {have} {ref}; can't remove {qty}.")
    _take(state, ref, qty)
    return {"item": ref, "qty": have - qty}


def t_adjust_gold(state: GameState, amount: int, reason: str) -> dict:
    ch = state.character
    if ch.gold + amount < 0:
        raise ToolError(f"The Character has only {ch.gold} gp.")
    ch.gold += amount
    return {"gold": ch.gold, "reason": reason}


def grow_slots(ch) -> None:
    """Raise slot maximums to the table for the Character's level; spent slots stay spent (R18)."""
    have = {s.level: s for s in ch.spell_slots}
    for lvl, n in enumerate(srd.SPELL_SLOTS[ch.level], 1):
        if lvl in have:
            have[lvl].max = n
        else:
            ch.spell_slots.append(SpellSlot(level=lvl, max=n, used=0))


def t_grant_xp(state: GameState, amount: int, reason: str) -> dict:
    ch = state.character
    if amount < 0:
        raise ToolError("XP can't be negative.")
    ch.xp += amount  # XP past level 5 is stored (R6)
    levels = []
    cls = srd.CLASSES[ch.char_class]
    while ch.level < srd.LEVEL_CAP and ch.xp >= srd.XP_THRESHOLDS[ch.level + 1]:
        ch.level += 1
        if ch.level == 4:
            # Template's fixed ASI: +2 to the main ability, max 20 (§8.3, R6).
            a = cls["asi_ability"]
            setattr(ch, f"{a}_score", min(20, ch.score(a) + 2))
        gain = cls["avg"] + mod(ch, "con")  # average HP per level (§8.2, D5)
        ch.hp_max += gain
        if ch.hp_current > 0:
            ch.hp_current += gain
        ch.hit_dice += 1  # one Hit Die per level (§6.3)
        if ch.spell_slots:
            grow_slots(ch)
        levels.append(ch.level)
    return {"xp": ch.xp, "level": ch.level, "levels_gained": levels, "reason": reason, "hp_max": ch.hp_max}


def t_update_quest(state: GameState, quest_id: int | None = None, title: str | None = None,
                   status: str | None = None, note: str | None = None) -> dict:
    if status is not None and status not in ("active", "completed", "failed"):
        raise ToolError("status must be active, completed or failed.")
    if quest_id is None:
        if not title:
            raise ToolError("A new quest needs a title.")
        q = Quest(title=title, status=status or "active", notes=[note] if note else [])
        state.campaign.quests.append(q)
        return {"created": True, "title": q.title, "status": q.status, "quest_index": len(state.campaign.quests)}
    quests = state.campaign.quests
    q = quests[quest_id - 1] if 1 <= quest_id <= len(quests) else None  # quest id = its position in the log
    if q is None:
        raise ToolError(f"No quest {quest_id}. Quests: {[(i, x.title) for i, x in enumerate(state.campaign.quests, 1)]}.")
    if title:
        q.title = title
    if status:
        q.status = status
    if note:
        q.notes = q.notes + [note]
    return {"title": q.title, "status": q.status, "notes": q.notes}


# --- SRD lookups -----------------------------------------------------------------

_SRD_KINDS = {"monster": SrdMonster, "spell": SrdSpell, "item": SrdItem}
_DROPPED = {"url", "image", "updated_at"}


def _strip(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _strip(v) for k, v in value.items() if k not in _DROPPED}
    if isinstance(value, list):
        return [_strip(v) for v in value]
    return value


def t_lookup_srd(state: GameState, kind: str, slug: str) -> dict:
    model = _SRD_KINDS[kind]
    key = "-".join(slug.strip().lower().replace("_", " ").split())
    row = state.db.get(model, key)
    if row is not None:
        return _strip(row.data)
    names = dict(state.db.execute(select(model.slug, model.name)).all())
    similar = [s for s in names if key in s]
    similar += [s for s in difflib.get_close_matches(key, list(names), n=5, cutoff=0.5) if s not in similar]
    raise ToolError(f"No SRD {kind} {key!r}. Similar: {', '.join(similar[:5]) or 'none'}.")


def t_lookup_rule(state: GameState, query: str) -> dict:
    return {"sections": rules.lookup(state.db, query)}


# --- snapshot ------------------------------------------------------------------------

def snapshot(state: GameState) -> dict:
    """Everything Claude may state as a number comes from here or a tool result."""
    ch = state.character
    nxt = srd.XP_THRESHOLDS.get(ch.level + 1)
    feats = {}
    if ch.char_class == "barbarian":
        feats["rage"] = f"{srd.RAGES[ch.level] - ch.feature_uses.get('rage', 0)}/{srd.RAGES[ch.level]} left"
    if ch.char_class == "fighter":
        feats["second_wind"] = "spent" if ch.feature_uses.get("second_wind") else "ready"
        if ch.level >= 2:
            feats["action_surge"] = "spent" if ch.feature_uses.get("action_surge") else "ready"
    if ch.char_class == "rogue":
        feats["sneak_attack"] = srd.SNEAK_ATTACK[ch.level]
    if ch.race == "half_orc":
        feats["relentless_endurance"] = "spent" if ch.feature_uses.get("relentless_endurance") else "ready"
    sheet = {
        "name": ch.name, "race": ch.race, "class": ch.char_class, "subclass": ch.subclass, "level": ch.level,
        "xp": ch.xp, "xp_next_level": nxt, "hp": ch.hp_current, "hp_max": hp_max(ch), "temp_hp": ch.temp_hp,
        "ac": armor_class(ch), "proficiency_bonus": prof(ch),
        "abilities": {a: {"score": ch.score(a), "mod": mod(ch, a)} for a in srd.ABILITIES},
        "saves": {a: save_bonus(ch, a) for a in srd.ABILITIES},
        "skills": {s.skill: check_bonus(ch, s.skill)[0] for s in ch.skills if s.proficient},
        "conditions": [c["name"] for c in ch.conditions], "exhaustion": ch.exhaustion,
        "death_saves": {"successes": ch.death_successes, "failures": ch.death_failures, "stable": ch.stable},
        "dead": ch.dead, "hit_dice": f"{ch.hit_dice}/{ch.level}", "features": feats,
        "status_flags": sorted(k for k, v in ch.flags.items() if v is True and k in ("raging", "frenzy", "hidden", "dodging", "reckless")),
        "spell_slots": [{"level": s.level, "used": s.used, "max": s.max} for s in ch.spell_slots],
        "spells": ch.spells,
        "gold": ch.gold,
        "inventory": [{"item": i.item_ref, "qty": i.qty, **({"equipped": True} if i.equipped else {})} for i in ch.inventory],
    }
    out = {"character": sheet,
           "quests": [{"id": i, "title": q.title, "status": q.status, "notes": q.notes}
                      for i, q in enumerate(state.campaign.quests, 1)]}
    enc = state.encounter
    if enc:
        econ = enc.state.get("economy", {})
        out["encounter"] = {
            "round": enc.round, "active": enc.active_combatant,
            "order": [e["name"] for e in enc.state["order"]],
            "combatants": [{"name": c.name, "hp": c.hp, "hp_max": c.hp_max, "ac": c.ac, "status": c.status,
                            "conditions": [x["name"] for x in c.conditions],
                            **({"ready_to_flee": True} if ready_to_flee(c) else {})} for c in enc.combatants],
            "character_turn": {k: econ.get(k) for k in ("actions_used", "actions_allowed", "attacks_left", "bonus_used", "reaction_used")}
            if _is_character_turn(state, enc) else None,
        }
    return out


# --- schemas and dispatch ---------------------------------------------------------------

_S = {"type": "string"}
_I = {"type": "integer"}
_B = {"type": "boolean"}
_TARGET = {"type": "string", "description": "'character' or a Combatant's exact name, e.g. 'Goblin 1'."}


def _schema(props: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


TOOLS: dict[str, tuple[Callable[..., dict], str, dict]] = {
    "roll": (t_roll, "Roll dice for anything no other tool covers. Never invent dice results.",
             _schema({"expr": {**_S, "description": "e.g. '2d6+3'"}, "purpose": _S}, ["expr", "purpose"])),
    "skill_check": (t_skill_check, "The Character makes an ability check against a DC, using its real modifiers, proficiency and Expertise. skill is a skill (e.g. 'stealth'), 'thieves_tools', or an ability for a plain check (e.g. 'strength').",
                    _schema({"skill": _S, "dc": _I, "advantage": _B, "disadvantage": _B}, ["skill", "dc"])),
    "saving_throw": (t_saving_throw, "A saving throw by the Character or a Combatant. On a failure the effect applies: damage (or half on a success when half_on_success) and/or a condition with an optional duration in Combat rounds.",
                     _schema({"target": _TARGET, "ability": _S, "dc": _I, "advantage": _B, "disadvantage": _B,
                              "effect": _schema({"damage": {**_S, "description": "dice, e.g. '2d6'"}, "damage_type": _S,
                                                 "half_on_success": _B, "condition": _S, "duration": _I}, [])},
                             ["target", "ability", "dc"])),
    "contest": (t_contest, "Opposed check between two participants (e.g. Stealth vs Perception). effect: 'grapple' or 'shove_prone' (Character vs Combatant; replaces one attack; skills chosen by the engine) or 'escape' (the grappled Character escapes; uses its action).",
                _schema({"a": _TARGET, "skill_a": _S, "b": _TARGET, "skill_b": _S,
                         "effect": {"type": "string", "enum": ["grapple", "shove_prone", "escape"]}}, ["a", "b"])),
    "attack": (t_attack, "The Character attacks a Combatant with a carried weapon (or 'unarmed'). Rolls to hit, rolls and applies damage, spends ammunition, applies Sneak Attack, Rage and crits automatically. Enforces attacks per turn.",
               _schema({"target": _TARGET, "weapon": _S,
                        "cover": {"type": "string", "enum": ["none", "half", "three_quarters"]},
                        "reckless": _B, "nonlethal": _B, "offhand": _B,
                        "thrown": {**_B, "description": "Throw a melee weapon with the thrown property."}},
                       ["target", "weapon"])),
    "apply_damage": (t_apply_damage, "Deal damage from a trap, fall or other non-attack source. amount is dice or a number.",
                     _schema({"target": _TARGET, "amount": _S, "damage_type": _S, "critical": _B}, ["target", "amount", "damage_type"])),
    "heal": (t_heal, "Restore hit points (capped at max), or give temporary HP with temporary=true. amount is dice or a number.",
             _schema({"target": _TARGET, "amount": _S, "temporary": _B}, ["target", "amount"])),
    "set_condition": (t_set_condition, "Add (on=true) or remove (on=false) an SRD condition, with an optional duration in Combat rounds. Exhaustion changes by one level.",
                      _schema({"target": _TARGET, "condition": _S, "on": _B, "duration": _I}, ["target", "condition"])),
    "use_feature": (t_use_feature, "Use a class feature: 'rage' (frenzy=true for a Berserker's Frenzy), 'second_wind', or 'action_surge'.",
                    _schema({"name": _S, "frenzy": _B}, ["name"])),
    "hide": (t_hide, "The Character takes the Hide action (a bonus action for a Rogue with Cunning Action): Stealth against the Combatants' best passive Perception. A hidden Character's next attack has advantage.",
             _schema({}, [])),
    "dodge": (t_dodge, "The Character takes the Dodge action: attacks against it have disadvantage until its next turn.", _schema({}, [])),
    "start_encounter": (t_start_encounter, "Start a fight. monsters is a list of {monster, count}; monster is any SRD monster slug (e.g. goblin, wolf, bandit-captain). surprise: none, character or monsters (from a prior Stealth contest).",
                        _schema({"monsters": {"type": "array", "items": _schema({"monster": _S, "count": _I}, ["monster"])},
                                 "surprise": {"type": "string", "enum": ["none", "character", "monsters"]}}, ["monsters"])),
    "resolve_npc_turns": (t_resolve_npc_turns, "End the Character's turn and play every Combatant's turn in initiative order until it is the Character's turn again (rolls the Character's death save when due). Call once at the end of each Character turn in combat.",
                          _schema({}, [])),
    "end_encounter": (t_end_encounter, "End the fight (all foes beaten, fled or surrendered). Recovers half the spent ammunition and all thrown weapons.",
                      _schema({}, [])),
    "rest": (t_rest, "Short rest (spend up to hit_dice Hit Dice) or long rest. Not during an Encounter.",
             _schema({"kind": {"type": "string", "enum": ["short", "long"]}, "hit_dice": _I}, ["kind"])),
    "add_item": (t_add_item, "Add an item to the Character's inventory.", _schema({"item": _S, "qty": _I}, ["item"])),
    "remove_item": (t_remove_item, "Remove an item the Character has.", _schema({"item": _S, "qty": _I}, ["item"])),
    "adjust_gold": (t_adjust_gold, "Add (positive) or spend (negative) gold pieces.", _schema({"amount": _I, "reason": _S}, ["amount", "reason"])),
    "grant_xp": (t_grant_xp, "Grant XP with a reason; levels up automatically at each threshold (max level 5).",
                 _schema({"amount": _I, "reason": _S}, ["amount", "reason"])),
    "update_quest": (t_update_quest, "Create a quest (no quest_id; title required) or update one by id: status (active, completed, failed) and/or a note.",
                     _schema({"quest_id": _I, "title": _S, "status": {"type": "string", "enum": ["active", "completed", "failed"]}, "note": _S}, [])),
    "move_to": (t_move_to, "The Character arrives at a bible Location (slug, e.g. 'loc.mill'). Places you invent are not Locations and need no call.",
                _schema({"location": _S}, ["location"])),
    "advance_beat": (t_advance_beat, "Resolve a Beat of the current Act (slug, e.g. 'act1.beat2') when its goal is met, with a one-line outcome. Beats resolve in any order once their requires are met. Reports when the next Act opens or the Victory condition is met.",
                     _schema({"beat": _S, "outcome": _S}, ["beat", "outcome"])),
    "reveal_clue": (t_reveal_clue, "The Character finds a Clue of the current Act (slug, e.g. 'clue.ledger.1'), wherever it was placed. Returns its text and whether its Secret is now learned.",
                    _schema({"clue": _S}, ["clue"])),
    "tick_clock": (t_tick_clock, "Fill a Clock (slug, e.g. 'clock.ritual') by 1 to 3 segments when time passes, a check fails with consequences, or a threat is ignored. Returns the consequence when the Clock fills.",
                   _schema({"clock": _S, "segments": _I, "reason": _S}, ["clock", "segments", "reason"])),
    "end_campaign": (t_end_campaign, "End the Campaign with an Ending whose condition holds (the Director block says when): victory, defeat or fallen_hero. Then narrate the epilogue.",
                     _schema({"ending": {"type": "string", "enum": list(ENDINGS)}}, ["ending"])),
    "end_scene": (t_end_scene, "End the current Scene: a change of place, the end of an Encounter or a long rest. Changes nothing else.",
                  _schema({"reason": _S}, ["reason"])),
    "add_fact": (t_add_fact, "Record a Fact: a relation between two Entities that is now true (e.g. 'Mira' 'works for' 'The Guild', 'Old Hesta' 'was killed by' 'Abbess Varn'). Names of known NPCs and places resolve by name or alias; a new name needs its kind (subject_kind / object_kind) and becomes an Entity. Record lasting changes, such as deaths, allegiances and ownership.",
                 _schema({"subject": _S, "relation": _S, "object": _S,
                          "subject_kind": {"type": "string", "enum": list(KINDS)},
                          "object_kind": {"type": "string", "enum": list(KINDS)}}, ["subject", "relation", "object"])),
    "retire_fact": (t_retire_fact, "A Fact in <world> stopped being true: retire it by its id. It is kept as history but no longer shown.",
                    _schema({"fact_id": _I}, ["fact_id"])),
    "write_note": (t_write_note, "Keep a DM note for yourself (running jokes, planned callbacks, player preferences, rulings); all notes are shown in <notes> every Turn. With note_id the note is replaced; an empty note deletes it. The notes share a small cap, and at the cap you must update or delete an older note.",
                   _schema({"note": _S, "note_id": _I}, ["note"])),
    "lookup_rule": (t_lookup_rule, "Search the SRD rules prose. Returns the top three matching Rule sections in full, each with its heading path. Changes nothing.",
                    _schema({"query": {**_S, "description": "e.g. 'grapple' or 'falling damage'"}}, ["query"])),
    "lookup_srd": (t_lookup_srd, "Look up an SRD monster, spell or item record by slug (e.g. 'bandit-captain', 'cure-wounds', 'longsword'). Changes nothing.",
                   _schema({"kind": {"type": "string", "enum": ["monster", "spell", "item"]}, "slug": _S}, ["kind", "slug"])),
}


def tool_definitions() -> list[dict]:
    return [{"name": n, "description": d, "input_schema": s} for n, (_, d, s) in TOOLS.items()]


_TYPES = {"string": str, "integer": int, "boolean": bool, "object": dict, "array": list}


def _validate(schema: dict, value: Any, path: str) -> None:
    t = schema.get("type")
    py = _TYPES.get(t)
    if py and (not isinstance(value, py) or (t == "integer" and isinstance(value, bool))):
        raise ToolError(f"{path} must be a {t}.")
    if "enum" in schema and value not in schema["enum"]:
        raise ToolError(f"{path} must be one of {schema['enum']}.")
    if t == "object":
        props = schema.get("properties", {})
        for k in schema.get("required", []):
            if k not in value:
                raise ToolError(f"Missing required argument {path}.{k}." if path != "args" else f"Missing required argument {k!r}.")
        for k, v in value.items():
            if k not in props:
                raise ToolError(f"Unknown argument {k!r}.")
            if v is not None:
                _validate(props[k], v, k)
    if t == "array":
        for i, v in enumerate(value):
            _validate(schema["items"], v, f"{path}[{i}]")


def dispatch(state: GameState, name: str, args: dict | None) -> dict:
    """Run one tool call. Invalid calls return {"error": ...} and change nothing."""
    if name not in TOOLS:
        return {"error": f"Unknown tool {name!r}."}
    fn, _, schema = TOOLS[name]
    args = args or {}
    try:
        _validate(schema, args, "args")
        return fn(state, **{k: v for k, v in args.items() if v is not None})
    except ToolError as e:
        return {"error": str(e)}
