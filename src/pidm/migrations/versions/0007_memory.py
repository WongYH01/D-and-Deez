"""memory

Entities, Facts and DM notes. Campaigns made before this revision start with no Entities.

Revision ID: 0007
Revises: 0006
"""
from alembic import op
import sqlalchemy as sa


revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'entities',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('campaign_id', sa.Integer(), sa.ForeignKey('campaigns.id'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('kind', sa.String(20), nullable=False),
        sa.Column('aliases', sa.JSON(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False, server_default=''),
        sa.Column('location_slug', sa.String(60), nullable=False, server_default=''),
    )
    op.create_table(
        'facts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('campaign_id', sa.Integer(), sa.ForeignKey('campaigns.id'), nullable=False),
        sa.Column('subject_id', sa.Integer(), sa.ForeignKey('entities.id'), nullable=False),
        sa.Column('relation', sa.String(100), nullable=False),
        sa.Column('object_id', sa.Integer(), sa.ForeignKey('entities.id'), nullable=False),
        sa.Column('valid_from_turn', sa.Integer(), nullable=False),
        sa.Column('valid_to_turn', sa.Integer(), nullable=True),
        sa.Column('source_turn', sa.Integer(), nullable=False),
    )
    op.create_table(
        'dm_notes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('campaign_id', sa.Integer(), sa.ForeignKey('campaigns.id'), nullable=False),
        sa.Column('note', sa.Text(), nullable=False),
        sa.Column('updated_turn', sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('dm_notes')
    op.drop_table('facts')
    op.drop_table('entities')
