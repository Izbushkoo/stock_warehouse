"""add_item_group_description_and_is_active

Revision ID: f1a2b3c4d5e6
Revises: 43e2d1e8c21f
Create Date: 2025-09-28 23:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = '43e2d1e8c21f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add item_group_description field to item_group table
    op.add_column('item_group', sa.Column('item_group_description', sa.String(), nullable=True))
    
    # Add is_active field to item_group table
    op.add_column('item_group', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))


def downgrade() -> None:
    # Drop columns
    op.drop_column('item_group', 'is_active')
    op.drop_column('item_group', 'item_group_description')