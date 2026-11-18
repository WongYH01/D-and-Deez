"""SRD 5.1 tables used by the engine. Section numbers refer to docs/rules/srd-5.1-mechanics.md."""

from __future__ import annotations

import re

ABILITIES = ("str", "dex", "con", "int", "wis", "cha")
ABILITY_NAMES = {
    "strength": "str", "dexterity": "dex", "constitution": "con",
    "intelligence": "int", "wisdom": "wis", "charisma": "cha",
}

# §2.3 Skills and their abilities.
SKILLS = {
    "athletics": "str",
    "acrobatics": "dex", "sleight_of_hand": "dex", "stealth": "dex",
    "arcana": "int", "history": "int", "investigation": "int", "nature": "int", "religion": "int",
    "animal_handling": "wis", "insight": "wis", "medicine": "wis", "perception": "wis", "survival": "wis",
    "deception": "cha", "intimidation": "cha", "performance": "cha", "persuasion": "cha",
}
# §2.3 Tool proficiency; thieves' tools use Dexterity (§12.5 Lock: "Dexterity check").
TOOLS = {"thieves_tools": "dex"}

# §5 Conditions (Appendix PH-A).
CONDITIONS = (
    "blinded", "charmed", "deafened", "exhaustion", "frightened", "grappled", "incapacitated",
    "invisible", "paralyzed", "petrified", "poisoned", "prone", "restrained", "stunned", "unconscious",
)
INCAPACITATING = {"incapacitated", "paralyzed", "petrified", "stunned", "unconscious"}
AUTO_FAIL_STR_DEX = {"paralyzed", "petrified", "stunned", "unconscious"}

DAMAGE_TYPES = (
    "acid", "bludgeoning", "cold", "fire", "force", "lightning", "necrotic",
    "piercing", "poison", "psychic", "radiant", "slashing", "thunder",
)

SIZES = ("tiny", "small", "medium", "large", "huge", "gargantuan")

# §8.1 XP thresholds and §1.2 proficiency bonus.
XP_THRESHOLDS = {1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500}
LEVEL_CAP = 5


def proficiency_bonus(level: int) -> int:
    return 2 + (level - 1) // 4


def ability_mod(score: int) -> int:
    """§1.1: (score - 10) / 2, rounded down."""
    return (score - 10) // 2


# §13.3 Proficiency bonus by CR (only the range M1 monsters need is exercised).
def cr_proficiency(cr: float) -> int:
    if cr < 5:
        return 2
    return 2 + (int(cr) - 1) // 4


# §12.4 Weapons. damage, type, category (simple/martial), kind (melee/ranged), properties,
# and for ammunition weapons the ammunition item they fire.
def _w(damage, dtype, category, kind, props=(), versatile=None, ammo=None):
    return {"damage": damage, "damage_type": dtype, "category": category, "kind": kind,
            "properties": set(props), "versatile": versatile, "ammo": ammo}


WEAPONS = {
    "club": _w("1d4", "bludgeoning", "simple", "melee", ["light"]),
    "dagger": _w("1d4", "piercing", "simple", "melee", ["finesse", "light", "thrown"]),
    "greatclub": _w("1d8", "bludgeoning", "simple", "melee", ["two_handed"]),
    "handaxe": _w("1d6", "slashing", "simple", "melee", ["light", "thrown"]),
    "javelin": _w("1d6", "piercing", "simple", "melee", ["thrown"]),
    "light_hammer": _w("1d4", "bludgeoning", "simple", "melee", ["light", "thrown"]),
    "mace": _w("1d6", "bludgeoning", "simple", "melee"),
    "quarterstaff": _w("1d6", "bludgeoning", "simple", "melee", ["versatile"], "1d8"),
    "sickle": _w("1d4", "slashing", "simple", "melee", ["light"]),
    "spear": _w("1d6", "piercing", "simple", "melee", ["thrown", "versatile"], "1d8"),
    "light_crossbow": _w("1d8", "piercing", "simple", "ranged", ["ammunition", "loading", "two_handed"], ammo="crossbow_bolt"),
    "dart": _w("1d4", "piercing", "simple", "ranged", ["finesse", "thrown"]),
    "shortbow": _w("1d6", "piercing", "simple", "ranged", ["ammunition", "two_handed"], ammo="arrow"),
    "sling": _w("1d4", "bludgeoning", "simple", "ranged", ["ammunition"], ammo="sling_bullet"),
    "battleaxe": _w("1d8", "slashing", "martial", "melee", ["versatile"], "1d10"),
    "flail": _w("1d8", "bludgeoning", "martial", "melee"),
    "glaive": _w("1d10", "slashing", "martial", "melee", ["heavy", "reach", "two_handed"]),
    "greataxe": _w("1d12", "slashing", "martial", "melee", ["heavy", "two_handed"]),
    "greatsword": _w("2d6", "slashing", "martial", "melee", ["heavy", "two_handed"]),
    "halberd": _w("1d10", "slashing", "martial", "melee", ["heavy", "reach", "two_handed"]),
    "lance": _w("1d12", "piercing", "martial", "melee", ["reach", "special"]),
    "longsword": _w("1d8", "slashing", "martial", "melee", ["versatile"], "1d10"),
    "maul": _w("2d6", "bludgeoning", "martial", "melee", ["heavy", "two_handed"]),
    "morningstar": _w("1d8", "piercing", "martial", "melee"),
    "pike": _w("1d10", "piercing", "martial", "melee", ["heavy", "reach", "two_handed"]),
    "rapier": _w("1d8", "piercing", "martial", "melee", ["finesse"]),
    "scimitar": _w("1d6", "slashing", "martial", "melee", ["finesse", "light"]),
    "shortsword": _w("1d6", "piercing", "martial", "melee", ["finesse", "light"]),
    "trident": _w("1d6", "piercing", "martial", "melee", ["thrown", "versatile"], "1d8"),
    "war_pick": _w("1d8", "piercing", "martial", "melee"),
    "warhammer": _w("1d8", "bludgeoning", "martial", "melee", ["versatile"], "1d10"),
    "whip": _w("1d4", "slashing", "martial", "melee", ["finesse", "reach"]),
    "blowgun": _w("1", "piercing", "martial", "ranged", ["ammunition", "loading"], ammo="blowgun_needle"),
    "hand_crossbow": _w("1d6", "piercing", "martial", "ranged", ["ammunition", "light", "loading"], ammo="crossbow_bolt"),
    "heavy_crossbow": _w("1d10", "piercing", "martial", "ranged", ["ammunition", "heavy", "loading", "two_handed"], ammo="crossbow_bolt"),
    "longbow": _w("1d8", "piercing", "martial", "ranged", ["ammunition", "heavy", "two_handed"], ammo="arrow"),
}

