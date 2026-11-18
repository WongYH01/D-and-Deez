"""playtest fixes

Player notes (one free-text page per Campaign) and the Auto-roll setting.

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa


revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('campaigns') as batch:
        batch.add_column(sa.Column('player_notes', sa.Text(), nullable=False, server_default=''))
        batch.add_column(sa.Column('auto_roll', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table('campaigns') as batch:
        batch.drop_column('auto_roll')
        batch.drop_column('player_notes')
