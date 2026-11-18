"""Rules engine: derived values, d20 tests, damage, healing, conditions, death and dying.

Every rule cites docs/rules/srd-5.1-mechanics.md by section (§) or ruling (R1-R15).
Functions here change only the in-memory state tree (ADR 0002).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session as DbSession

from pidm import srd
from pidm.dice import Dice, Roll, combine_modes
from pidm.models import Campaign, Character, Combatant, Encounter, Session, SrdMonster


class ToolError(Exception):
    """An invalid tool call; the message goes back to Claude and nothing changes."""


@dataclass
class GameState:
    """The Turn's state tree plus the dice that resolve it."""

    db: DbSession
    session: Session
    dice: Dice
    _monsters: dict = field(default_factory=dict)
    turn: int = 0  # seq of the Turn being played; story tools stamp it on Beats, Clues and Secrets

    @property
    def campaign(self) -> Campaign:
        return self.session.campaign

    @property
    def character(self) -> Character:
        return self.session.campaign.character

    @property
    def encounter(self) -> Encounter | None:
        # An Encounter belongs to the Campaign: a fight carries over when its Session closes.
        for sess in self.campaign.sessions:
            for enc in sess.encounters:
                if enc.status == "active":
                    return enc
        return None

    def monster(self, ref: str) -> dict:
        if ref not in self._monsters:
            row = self.db.get(SrdMonster, ref)
            if row is None:
                raise ToolError(f"Unknown monster {ref!r}.")
            self._monsters[ref] = row.data
        return self._monsters[ref]


def load_state(db: DbSession, session_id: int, dice: Dice) -> GameState:
    sess = db.get(Session, session_id)
    if sess is None:
        raise ValueError(f"No session {session_id}")
    return GameState(db=db, session=sess, dice=dice)


# --- conditions (§5) -------------------------------------------------------

def has(entity, name: str) -> bool:
    return any(c["name"] == name for c in entity.conditions)


def add_condition(entity, name: str, until_round: int | None = None, source: str | None = None) -> None:
    # §5: a creature either has a condition or doesn't; keep the longest-lasting instance.
    conds = [c for c in entity.conditions if c["name"] != name]
    old = next((c for c in entity.conditions if c["name"] == name), None)
    if old and (old.get("until_round") is None or (until_round is not None and old["until_round"] > until_round)):
        until_round = old.get("until_round")
        source = source or old.get("source")
    conds.append({"name": name, "until_round": until_round, "source": source})
    entity.conditions = conds


def remove_condition(entity, name: str) -> None:
    entity.conditions = [c for c in entity.conditions if c["name"] != name]


def incapacitated(entity) -> bool:
    return any(c["name"] in srd.INCAPACITATING for c in entity.conditions)


def expire_conditions(entity, round_no: int) -> list[str]:
    """Conditions with a duration end when their last Combat round is over."""
    gone = [c["name"] for c in entity.conditions if c.get("until_round") is not None and c["until_round"] < round_no]
    if gone:
        entity.conditions = [c for c in entity.conditions if c["name"] not in gone]
    return gone


# --- the Character's derived values (computed on read) ------------------------

def mod(ch: Character, ability: str) -> int:
    return srd.ability_mod(ch.score(ability))


def prof(ch: Character) -> int:
    return srd.proficiency_bonus(ch.level)


def hp_max(ch: Character) -> int:
    """Exhaustion level 4 halves the hit point maximum (§5), rounded down (R11)."""
    return ch.hp_max // 2 if ch.exhaustion >= 4 else ch.hp_max


def equipped_armor(ch: Character) -> str | None:
    for it in ch.inventory:
        if it.equipped and it.item_ref in srd.ARMOR:
            return it.item_ref
    return None


def has_shield(ch: Character) -> bool:
    return any(it.equipped and it.item_ref == srd.SHIELD for it in ch.inventory)


