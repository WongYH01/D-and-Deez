"""spell slots

Spell slots and a Character's known spells. Characters made before this revision are non-casters.

Revision ID: 0008
Revises: 0007
"""
from alembic import op
import sqlalchemy as sa


revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('characters') as batch:
        batch.add_column(sa.Column('spells', sa.JSON(), nullable=False, server_default='{}'))
    op.create_table(
        'spell_slots',
        sa.Column('character_id', sa.Integer(), sa.ForeignKey('characters.id'), primary_key=True),
        sa.Column('level', sa.Integer(), primary_key=True),
        sa.Column('max', sa.Integer(), nullable=False),
        sa.Column('used', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    op.drop_table('spell_slots')
    with op.batch_alter_table('characters') as batch:
        batch.drop_column('spells')
