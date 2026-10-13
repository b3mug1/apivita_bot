-- Allow guest website orders and retain their contact phone number.
ALTER TABLE orders ALTER COLUMN user_id DROP NOT NULL;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS guest_phone VARCHAR(32);
