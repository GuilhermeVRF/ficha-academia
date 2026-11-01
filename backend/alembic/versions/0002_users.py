"""user accounts, sessions and invites

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-01 10:00:00

Existing workouts keep a NULL owner; the first account created claims them.
"""

import sqlalchemy as sa
from alembic import op

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply this migration."""
    op.create_table(
        'app_user',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=254), nullable=False),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('is_admin', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )
    op.create_table(
        'user_session',
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('token_hash'),
    )
    op.create_index(op.f('ix_user_session_user_id'), 'user_session', ['user_id'], unique=False)
    op.create_table(
        'invite',
        sa.Column('code', sa.String(length=32), nullable=False),
        sa.Column('created_by_id', sa.String(length=36), nullable=False),
        sa.Column('used_by_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['app_user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['used_by_id'], ['app_user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('code'),
    )
    with op.batch_alter_table('workout') as batch:
        batch.add_column(sa.Column('user_id', sa.String(length=36), nullable=True))
        batch.create_index(batch.f('ix_workout_user_id'), ['user_id'], unique=False)
        batch.create_foreign_key('fk_workout_user_id', 'app_user', ['user_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    """Revert this migration."""
    with op.batch_alter_table('workout') as batch:
        batch.drop_constraint('fk_workout_user_id', type_='foreignkey')
        batch.drop_index(batch.f('ix_workout_user_id'))
        batch.drop_column('user_id')
    op.drop_table('invite')
    op.drop_index(op.f('ix_user_session_user_id'), table_name='user_session')
    op.drop_table('user_session')
    op.drop_table('app_user')