def armor_class(ch: Character) -> int:
    armor = equipped_armor(ch)
    dex = mod(ch, "dex")
    if armor:
        a = srd.ARMOR[armor]
        cat = a["category"]
        # §12.2: light adds Dex, medium Dex up to +2, heavy none.
        ac = a["base"] + (dex if cat == "light" else min(dex, 2) if cat == "medium" else 0)
        if ch.char_class == "fighter":
            ac += 1  # Fighting Style Defense while wearing armor (§9.2, R6)
    elif ch.char_class == "barbarian":
        ac = 10 + dex + mod(ch, "con")  # Unarmored Defense (§9.1)
    else:
        # shortcut: SRD 5.1 has no general unarmored AC (§12.3); 10 + Dex is the PHB convention.
        ac = 10 + dex
    if has_shield(ch):
        ac += 2  # §12.2
    return ac


def skill_row(ch: Character, skill: str):
    return next((s for s in ch.skills if s.skill == skill), None)


def check_bonus(ch: Character, skill_or_ability: str) -> tuple[int, str]:
    """Bonus for an ability check: ability mod + proficiency (doubled by Expertise) (§1.2, §2.3, §9.3)."""
    key = skill_or_ability
    if key in srd.ABILITY_NAMES:
        key = srd.ABILITY_NAMES[key]
    if key in srd.ABILITIES:
        return mod(ch, key), key
    ability = srd.SKILLS.get(key) or srd.TOOLS.get(key)
    if ability is None:
        raise ToolError(f"Unknown skill {skill_or_ability!r}. Use one of: {', '.join(sorted(srd.SKILLS) + sorted(srd.TOOLS) + list(srd.ABILITY_NAMES))}.")
    row = skill_row(ch, key)
    bonus = mod(ch, ability)
    if row and row.proficient:
        bonus += prof(ch) * (2 if row.expertise else 1)
    return bonus, ability


def save_bonus(ch: Character, ability: str) -> int:
    b = mod(ch, ability)
    if ability in srd.CLASSES[ch.char_class]["saves"]:
        b += prof(ch)
    return b


# Base walking speed in feet (§10 Races table).
RACE_SPEED = {"human": 30, "lightfoot_halfling": 25, "half_orc": 30}


def speed(ch: Character) -> int:
    """Walking speed: the race's, plus Fast Movement (§9.1) without heavy armor.

    shortcut: exhaustion and conditions that cut speed (§5) are not applied; this is the sheet's base figure.
    """
    base = RACE_SPEED.get(ch.race, 30)  # 30 ft is the common SRD speed
    armor = equipped_armor(ch)
    if ch.char_class == "barbarian" and ch.level >= 5 and not (armor and srd.ARMOR[armor]["category"] == "heavy"):
        base += 10
    return base


def skill_list(ch: Character) -> list[dict]:
    """All 18 skills for the sheet: bonus (expertise included) and whether the Character is proficient (§2.3)."""
    return [{"skill": s, "ability": a, "bonus": check_bonus(ch, s)[0],
             "proficient": bool((row := skill_row(ch, s)) and row.proficient)} for s, a in srd.SKILLS.items()]


def lucky(ch: Character) -> bool:
    return ch.race == "lightfoot_halfling"  # Lucky (§10, R9: always reroll)


def can_act(ch: Character) -> None:
    if ch.dead:
        raise ToolError(f"{ch.name} is dead.")
    if ch.hp_current == 0:
        raise ToolError(f"{ch.name} is at 0 HP and unconscious.")
    if incapacitated(ch):
        raise ToolError(f"{ch.name} is incapacitated and can't take actions.")


# --- monsters ----------------------------------------------------------------

_ABILITY_KEYS = {"str": "strength", "dex": "dexterity", "con": "constitution",
                 "int": "intelligence", "wis": "wisdom", "cha": "charisma"}


def m_mod(data: dict, ability: str) -> int:
    return srd.ability_mod(data[_ABILITY_KEYS[ability]])


