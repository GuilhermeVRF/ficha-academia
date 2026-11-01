"""workout sessions and workout colors

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-01 11:00:00

Existing workouts get plate colors in list order, per user.
"""

import sqlalchemy as sa
from alembic import op

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None

PLATE_COLORS = ['red', 'blue', 'yellow', 'green', 'white']


def upgrade() -> None:
    """Apply this migration."""
    with op.batch_alter_table('workout') as batch:
        batch.add_column(sa.Column('color', sa.String(length=16), nullable=False, server_default='red'))
    _color_existing_workouts()

    op.create_table(
        'workout_session',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('workout_id', sa.String(length=36), nullable=True),
        sa.Column('workout_name', sa.String(length=120), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workout_id'], ['workout.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_workout_session_user_id'), 'workout_session', ['user_id'], unique=False)
    op.create_index(op.f('ix_workout_session_started_at'), 'workout_session', ['started_at'], unique=False)
    op.create_table(
        'session_set',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('exercise_id', sa.String(length=36), nullable=True),
        sa.Column('exercise_name', sa.String(length=200), nullable=False),
        sa.Column('exercise_position', sa.Integer(), nullable=False),
        sa.Column('set_index', sa.Integer(), nullable=False),
        sa.Column('weight_kg', sa.Float(), nullable=False),
        sa.Column('reps', sa.Integer(), nullable=False),
        sa.Column('done', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['workout_session.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['exercise_id'], ['exercise.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_session_set_session_id'), 'session_set', ['session_id'], unique=False)
    op.create_index(op.f('ix_session_set_exercise_id'), 'session_set', ['exercise_id'], unique=False)


def downgrade() -> None:
    """Revert this migration."""
    op.drop_index(op.f('ix_session_set_exercise_id'), table_name='session_set')
    op.drop_index(op.f('ix_session_set_session_id'), table_name='session_set')
    op.drop_table('session_set')
    op.drop_index(op.f('ix_workout_session_started_at'), table_name='workout_session')
    op.drop_index(op.f('ix_workout_session_user_id'), table_name='workout_session')
    op.drop_table('workout_session')
    with op.batch_alter_table('workout') as batch:
        batch.drop_column('color')


def _color_existing_workouts() -> None:
    """Give each user's workouts distinct plate colors following their order."""
    bind = op.get_bind()
    rows = bind.execute(sa.text('SELECT id, user_id FROM workout ORDER BY user_id, position, id')).all()
    index_by_user: dict[str | None, int] = {}
    for workout_id, user_id in rows:
        index = index_by_user.get(user_id, 0)
        index_by_user[user_id] = index + 1
        bind.execute(
            sa.text('UPDATE workout SET color = :color WHERE id = :id'),
            {'color': PLATE_COLORS[index % len(PLATE_COLORS)], 'id': workout_id},
        )