# §12.2 Armor: base AC, category, Dex cap.
ARMOR = {
    "padded": {"base": 11, "category": "light", "stealth_disadvantage": True},
    "leather": {"base": 11, "category": "light", "stealth_disadvantage": False},
    "studded_leather": {"base": 12, "category": "light", "stealth_disadvantage": False},
    "hide": {"base": 12, "category": "medium", "stealth_disadvantage": False},
    "chain_shirt": {"base": 13, "category": "medium", "stealth_disadvantage": False},
    "scale_mail": {"base": 14, "category": "medium", "stealth_disadvantage": True},
    "breastplate": {"base": 14, "category": "medium", "stealth_disadvantage": False},
    "half_plate": {"base": 15, "category": "medium", "stealth_disadvantage": True},
    "ring_mail": {"base": 14, "category": "heavy", "stealth_disadvantage": True},
    "chain_mail": {"base": 16, "category": "heavy", "stealth_disadvantage": True},
    "splint": {"base": 17, "category": "heavy", "stealth_disadvantage": True},
    "plate": {"base": 18, "category": "heavy", "stealth_disadvantage": True},
}
SHIELD = "shield"

# §9 Classes.
CLASSES = {
    "fighter": {"hit_die": 10, "avg": 6, "saves": ("str", "con"),
                "weapons": {"simple", "martial"}, "asi_ability": "str"},
    "rogue": {"hit_die": 8, "avg": 5, "saves": ("dex", "int"),
              "weapons": {"simple", "hand_crossbow", "longsword", "rapier", "shortsword"}, "asi_ability": "dex"},
    "barbarian": {"hit_die": 12, "avg": 7, "saves": ("str", "con"),
                  "weapons": {"simple", "martial"}, "asi_ability": "str"},
    "wizard": {"hit_die": 6, "avg": 4, "saves": ("int", "wis"),
               "weapons": {"dagger", "dart", "sling", "quarterstaff", "light_crossbow"}, "asi_ability": "int"},
    "cleric": {"hit_die": 8, "avg": 5, "saves": ("wis", "cha"),
               "weapons": {"simple"}, "asi_ability": "wis"},
}
# R18: SRD Wizard and Cleric tables (identical full-caster slots): spell slots by Character level, indexed by slot level - 1.
SPELL_SLOTS = {1: (2,), 2: (3,), 3: (4, 2), 4: (4, 3), 5: (4, 3, 2)}
# §9.1 Rages per level (levels 1-5).
RAGES = {1: 2, 2: 2, 3: 3, 4: 3, 5: 3}
RAGE_DAMAGE = 2  # +2 for levels 1-8 (§9.1)
RAGE_ROUNDS = 10  # 1 minute (§9.1, §4.1: a round is 6 seconds)
# §9.3 Sneak Attack dice per level (levels 1-5).
SNEAK_ATTACK = {1: "1d6", 2: "1d6", 3: "2d6", 4: "2d6", 5: "3d6"}

# §13.4 XP by CR.
CR_XP = {0: 10, 0.125: 25, 0.25: 50, 0.5: 100, 1: 200, 2: 450, 3: 700, 4: 1100, 5: 1800}


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


ITEM_ALIASES = {
    "arrows": "arrow", "bolt": "crossbow_bolt", "bolts": "crossbow_bolt", "crossbow_bolts": "crossbow_bolt",
    "crossbow_light": "light_crossbow", "crossbow_hand": "hand_crossbow", "crossbow_heavy": "heavy_crossbow",
    "daggers": "dagger", "handaxes": "handaxe", "javelins": "javelin", "darts": "dart",
    "leather_armor": "leather", "studded_leather_armor": "studded_leather", "padded_armor": "padded",
    "half_plate_armor": "half_plate", "thieves_tools": "thieves_tools", "potions_of_healing": "potion_of_healing",
    "sling_bullets": "sling_bullet", "torches": "torch",
}


def item_ref(name: str) -> str:
    s = slug(name)
    return ITEM_ALIASES.get(s, s)