def m_prof_value(data: dict, index: str) -> int | None:
    for p in data.get("proficiencies", []):
        if p["proficiency"]["index"] == index:
            return p["value"]
    return None


def m_save_bonus(data: dict, ability: str) -> int:
    v = m_prof_value(data, f"saving-throw-{ability}")
    return v if v is not None else m_mod(data, ability)


def m_check_bonus(data: dict, skill_or_ability: str) -> int:
    key = srd.ABILITY_NAMES.get(skill_or_ability, skill_or_ability)
    if key in srd.ABILITIES:
        return m_mod(data, key)
    if key not in srd.SKILLS:
        raise ToolError(f"Unknown skill {skill_or_ability!r}.")
    v = m_prof_value(data, "skill-" + key.replace("_", "-"))
    return v if v is not None else m_mod(data, srd.SKILLS[key])


def passive_perception(data: dict) -> int:
    return data.get("senses", {}).get("passive_perception", 10 + m_mod(data, "wis"))


# --- d20 tests ----------------------------------------------------------------

def d20_test(state: GameState, bonus: int, purpose: str, *, advantage=False, disadvantage=False,
             is_lucky=False, target: int | None = None, record: bool = True) -> tuple[Roll, int]:
    """Roll d20 + bonus. Returns (roll, natural d20 kept).

    With record=False the caller sets target/outcome and then records it, so the emitted Roll is complete.
    """
    mode = combine_modes(advantage, disadvantage)
    dice, nat = state.dice.d20(mode, lucky=is_lucky)
    expr = {"normal": "d20", "advantage": "2d20kh1", "disadvantage": "2d20kl1"}[mode] + (f"{bonus:+d}" if bonus else "")
    total = nat + bonus
    outcome = None if target is None else ("success" if total >= target else "failure")
    roll = Roll(purpose, expr, dice, total, target, outcome)
    if record:
        state.dice.record(roll)
    return roll, nat


def ask_roll(state: GameState, purpose: str, bonus: int, target: int | None, advantage: bool, disadvantage: bool,
             versus: str | None = None) -> None:
    """Roll prompt: before a d20 Roll for the Character, ask the player to make it (a hook set by the orchestrator).

    Monster and NPC Rolls never call this, and neither does damage.
    """
    if state.dice.prompt:
        state.dice.prompt({"purpose": purpose, "bonus": bonus, "target": target, "versus": versus,
                           "mode": combine_modes(advantage, disadvantage)})


def character_check_modes(ch: Character, ability: str, skill: str | None) -> tuple[bool, bool]:
    adv = dis = False
    if ch.exhaustion >= 1 or has(ch, "poisoned") or has(ch, "frightened"):
        dis = True  # §5 exhaustion 1, poisoned, frightened
    if ability == "str" and ch.flags.get("raging"):
        adv = True  # Rage (§9.1)
    if skill == "stealth":
        armor = equipped_armor(ch)
        if armor and srd.ARMOR[armor]["stealth_disadvantage"]:
            dis = True  # §12.2 Stealth column
    return adv, dis


# --- damage, healing and dying (§4.18-§4.29, R7) ------------------------------------

def set_flag(ch: Character, **kw) -> None:
    flags = dict(ch.flags)
    for k, v in kw.items():
        if v is None:
            flags.pop(k, None)
        else:
            flags[k] = v
    ch.flags = flags


def end_rage(ch: Character) -> dict:
    if not ch.flags.get("raging"):
        return {}
    frenzy = ch.flags.get("frenzy")
    set_flag(ch, raging=None, frenzy=None, rage_rounds=None, rage_kept=None, frenzy_ok=None)
    out = {"rage_ended": True}
    if frenzy:
        out["exhaustion"] = change_exhaustion(ch, 1)["exhaustion"]  # Frenzy (§9.1, R6)
    return out


