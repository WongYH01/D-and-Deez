"""m4 server

Campaign setup choices the bible job needs (Template, Character name, backstory hook) and the setup error
of a `failed` Campaign, and how many committed Turns a Session's Rolling recap covers. Status gains generating, ready and failed (a plain string column, so no change).

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa


revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('campaigns') as batch:
        batch.add_column(sa.Column('template', sa.String(length=20), nullable=False, server_default=''))
        batch.add_column(sa.Column('character_name', sa.String(length=100), nullable=False, server_default=''))
        batch.add_column(sa.Column('hook', sa.Text(), nullable=False, server_default=''))
        batch.add_column(sa.Column('setup_error', sa.Text(), nullable=False, server_default=''))
    with op.batch_alter_table('sessions') as batch:
        batch.add_column(sa.Column('rolling_through', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    with op.batch_alter_table('sessions') as batch:
        batch.drop_column('rolling_through')
    with op.batch_alter_table('campaigns') as batch:
        for col in ('setup_error', 'hook', 'character_name', 'template'):
            batch.drop_column(col)
