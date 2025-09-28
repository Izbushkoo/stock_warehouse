"""create triggers and initial data

Revision ID: create_triggers_and_data
Revises: 529d572a4609
Create Date: 2025-09-28 18:46:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision: str = 'create_triggers_and_data'
down_revision: Union[str, None] = '529d572a4609'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create triggers
    op.execute(text("""
    CREATE OR REPLACE FUNCTION update_stock_balance()
    RETURNS TRIGGER AS $$
    BEGIN
        -- Update stock balance after stock movement
        INSERT INTO stock_balance (
            warehouse_id, item_id, bin_location_id, lot_id,
            available_quantity, reserved_quantity, total_quantity,
            last_movement_at, created_at, updated_at
        )
        VALUES (
            NEW.warehouse_id, NEW.item_id, NEW.bin_location_id, NEW.lot_id,
            CASE WHEN NEW.movement_type IN ('inbound', 'adjustment_positive') THEN NEW.quantity_change ELSE 0 END,
            0,
            CASE WHEN NEW.movement_type IN ('inbound', 'adjustment_positive') THEN NEW.quantity_change ELSE 0 END,
            NEW.occurred_at, NOW(), NOW()
        )
        ON CONFLICT (warehouse_id, item_id, COALESCE(bin_location_id, 0), COALESCE(lot_id, 0))
        DO UPDATE SET
            available_quantity = stock_balance.available_quantity + 
                CASE WHEN NEW.movement_type IN ('inbound', 'adjustment_positive') THEN NEW.quantity_change
                     WHEN NEW.movement_type IN ('outbound', 'adjustment_negative') THEN -NEW.quantity_change
                     ELSE 0 END,
            total_quantity = stock_balance.total_quantity + 
                CASE WHEN NEW.movement_type IN ('inbound', 'adjustment_positive') THEN NEW.quantity_change
                     WHEN NEW.movement_type IN ('outbound', 'adjustment_negative') THEN -NEW.quantity_change
                     ELSE 0 END,
            last_movement_at = NEW.occurred_at,
            updated_at = NOW();
        
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """))
    
    op.execute(text("""
    CREATE TRIGGER trigger_update_stock_balance
        AFTER INSERT ON stock_movement
        FOR EACH ROW
        EXECUTE FUNCTION update_stock_balance();
    """))
    
    op.execute(text("""
    CREATE OR REPLACE FUNCTION validate_stock_movement()
    RETURNS TRIGGER AS $$
    BEGIN
        -- Validate outbound movements don't exceed available stock
        IF NEW.movement_type IN ('outbound', 'adjustment_negative') THEN
            IF (SELECT COALESCE(SUM(available_quantity), 0) 
                FROM stock_balance 
                WHERE warehouse_id = NEW.warehouse_id 
                AND item_id = NEW.item_id
                AND (NEW.bin_location_id IS NULL OR bin_location_id = NEW.bin_location_id)
                AND (NEW.lot_id IS NULL OR lot_id = NEW.lot_id)
            ) < NEW.quantity_change THEN
                RAISE EXCEPTION 'Insufficient stock for movement';
            END IF;
        END IF;
        
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """))
    
    op.execute(text("""
    CREATE TRIGGER trigger_validate_stock_movement
        BEFORE INSERT ON stock_movement
        FOR EACH ROW
        EXECUTE FUNCTION validate_stock_movement();
    """))
    
    op.execute(text("""
    CREATE OR REPLACE FUNCTION create_audit_log()
    RETURNS TRIGGER AS $$
    BEGIN
        INSERT INTO audit_log (
            entity_table_name, entity_primary_identifier, operation_type,
            changed_fields, old_values, new_values, changed_by_user_id, recorded_at
        )
        VALUES (
            TG_TABLE_NAME,
            COALESCE(
                CASE TG_TABLE_NAME 
                    WHEN 'app_user' THEN COALESCE(NEW.app_user_id::text, OLD.app_user_id::text)
                    WHEN 'warehouse' THEN COALESCE(NEW.warehouse_id::text, OLD.warehouse_id::text)
                    WHEN 'item' THEN COALESCE(NEW.item_id::text, OLD.item_id::text)
                    ELSE COALESCE(NEW.id::text, OLD.id::text)
                END
            ),
            TG_OP,
            '{}',
            CASE WHEN TG_OP = 'DELETE' THEN row_to_json(OLD) ELSE NULL END,
            CASE WHEN TG_OP != 'DELETE' THEN row_to_json(NEW) ELSE NULL END,
            NULL,
            NOW()
        );
        
        RETURN COALESCE(NEW, OLD);
    END;
    $$ LANGUAGE plpgsql;
    """))
    
    op.execute(text("""
    CREATE OR REPLACE FUNCTION create_sales_analytics()
    RETURNS TRIGGER AS $$
    BEGIN
        -- Create analytics record when sales order is completed
        IF NEW.order_status = 'completed' AND OLD.order_status != 'completed' THEN
            INSERT INTO sales_analytics (
                item_id, warehouse_id, marketplace_channel, sale_date,
                quantity_sold, unit_price, total_revenue, profit_margin,
                customer_segment, created_at, updated_at
            )
            SELECT 
                sol.item_id,
                NEW.warehouse_id,
                NEW.marketplace_channel,
                NEW.order_date::date,
                sol.quantity,
                sol.unit_price,
                sol.line_total,
                0.0, -- Calculate profit margin separately
                'standard',
                NOW(),
                NOW()
            FROM sales_order_line sol
            WHERE sol.sales_order_id = NEW.sales_order_id;
        END IF;
        
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """))
    
    op.execute(text("""
    CREATE TRIGGER trigger_create_sales_analytics
        AFTER UPDATE ON sales_order
        FOR EACH ROW
        EXECUTE FUNCTION create_sales_analytics();
    """))

    # Insert initial data
    op.execute(text("""
    INSERT INTO app_user (app_user_id, user_email, user_display_name, password_hash, is_active, created_at, updated_at)
    VALUES (
        gen_random_uuid(),
        'admin@example.com',
        'System Administrator',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3bp.Gm.F5e', -- 'change-me'
        true,
        NOW(),
        NOW()
    )
    ON CONFLICT (user_email) DO NOTHING;
    """))
    
    op.execute(text("""
    INSERT INTO warehouse (warehouse_id, warehouse_code, warehouse_name, warehouse_address, time_zone, is_active, created_at, updated_at)
    VALUES (
        gen_random_uuid(),
        'MAIN',
        'Main Warehouse',
        '123 Main St, City, Country',
        'UTC',
        true,
        NOW(),
        NOW()
    )
    ON CONFLICT (warehouse_code) DO NOTHING;
    """))


def downgrade() -> None:
    # Drop triggers
    op.execute(text("DROP TRIGGER IF EXISTS trigger_create_sales_analytics ON sales_order;"))
    op.execute(text("DROP TRIGGER IF EXISTS trigger_validate_stock_movement ON stock_movement;"))
    op.execute(text("DROP TRIGGER IF EXISTS trigger_update_stock_balance ON stock_movement;"))
    
    # Drop functions
    op.execute(text("DROP FUNCTION IF EXISTS create_sales_analytics();"))
    op.execute(text("DROP FUNCTION IF EXISTS create_audit_log();"))
    op.execute(text("DROP FUNCTION IF EXISTS validate_stock_movement();"))
    op.execute(text("DROP FUNCTION IF EXISTS update_stock_balance();"))