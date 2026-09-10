"""Add skill ownership and template provenance for restart rehydration

Revision ID: 002
Revises: 001
Create Date: 2026-09-09 00:00:00.000000

Adds nullable ``user_id`` (owner scope for per-user rehydration) and
``template`` (origin template name for audit/re-resolution) to
``hermes_skills``. Both nullable: pre-existing rows keep working and
NULL-owner rows never rehydrate (fail closed).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'hermes_skills',
        sa.Column('user_id', sa.Integer(), nullable=True),
    )
    op.create_index('ix_hermes_skills_user_id', 'hermes_skills', ['user_id'], unique=False)
    op.create_foreign_key(
        'fk_hermes_skills_user_id', 'hermes_skills', 'users',
        ['user_id'], ['id'], ondelete='CASCADE',
    )
    op.add_column(
        'hermes_skills',
        sa.Column('template', sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_constraint('fk_hermes_skills_user_id', 'hermes_skills', type_='foreignkey')
    op.drop_index('ix_hermes_skills_user_id', table_name='hermes_skills')
    op.drop_column('hermes_skills', 'template')
    op.drop_column('hermes_skills', 'user_id')
