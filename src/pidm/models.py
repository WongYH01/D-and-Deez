"""SQLAlchemy ORM models. The loaded objects form the Turn's state tree (ADR 0002).

Derived values (ability modifiers, proficiency, skill and save bonuses, AC) are computed
on read in `engine.py`, never stored. JSON columns are replaced, never mutated in place,
so SQLAlchemy sees the change.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Campaign(Base):
    __tablename__ = "campaigns"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    premise: Mapped[str] = mapped_column(Text, default="")
    ruleset: Mapped[str] = mapped_column(String(20), default="srd-5.1")
    status: Mapped[str] = mapped_column(String(20), default="active")

    character: Mapped["Character"] = relationship(back_populates="campaign", uselist=False, cascade="all, delete-orphan")
    quests: Mapped[list["Quest"]] = relationship(back_populates="campaign", cascade="all, delete-orphan", order_by="Quest.id")
    sessions: Mapped[list["Session"]] = relationship(back_populates="campaign", cascade="all, delete-orphan", order_by="Session.id")


class Character(Base):
    __tablename__ = "characters"
    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    name: Mapped[str] = mapped_column(String(100))
    template: Mapped[str] = mapped_column(String(20))
    race: Mapped[str] = mapped_column(String(30))
    char_class: Mapped[str] = mapped_column(String(20))
    subclass: Mapped[str] = mapped_column(String(30))
    size: Mapped[str] = mapped_column(String(10), default="medium")
    level: Mapped[int] = mapped_column(Integer, default=1)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    hp_current: Mapped[int] = mapped_column(Integer)
    hp_max: Mapped[int] = mapped_column(Integer)
    temp_hp: Mapped[int] = mapped_column(Integer, default=0)
    str_score: Mapped[int] = mapped_column("str", Integer)
    dex_score: Mapped[int] = mapped_column("dex", Integer)
    con_score: Mapped[int] = mapped_column("con", Integer)
    int_score: Mapped[int] = mapped_column("int", Integer)
    wis_score: Mapped[int] = mapped_column("wis", Integer)
    cha_score: Mapped[int] = mapped_column("cha", Integer)
    gold: Mapped[int] = mapped_column(Integer, default=0)
    # [{"name": "prone", "until_round": 3 | None, "source": "Goblin 1" | None}]
    conditions: Mapped[list] = mapped_column(JSON, default=list)
    exhaustion: Mapped[int] = mapped_column(Integer, default=0)
    death_successes: Mapped[int] = mapped_column(Integer, default=0)
    death_failures: Mapped[int] = mapped_column(Integer, default=0)
    stable: Mapped[bool] = mapped_column(Boolean, default=False)
    dead: Mapped[bool] = mapped_column(Boolean, default=False)
    hit_dice: Mapped[int] = mapped_column(Integer)  # remaining Hit Dice; total equals level
    # Uses spent since the last rest, e.g. {"rage": 1, "second_wind": 1, "relentless_endurance": 1}
    feature_uses: Mapped[dict] = mapped_column(JSON, default=dict)
    # Short-lived combat flags: hidden, dodging, raging, frenzy, rage_rounds, reckless.
    flags: Mapped[dict] = mapped_column(JSON, default=dict)

    campaign: Mapped[Campaign] = relationship(back_populates="character")
    skills: Mapped[list["Skill"]] = relationship(back_populates="character", cascade="all, delete-orphan")
    inventory: Mapped[list["InventoryItem"]] = relationship(
        back_populates="character", cascade="all, delete-orphan", order_by="InventoryItem.id")

    def score(self, ability: str) -> int:
        return getattr(self, f"{ability}_score")


class Skill(Base):
    __tablename__ = "skills"
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), primary_key=True)
    skill: Mapped[str] = mapped_column(String(30), primary_key=True)
    proficient: Mapped[bool] = mapped_column(Boolean, default=True)
    expertise: Mapped[bool] = mapped_column(Boolean, default=False)
    character: Mapped[Character] = relationship(back_populates="skills")


class InventoryItem(Base):
    __tablename__ = "inventory"
    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"))
    item_ref: Mapped[str] = mapped_column(String(60))
    qty: Mapped[int] = mapped_column(Integer, default=1)
    equipped: Mapped[bool] = mapped_column(Boolean, default=False)
    character: Mapped[Character] = relationship(back_populates="inventory")


class Quest(Base):
    __tablename__ = "quests"
    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="active")
    notes: Mapped[list] = mapped_column(JSON, default=list)
    campaign: Mapped[Campaign] = relationship(back_populates="quests")


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rolling_recap: Mapped[str] = mapped_column(Text, default="")
    final_recap: Mapped[str] = mapped_column(Text, default="")
    campaign: Mapped[Campaign] = relationship(back_populates="sessions")
    encounters: Mapped[list["Encounter"]] = relationship(back_populates="session", cascade="all, delete-orphan", order_by="Encounter.id")


class Encounter(Base):
    __tablename__ = "encounters"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    status: Mapped[str] = mapped_column(String(20), default="active")
    round: Mapped[int] = mapped_column(Integer, default=1)
    active_combatant: Mapped[str] = mapped_column(String(100), default="")
    # order, surprised names, the Character's turn economy, ammunition spent, thrown weapons.
    state: Mapped[dict] = mapped_column(JSON, default=dict)
    session: Mapped[Session] = relationship(back_populates="encounters")
    combatants: Mapped[list["Combatant"]] = relationship(
        back_populates="encounter", cascade="all, delete-orphan", order_by="Combatant.id")


class Combatant(Base):
    __tablename__ = "combatants"
    id: Mapped[int] = mapped_column(primary_key=True)
    encounter_id: Mapped[int] = mapped_column(ForeignKey("encounters.id"))
    name: Mapped[str] = mapped_column(String(100))
    monster_ref: Mapped[str] = mapped_column(String(60))
    hp: Mapped[int] = mapped_column(Integer)
    hp_max: Mapped[int] = mapped_column(Integer)
    ac: Mapped[int] = mapped_column(Integer)
    initiative: Mapped[int] = mapped_column(Integer)
    conditions: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, dead, knocked_out
    encounter: Mapped[Encounter] = relationship(back_populates="combatants")


class Turn(Base):
    __tablename__ = "turns"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    seq: Mapped[int] = mapped_column(Integer)
    player_text: Mapped[str] = mapped_column(Text)
    narration: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20))  # committed, failed
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    tokens_cached: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    rolls: Mapped[list["RollRecord"]] = relationship(back_populates="turn", cascade="all, delete-orphan", order_by="RollRecord.seq")


class RollRecord(Base):
    __tablename__ = "rolls"
    id: Mapped[int] = mapped_column(primary_key=True)
    turn_id: Mapped[int] = mapped_column(ForeignKey("turns.id"))
    seq: Mapped[int] = mapped_column(Integer)
    purpose: Mapped[str] = mapped_column(String(200))
    expr: Mapped[str] = mapped_column(String(100))
    dice: Mapped[list] = mapped_column(JSON)
    total: Mapped[int] = mapped_column(Integer)
    target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(40), nullable=True)
    turn: Mapped[Turn] = relationship(back_populates="rolls")


class SrdMonster(Base):
    __tablename__ = "srd_monsters"
    slug: Mapped[str] = mapped_column(String(60), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    data: Mapped[dict] = mapped_column(JSON)
