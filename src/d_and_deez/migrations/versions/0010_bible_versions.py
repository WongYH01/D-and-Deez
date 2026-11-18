"""bible_versions

Saved bible versions for replanning. A Campaign that already has a bible gets it as version 1.

Revision ID: 0010
Revises: 0009
"""
from alembic import op
import sqlalchemy as sa


revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'bible_versions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('campaign_id', sa.Integer(), sa.ForeignKey('campaigns.id'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('bible', sa.JSON(), nullable=False),
        sa.Column('diff', sa.Text(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.execute("INSERT INTO bible_versions (campaign_id, version, bible) "
               "SELECT id, 1, bible FROM campaigns WHERE bible IS NOT NULL")


def downgrade() -> None:
    op.drop_table('bible_versions')
