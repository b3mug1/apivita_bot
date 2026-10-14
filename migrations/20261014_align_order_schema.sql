-- Align databases created before guest checkout with the current ORM models.
ALTER TABLE products ADD COLUMN IF NOT EXISTS description TEXT;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'orders'
          AND column_name = 'status'
          AND udt_name = 'orderstatus'
    ) THEN
        ALTER TABLE orders
            ALTER COLUMN status TYPE order_status
            USING status::text::order_status;
    END IF;
END
$$;
