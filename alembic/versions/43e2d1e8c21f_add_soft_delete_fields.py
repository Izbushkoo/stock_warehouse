"""add_soft_delete_fields

Revision ID: 43e2d1e8c21f
Revises: 529d572a4609
Create Date: 2025-09-28 23:13:21.927687

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlmodel import SQLModel
import sqlmodel


# revision identifiers, used by Alembic.
revision = '43e2d1e8c21f'
down_revision = '529d572a4609'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add soft delete fields to warehouse table
    op.add_column('warehouse', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('warehouse', sa.Column('deleted_by', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_warehouse_deleted_by', 'warehouse', 'app_user', ['deleted_by'], ['app_user_id'])
    
    # Add soft delete fields to item_group table
    op.add_column('item_group', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('item_group', sa.Column('deleted_by', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_item_group_deleted_by', 'item_group', 'app_user', ['deleted_by'], ['app_user_id'])
    
    # Add created_by and soft delete fields to item table
    op.add_column('item', sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('item', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('item', sa.Column('deleted_by', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_item_created_by', 'item', 'app_user', ['created_by'], ['app_user_id'])
    op.create_foreign_key('fk_item_deleted_by', 'item', 'app_user', ['deleted_by'], ['app_user_id'])
    
    # Add soft delete fields to sales_order table
    op.add_column('sales_order', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('sales_order', sa.Column('deleted_by', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_sales_order_deleted_by', 'sales_order', 'app_user', ['deleted_by'], ['app_user_id'])
    
    # Add soft delete fields to return_order table
    op.add_column('return_order', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('return_order', sa.Column('deleted_by', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_return_order_deleted_by', 'return_order', 'app_user', ['deleted_by'], ['app_user_id'])
    
    # Create index for soft delete queries
    op.create_index('ix_warehouse_deleted_at', 'warehouse', ['deleted_at'])
    op.create_index('ix_item_group_deleted_at', 'item_group', ['deleted_at'])
    op.create_index('ix_item_deleted_at', 'item', ['deleted_at'])
    op.create_index('ix_sales_order_deleted_at', 'sales_order', ['deleted_at'])
    op.create_index('ix_return_order_deleted_at', 'return_order', ['deleted_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_return_order_deleted_at', table_name='return_order')
    op.drop_index('ix_sales_order_deleted_at', table_name='sales_order')
    op.drop_index('ix_item_deleted_at', table_name='item')
    op.drop_index('ix_item_group_deleted_at', table_name='item_group')
    op.drop_index('ix_warehouse_deleted_at', table_name='warehouse')
    
    # Drop foreign keys
    op.drop_constraint('fk_return_order_deleted_by', 'return_order', type_='foreignkey')
    op.drop_constraint('fk_sales_order_deleted_by', 'sales_order', type_='foreignkey')
    op.drop_constraint('fk_item_deleted_by', 'item', type_='foreignkey')
    op.drop_constraint('fk_item_created_by', 'item', type_='foreignkey')
    op.drop_constraint('fk_item_group_deleted_by', 'item_group', type_='foreignkey')
    op.drop_constraint('fk_warehouse_deleted_by', 'warehouse', type_='foreignkey')
    
    # Drop columns
    op.drop_column('return_order', 'deleted_by')
    op.drop_column('return_order', 'deleted_at')
    op.drop_column('sales_order', 'deleted_by')
    op.drop_column('sales_order', 'deleted_at')
    op.drop_column('item', 'deleted_by')
    op.drop_column('item', 'deleted_at')
    op.drop_column('item', 'created_by')
    op.drop_column('item_group', 'deleted_by')
    op.drop_column('item_group', 'deleted_at')
    op.drop_column('warehouse', 'deleted_by')
    op.drop_column('warehouse', 'deleted_at')
