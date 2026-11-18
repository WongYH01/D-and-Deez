"""m3 story

Campaign setup choices, the Campaign bible and story position on `campaigns`, and the
story tables `beats`, `secrets`, `clues` and `clocks`.

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa


revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('campaigns') as batch:
        batch.add_column(sa.Column('setting', sa.Text(), nullable=False, server_default=''))
        batch.add_column(sa.Column('tone', sa.String(length=40), nullable=False, server_default=''))
        batch.add_column(sa.Column('length', sa.String(length=20), nullable=False, server_default='one-shot'))
        batch.add_column(sa.Column('lines', sa.Text(), nullable=False, server_default=''))
        batch.add_column(sa.Column('veils', sa.Text(), nullable=False, server_default=''))
        batch.add_column(sa.Column('bible', sa.JSON(), nullable=True))
        batch.add_column(sa.Column('current_act', sa.Integer(), nullable=False, server_default='1'))
        batch.add_column(sa.Column('current_location', sa.String(length=60), nullable=False, server_default=''))
        batch.add_column(sa.Column('last_progress_turn', sa.Integer(), nullable=False, server_default='0'))
        batch.add_column(sa.Column('ending', sa.String(length=20), nullable=True))
    op.create_table('beats',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('campaign_id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=60), nullable=False),
    sa.Column('act', sa.Integer(), nullable=False),
    sa.Column('goal', sa.Text(), nullable=False),
    sa.Column('requires', sa.JSON(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('resolved_turn', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('secrets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('campaign_id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=60), nullable=False),
    sa.Column('act', sa.Integer(), nullable=False),
    sa.Column('revelation', sa.Text(), nullable=False),
    sa.Column('learned_turn', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('clues',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('secret_id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=60), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('location', sa.String(length=60), nullable=False),
    sa.Column('revealed_turn', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['secret_id'], ['secrets.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('clocks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('campaign_id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=60), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('segments', sa.Integer(), nullable=False),
    sa.Column('filled', sa.Integer(), nullable=False),
    sa.Column('consequence', sa.Text(), nullable=False),
    sa.Column('is_main', sa.Boolean(), nullable=False),
    sa.Column('visible', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('clocks')
    op.drop_table('clues')
    op.drop_table('secrets')
    op.drop_table('beats')
    with op.batch_alter_table('campaigns') as batch:
        for col in ('ending', 'last_progress_turn', 'current_location', 'current_act', 'bible', 'veils', 'lines',
                    'length', 'tone', 'setting'):
            batch.drop_column(col)
