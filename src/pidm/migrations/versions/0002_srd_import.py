"""m2 srd import

Imports the full SRD 5.1 dataset vendored from 5e-bits/5e-database (src/2014/en/ at commit
536928f7460b5e5343dfb1805ded15706616765e, CC-BY-4.0): monsters, spells, items, and the rules
prose split into one rules_fts row per markdown heading.

Revision ID: 0002
Revises: 0001
"""
import json
import re
from importlib import resources

from alembic import op
import sqlalchemy as sa


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None

M1_MONSTERS = ("bandit", "bandit-captain", "goblin", "skeleton", "wolf")


def _load(name: str) -> list[dict]:
    return json.loads(resources.files("pidm.data").joinpath(f"5e-SRD-{name}.json").read_text(encoding="utf-8"))


def _rows(records: list[dict]) -> list[dict]:
    return [{"slug": r["index"], "name": r["name"], "data": r} for r in records]


def _srd_table(name: str):
    return sa.table(name, sa.column("slug", sa.String), sa.column("name", sa.String), sa.column("data", sa.JSON))


def _split(name: str, desc: str) -> list[tuple[str, str]]:
    """One (heading path, body) row per markdown heading; text before the first heading goes under `name`."""
    rows: list[tuple[str, str]] = []
    stack: list[tuple[int, str]] = []
    path, body = name, []
    for line in desc.splitlines():
        m = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if not m:
            body.append(line)
            continue
        rows.append((path, "\n".join(body).strip()))
        level = len(m.group(1))
        stack = [s for s in stack if s[0] < level] + [(level, m.group(2))]
        path, body = " > ".join(t for _, t in stack), []
    rows.append((path, "\n".join(body).strip()))
    return [r for r in rows if r[1]]


def upgrade() -> None:
    srd_monsters = _srd_table("srd_monsters")
    op.execute(srd_monsters.delete())
    op.bulk_insert(srd_monsters, _rows(_load("Monsters")))
    for table, records in (("srd_spells", _load("Spells")), ("srd_items", _load("Equipment") + _load("Magic-Items"))):
        op.create_table(table,
        sa.Column('slug', sa.String(length=60), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('slug')
        )
        op.bulk_insert(_srd_table(table), _rows(records))
    # Porter stemming lets "grapple" match "Grappling".
    op.execute("CREATE VIRTUAL TABLE rules_fts USING fts5(section, body, tokenize='porter unicode61')")
    rows = [row for s in _load("Rule-Sections") for row in _split(s["name"], s["desc"])]
    rows += [(f"Conditions > {c['name']}", "\n".join(c["desc"])) for c in _load("Conditions")]
    fts = sa.table("rules_fts", sa.column("section", sa.Text), sa.column("body", sa.Text))
    op.bulk_insert(fts, [{"section": s, "body": b} for s, b in rows])


def downgrade() -> None:
    op.execute("DROP TABLE rules_fts")
    op.drop_table('srd_items')
    op.drop_table('srd_spells')
    srd_monsters = _srd_table("srd_monsters")
    op.execute(srd_monsters.delete().where(srd_monsters.c.slug.not_in(M1_MONSTERS)))
