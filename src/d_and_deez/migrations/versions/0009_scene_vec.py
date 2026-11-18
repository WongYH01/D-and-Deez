"""scene_vec

Scene embeddings for recall (sqlite-vec). Scenes that already have a summary are embedded at startup.

Revision ID: 0009
Revises: 0008
"""
from alembic import op


revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE VIRTUAL TABLE scene_vec USING vec0("
               "scene_id integer primary key, embedding float[384], +model_id text)")


def downgrade() -> None:
    op.execute("DROP TABLE scene_vec")
