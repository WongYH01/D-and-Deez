"""scenes

Finished Scenes with their background-written summaries.

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa


revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'scenes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('sessions.id'), nullable=False),
        sa.Column('start_turn', sa.Integer(), nullable=False),
        sa.Column('end_turn', sa.Integer(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False, server_default=''),
    )


def downgrade() -> None:
    op.drop_table('scenes')
