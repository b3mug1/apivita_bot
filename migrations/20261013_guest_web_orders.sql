-- Allow guest website orders and retain their contact phone number.
ALTER TABLE orders ALTER COLUMN user_id DROP NOT NULL;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS guest_phone VARCHAR(32);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivery_type VARCHAR(128);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'orders' AND column_name = 'note'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'orders' AND column_name = 'comment'
    ) THEN
        ALTER TABLE orders RENAME COLUMN note TO comment;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'order_items' AND column_name = 'unit_price'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'order_items' AND column_name = 'price_per_unit'
    ) THEN
        ALTER TABLE order_items RENAME COLUMN unit_price TO price_per_unit;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'order_items' AND column_name = 'subtotal' AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE order_items ALTER COLUMN subtotal DROP NOT NULL;
    END IF;
END
$$;
