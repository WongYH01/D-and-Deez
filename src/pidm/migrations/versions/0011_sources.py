"""sources

Adventure import: uploaded files (`sources`), their split text (`source_chunks`, FTS5) and `campaigns.source_id`.

Revision ID: 0011
Revises: 0010
"""
from alembic import op
import sqlalchemy as sa


revision = '0011'
down_revision = '0010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'sources',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('author', sa.String(200), nullable=False, server_default=''),
        sa.Column('path', sa.Text(), nullable=False, server_default=''),
        sa.Column('sha256', sa.String(64), nullable=False),
        sa.Column('imported_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.add_column('campaigns', sa.Column('source_id', sa.Integer(), nullable=True))
    # `ref` is the bible Location slug a chunk belongs to ('' for none); rowid keeps the author's order.
    op.execute("CREATE VIRTUAL TABLE source_chunks USING fts5("
               "heading, body, kind UNINDEXED, ref UNINDEXED, source_id UNINDEXED, tokenize='porter unicode61')")


def downgrade() -> None:
    op.execute("DROP TABLE source_chunks")
    op.drop_column('campaigns', 'source_id')
    op.drop_table('sources')