def change_exhaustion(ch: Character, delta: int) -> dict:
    ch.exhaustion = max(0, min(6, ch.exhaustion + delta))
    if ch.exhaustion >= 6:
        kill(ch)  # §5 exhaustion level 6: death
    ch.hp_current = min(ch.hp_current, hp_max(ch))
    return {"exhaustion": ch.exhaustion, "dead": ch.dead}


def kill(ch: Character) -> None:
    ch.dead = True
    ch.hp_current = 0
    ch.temp_hp = 0
    set_flag(ch, raging=None, frenzy=None, rage_rounds=None, hidden=None, dodging=None)


def resist_character(ch: Character, amount: int, dtype: str) -> int:
    """§4.22: resistance halves (R11 rounds down)."""
    resisted = (ch.flags.get("raging") and dtype in ("bludgeoning", "piercing", "slashing")) or has(ch, "petrified")
    return amount // 2 if resisted else amount


def hurt_character(state: GameState, amount: int, critical: bool = False) -> dict:
    """Apply damage already adjusted for resistance. Temp HP first (§4.24), then 0 HP rules (§4.25-§4.26)."""
    ch = state.character
    out: dict = {"damage": amount}
    if ch.dead or amount <= 0:
        out.update(hp=ch.hp_current, dead=ch.dead)
        return out
    absorbed = min(ch.temp_hp, amount)
    ch.temp_hp -= absorbed
    rest = amount - absorbed
    if absorbed:
        out["temp_hp_absorbed"] = absorbed
    if rest and ch.flags.get("raging"):
        set_flag(ch, rage_kept=True)  # took damage this turn keeps Rage going (§9.1)
    if rest == 0:
        pass
    elif ch.hp_current == 0:
        # §4.26 Damage at 0 hit points.
        if rest >= hp_max(ch):
            kill(ch)
            out["instant_death"] = True
        else:
            ch.stable = False
            ch.death_failures = min(3, ch.death_failures + (2 if critical else 1))
            out["death_save_failures"] = ch.death_failures
            if ch.death_failures >= 3:
                kill(ch)
    else:
        before = ch.hp_current
        ch.hp_current = max(0, before - rest)
        if ch.hp_current == 0:
            remaining = rest - before
            if remaining >= hp_max(ch):
                kill(ch)  # §4.25 Instant Death
                out["instant_death"] = True
            elif ch.race == "half_orc" and not ch.feature_uses.get("relentless_endurance"):
                ch.hp_current = 1  # Relentless Endurance (§10)
                ch.feature_uses = {**ch.feature_uses, "relentless_endurance": 1}
                out["relentless_endurance"] = True
            else:
                fall_unconscious(ch)
                out["unconscious"] = True
    out.update(hp=ch.hp_current, dead=ch.dead)
    if ch.hp_current == 0 and not ch.dead and state.encounter is None:
        out["dying"] = resolve_dying(state)  # R7
        out.update(hp=ch.hp_current, dead=ch.dead)
    return out


def fall_unconscious(ch: Character) -> None:
    """§4.25: unconscious, and an unconscious creature falls prone (§5). Rage ends (§9.1)."""
    add_condition(ch, "unconscious")
    add_condition(ch, "prone")
    ch.death_successes = ch.death_failures = 0
    ch.stable = False
    end_rage(ch)
    set_flag(ch, hidden=None, dodging=None)


def wake(ch: Character) -> None:
    remove_condition(ch, "unconscious")
    ch.death_successes = ch.death_failures = 0
    ch.stable = False


