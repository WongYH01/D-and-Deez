"""The three fixed level 1 Templates (R6, R12).

Ability scores use the SRD standard spread 15/14/13/12/10/8 plus racial increases
(§10). Skills: two (Rogue: four) class skills, racial skills, and the Acolyte
background's Insight and Religion (§11, the only SRD 5.1 background). Equipment is
the class starting equipment (§9) plus the Acolyte's 15 gp.
"""

from __future__ import annotations

from pidm import srd
from pidm.models import Campaign, Character, InventoryItem, Skill

_ACOLYTE_SKILLS = ["insight", "religion"]
_ACOLYTE_GEAR = [("holy_symbol", 1), ("prayer_book", 1), ("stick_of_incense", 5), ("vestments", 1), ("common_clothes", 1)]
_DUNGEONEERS_PACK = [("backpack", 1), ("crowbar", 1), ("hammer", 1), ("piton", 10), ("torch", 10),
                     ("tinderbox", 1), ("rations", 10), ("waterskin", 1), ("hempen_rope_50_feet", 1)]
_BURGLARS_PACK = [("backpack", 1), ("ball_bearings_bag_of_1000", 1), ("string_10_feet", 1), ("bell", 1),
                  ("candle", 5), ("crowbar", 1), ("hammer", 1), ("piton", 10), ("hooded_lantern", 1),
                  ("oil_flask", 2), ("rations", 5), ("tinderbox", 1), ("waterskin", 1), ("hempen_rope_50_feet", 1)]
_EXPLORERS_PACK = [("backpack", 1), ("bedroll", 1), ("mess_kit", 1), ("tinderbox", 1), ("torch", 10),
                   ("rations", 10), ("waterskin", 1), ("hempen_rope_50_feet", 1)]

TEMPLATES = {
    # Human (+1 all, §10) Champion Fighter, Fighting Style Defense (R6).
    "fighter": {
        "name": "Bram", "race": "human", "char_class": "fighter", "subclass": "champion", "size": "medium",
        "scores": {"str": 16, "dex": 14, "con": 15, "int": 9, "wis": 13, "cha": 11},
        "skills": ["athletics", "perception"], "expertise": [],
        "equipped": [("chain_mail", 1), ("shield", 1), ("longsword", 1)],
        "gear": [("light_crossbow", 1), ("crossbow_bolt", 20)] + _DUNGEONEERS_PACK,
    },
    # Lightfoot Halfling (Dex +2, Cha +1) Thief Rogue, Expertise in Stealth and thieves' tools (R6).
    "rogue": {
        "name": "Pip", "race": "lightfoot_halfling", "char_class": "rogue", "subclass": "thief", "size": "small",
        "scores": {"str": 8, "dex": 17, "con": 14, "int": 10, "wis": 13, "cha": 13},
        "skills": ["stealth", "acrobatics", "perception", "sleight_of_hand", "thieves_tools"],
        "expertise": ["stealth", "thieves_tools"],
        "equipped": [("leather", 1), ("shortsword", 1)],
        "gear": [("dagger", 2), ("shortbow", 1), ("quiver", 1), ("arrow", 20), ("thieves_tools", 1)] + _BURGLARS_PACK,
    },
    # Half-Orc (Str +2, Con +1; Menacing gives Intimidation) Berserker Barbarian (R6).
    "barbarian": {
        "name": "Grusk", "race": "half_orc", "char_class": "barbarian", "subclass": "berserker", "size": "medium",
        "scores": {"str": 17, "dex": 13, "con": 15, "int": 8, "wis": 12, "cha": 10},
        "skills": ["athletics", "survival", "intimidation"], "expertise": [],
        "equipped": [("greataxe", 1)],
        "gear": [("handaxe", 2), ("javelin", 4)] + _EXPLORERS_PACK,
    },
}


def create_character(campaign: Campaign, template: str, name: str | None = None) -> Character:
    if template not in TEMPLATES:
        raise ValueError(f"Unknown template {template!r}; choose one of {sorted(TEMPLATES)}")
    t = TEMPLATES[template]
    cls = srd.CLASSES[t["char_class"]]
    con_mod = srd.ability_mod(t["scores"]["con"])
    hp = cls["hit_die"] + con_mod  # §9: hit points at 1st level = max die + Con modifier
    ch = Character(
        campaign=campaign, name=name or t["name"], template=template, race=t["race"],
        char_class=t["char_class"], subclass=t["subclass"], size=t["size"], level=1, xp=0,
        hp_current=hp, hp_max=hp, temp_hp=0, gold=15, conditions=[], exhaustion=0,
        death_successes=0, death_failures=0, stable=False, dead=False, hit_dice=1,
        feature_uses={}, flags={},
        **{f"{a}_score": v for a, v in t["scores"].items()},
    )
    for s in t["skills"] + _ACOLYTE_SKILLS:
        ch.skills.append(Skill(skill=s, proficient=True, expertise=s in t["expertise"]))
    for ref, qty in t["equipped"]:
        ch.inventory.append(InventoryItem(item_ref=ref, qty=qty, equipped=True))
    for ref, qty in t["gear"] + _ACOLYTE_GEAR:
        ch.inventory.append(InventoryItem(item_ref=ref, qty=qty, equipped=False))
    return ch
