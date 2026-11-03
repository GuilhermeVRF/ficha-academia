"""exercise library

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-03 12:00:00

Loads the shared library from app/data/exercises.json and links existing
exercises whose name matches a library name exactly (ignoring case and accents).
"""

import sqlalchemy as sa
from alembic import op

from app.services.catalog import load_library, search_key

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply this migration."""
    catalog = op.create_table(
        'catalog_exercise',
        sa.Column('id', sa.String(length=80), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('name_pt', sa.String(length=200), nullable=False),
        sa.Column('name_en', sa.String(length=200), nullable=False),
        sa.Column('muscle_group', sa.String(length=20), nullable=False),
        sa.Column('equipment', sa.String(length=40), nullable=False),
        sa.Column('images', sa.JSON(), nullable=False),
        sa.Column('search_text', sa.String(length=500), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_catalog_exercise_user_id'), 'catalog_exercise', ['user_id'], unique=False)
    with op.batch_alter_table('exercise') as batch:
        batch.add_column(sa.Column('catalog_id', sa.String(length=80), nullable=True))
        batch.create_index(batch.f('ix_exercise_catalog_id'), ['catalog_id'], unique=False)
        batch.create_foreign_key('fk_exercise_catalog_id', 'catalog_exercise', ['catalog_id'], ['id'], ondelete='SET NULL')

    library = load_library()
    op.bulk_insert(catalog, library)
    _link_existing_exercises(library)


def downgrade() -> None:
    """Revert this migration."""
    with op.batch_alter_table('exercise') as batch:
        batch.drop_constraint('fk_exercise_catalog_id', type_='foreignkey')
        batch.drop_index(batch.f('ix_exercise_catalog_id'))
        batch.drop_column('catalog_id')
    op.drop_index(op.f('ix_catalog_exercise_user_id'), table_name='catalog_exercise')
    op.drop_table('catalog_exercise')


def _link_existing_exercises(library: list[dict]) -> None:
    """Give photos to exercises already named exactly like a library entry."""
    by_name = {search_key(row['name_pt']): row['id'] for row in library}
    bind = op.get_bind()
    for exercise_id, name in bind.execute(sa.text('SELECT id, name FROM exercise')).all():
        catalog_id = by_name.get(search_key(name))
        if catalog_id:
            bind.execute(
                sa.text('UPDATE exercise SET catalog_id = :catalog_id WHERE id = :id'),
                {'catalog_id': catalog_id, 'id': exercise_id},
            )