def death_save(state: GameState) -> dict:
    """One death saving throw (§4.26). Lucky applies, as it is a saving throw (§10)."""
    ch = state.character
    _, nat = d20_test(state, 0, f"{ch.name} death saving throw", is_lucky=lucky(ch), target=10)
    out = {"roll": nat}
    if nat == 20:
        ch.hp_current = 1
        wake(ch)
        out["result"] = "regained 1 HP"
    elif nat == 1:
        ch.death_failures = min(3, ch.death_failures + 2)
    elif nat >= 10:
        ch.death_successes += 1
    else:
        ch.death_failures += 1
    if ch.death_failures >= 3:
        kill(ch)
        out["result"] = "dead"
    elif ch.death_successes >= 3:
        ch.stable = True  # §4.27; counts reset on becoming stable (§4.26)
        ch.death_successes = ch.death_failures = 0
        out["result"] = "stable"
    out.update(successes=ch.death_successes, failures=ch.death_failures)
    return out


def resolve_dying(state: GameState) -> dict:
    """R7: outside an Encounter, roll death saves until stable or dead; a stable Character wakes at 1 HP after 1d4 hours."""
    ch = state.character
    saves = []
    while not ch.dead and ch.hp_current == 0 and not ch.stable:
        saves.append(death_save(state))
    out: dict = {"death_saves": saves}
    if ch.stable:
        hours = state.dice.roll("1d4", f"{ch.name} hours unconscious before regaining 1 HP").total
        ch.hp_current = 1
        wake(ch)
        out.update(result="stable", hours_unconscious=hours)
    else:
        out["result"] = "dead" if ch.dead else "regained 1 HP"
    return out


def heal_character(ch: Character, amount: int) -> dict:
    """§4.23: capped at the maximum; the dead can't regain hit points; any healing wakes a dying creature (§4.25)."""
    if ch.dead:
        raise ToolError(f"{ch.name} is dead and can't regain hit points.")
    before = ch.hp_current
    ch.hp_current = min(hp_max(ch), before + amount)
    if before == 0 and ch.hp_current > 0:
        wake(ch)
    return {"healed": ch.hp_current - before, "hp": ch.hp_current, "hp_max": hp_max(ch)}


def resist_monster(data: dict, conditions: list, amount: int, dtype: str) -> tuple[int, str | None]:
    """§4.22: immunity, then resistance halves (R11), then vulnerability doubles."""
    if dtype in data.get("damage_immunities", []):
        return 0, "immune"
    resisted = dtype in data.get("damage_resistances", []) or any(c["name"] == "petrified" for c in conditions)
    note = None
    if resisted:
        amount //= 2
        note = "resistant"
    if dtype in data.get("damage_vulnerabilities", []):
        amount *= 2
        note = "vulnerable"
    return amount, note


def hurt_combatant(state: GameState, c: Combatant, amount: int, dtype: str, *, melee=False, nonlethal=False) -> dict:
    data = state.monster(c.monster_ref)
    dealt, note = resist_monster(data, c.conditions, amount, dtype)
    c.hp = max(0, c.hp - dealt)
    out = {"damage": dealt, "target_hp": c.hp}
    if note:
        out["damage_note"] = note
    if c.hp == 0:
        if nonlethal and melee:
            c.status = "knocked_out"  # §4.29: unconscious and stable
            add_condition(c, "unconscious")
            add_condition(c, "prone")
        else:
            c.status = "dead"  # Monsters die at 0 HP (§4.28, R4)
    out["target_status"] = c.status
    if c.status == "active" and ready_to_flee(c):
        out["ready_to_flee"] = True
    return out


def ready_to_flee(c: Combatant) -> bool:
    # shortcut: a quarter of max HP is a house threshold for "low HP"; tune after play-tests.
    return c.status == "active" and c.hp <= c.hp_max // 4


_RIDER = re.compile(r"DC (\d+) (Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma) saving throw or be knocked prone")


def prone_rider(desc: str) -> tuple[int, str] | None:
    """A stat-block attack that knocks the target prone on a failed save (e.g. the wolf's Bite)."""
    m = _RIDER.search(desc or "")
    if not m:
        return None
    return int(m.group(1)), srd.ABILITY_NAMES[m.group(2).lower()]
