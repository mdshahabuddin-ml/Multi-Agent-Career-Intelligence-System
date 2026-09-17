"""Add is_admin flag to users for admin route authorization

Revision ID: 004
Revises: 003
Create Date: 2026-09-17 00:00:00.000000

Adds non-nullable ``is_admin`` (default False) to ``users`` so admin
endpoints can enforce authorization instead of allowing any
authenticated user. Existing rows default to non-admin (fail closed).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column('users', 'is_admin')
