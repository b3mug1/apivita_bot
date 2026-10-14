-- =============================================================================
-- Apivita Bot — PostgreSQL schema initialisation
-- Run once against an empty database: psql -d apivita -f migrations/init.sql
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- ---------------------------------------------------------------------------
-- ENUM types
-- ---------------------------------------------------------------------------

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'order_status') THEN
        CREATE TYPE order_status AS ENUM (
            'new',
            'confirmed',
            'paid',
            'shipped',
            'delivered',
            'cancelled'
        );
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'container_type') THEN
        CREATE TYPE container_type AS ENUM (
            'plastic',
            'glass',
            'other'
        );
    END IF;
END
$$;


-- ---------------------------------------------------------------------------
-- TABLE: users
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS users (
    id            SERIAL          PRIMARY KEY,
    telegram_id   BIGINT          NOT NULL UNIQUE,
    username      VARCHAR(64),
    name          VARCHAR(255),
    phone         VARCHAR(20),                          -- NULL until registered
    city          VARCHAR(128),
    address       TEXT,
    is_blocked    BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users (telegram_id);


-- ---------------------------------------------------------------------------
-- TABLE: products
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS products (
    id             SERIAL          PRIMARY KEY,
    name           VARCHAR(255)    NOT NULL,
    category       VARCHAR(128)    NOT NULL DEFAULT 'honey',
    container_type container_type  NOT NULL DEFAULT 'plastic',
    weight_grams   INTEGER         NOT NULL,            -- e.g. 1000, 500, 300, 200, 150, 10
    price          INTEGER         NOT NULL,            -- tenge
    description    TEXT,
    photo_file_id  VARCHAR(512),                        -- Telegram file_id for product photo
    is_available   BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_category          ON products (category);
CREATE INDEX IF NOT EXISTS idx_products_container_type    ON products (container_type);
CREATE INDEX IF NOT EXISTS idx_products_is_available      ON products (is_available);


-- ---------------------------------------------------------------------------
-- TABLE: carts
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS carts (
    id          SERIAL      PRIMARY KEY,
    user_id     INTEGER     NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    product_id  INTEGER     NOT NULL REFERENCES products (id) ON DELETE CASCADE,
    quantity    INTEGER     NOT NULL DEFAULT 1 CHECK (quantity > 0),
    added_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_carts_user_id ON carts (user_id);


-- ---------------------------------------------------------------------------
-- TABLE: orders
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS orders (
    id          SERIAL          PRIMARY KEY,
    user_id     INTEGER         REFERENCES users (id) ON DELETE RESTRICT,
    status      order_status    NOT NULL DEFAULT 'new',
    total_price INTEGER         NOT NULL DEFAULT 0,     -- tenge
    guest_phone VARCHAR(32),
    delivery_type VARCHAR(128),
    city        VARCHAR(128)    NOT NULL,
    address     TEXT,
    comment     TEXT,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_user_id    ON orders (user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status     ON orders (status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders (created_at DESC);


-- ---------------------------------------------------------------------------
-- TABLE: order_items
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS order_items (
    id            SERIAL      PRIMARY KEY,
    order_id      INTEGER     NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
    product_id    INTEGER     REFERENCES products (id) ON DELETE SET NULL,
    product_name  VARCHAR(255) NOT NULL,               -- snapshot at order time
    price_per_unit INTEGER     NOT NULL,
    quantity      INTEGER      NOT NULL DEFAULT 1 CHECK (quantity > 0)
);

CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items (order_id);


-- ---------------------------------------------------------------------------
-- TABLE: analytics
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS analytics (
    id          BIGSERIAL       PRIMARY KEY,
    user_id     INTEGER         REFERENCES users (id) ON DELETE SET NULL,
    action      VARCHAR(128)    NOT NULL,
    data        JSONB           NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analytics_user_id    ON analytics (user_id);
CREATE INDEX IF NOT EXISTS idx_analytics_action     ON analytics (action);
CREATE INDEX IF NOT EXISTS idx_analytics_created_at ON analytics (created_at DESC);


-- ---------------------------------------------------------------------------
-- Trigger: auto-update updated_at on users and orders
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_users_updated_at  ON users;
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_orders_updated_at ON orders;
CREATE TRIGGER trg_orders_updated_at
    BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- =============================================================================
-- SEED DATA: Products
-- =============================================================================

-- ---------------------------------------------------------------------------
-- PLASTIC containers (тара пластик)
-- ---------------------------------------------------------------------------

-- Мёд подсолнуховый / plastic
INSERT INTO products (name, category, container_type, weight_grams, price) VALUES
    ('Мёд подсолнуховый', 'honey', 'plastic', 1000, 3500),
    ('Мёд подсолнуховый', 'honey', 'plastic',  500, 1900),
    ('Мёд подсолнуховый', 'honey', 'plastic',  200,  900)
ON CONFLICT DO NOTHING;

-- Мёд гречишный / plastic
INSERT INTO products (name, category, container_type, weight_grams, price) VALUES
    ('Мёд гречишный', 'honey', 'plastic', 1000, 3500),
    ('Мёд гречишный', 'honey', 'plastic',  500, 1900),
    ('Мёд гречишный', 'honey', 'plastic',  200,  900)
ON CONFLICT DO NOTHING;

-- Мёд жантачный / plastic
INSERT INTO products (name, category, container_type, weight_grams, price) VALUES
    ('Мёд жантачный', 'honey', 'plastic', 1000, 3500),
    ('Мёд жантачный', 'honey', 'plastic',  500, 1900),
    ('Мёд жантачный', 'honey', 'plastic',  200,  900)
ON CONFLICT DO NOTHING;

-- Мёд степной / plastic
INSERT INTO products (name, category, container_type, weight_grams, price) VALUES
    ('Мёд степной', 'honey', 'plastic', 1000, 3500),
    ('Мёд степной', 'honey', 'plastic',  500, 1900),
    ('Мёд степной', 'honey', 'plastic',  200,  900)
ON CONFLICT DO NOTHING;

-- Мёд горный / plastic
INSERT INTO products (name, category, container_type, weight_grams, price) VALUES
    ('Мёд горный', 'honey', 'plastic', 1000, 3500),
    ('Мёд горный', 'honey', 'plastic',  500, 1900),
    ('Мёд горный', 'honey', 'plastic',  200,  900)
ON CONFLICT DO NOTHING;

-- Мёд разнотравье / plastic
INSERT INTO products (name, category, container_type, weight_grams, price) VALUES
    ('Мёд разнотравье', 'honey', 'plastic', 1000, 3500),
    ('Мёд разнотравье', 'honey', 'plastic',  500, 1900),
    ('Мёд разнотравье', 'honey', 'plastic',  200,  900)
ON CONFLICT DO NOTHING;

-- Мёд акациевый / plastic
INSERT INTO products (name, category, container_type, weight_grams, price) VALUES
    ('Мёд акациевый', 'honey', 'plastic', 1000, 5500),
    ('Мёд акациевый', 'honey', 'plastic',  500, 3000),
    ('Мёд акациевый', 'honey', 'plastic',  200, 1400)
ON CONFLICT DO NOTHING;

-- Мёд липовый / plastic
INSERT INTO products (name, category, container_type, weight_grams, price) VALUES
    ('Мёд липовый', 'honey', 'plastic', 1000, 5500),
    ('Мёд липовый', 'honey', 'plastic',  500, 3000),
    ('Мёд липовый', 'honey', 'plastic',  200, 1400)
ON CONFLICT DO NOTHING;


-- ---------------------------------------------------------------------------
-- GLASS containers (стекло)
-- ---------------------------------------------------------------------------

-- Мёд подсолнуховый / glass
INSERT INTO products (name, category, container_type, weight_grams, price) VALUES
    ('Мёд подсолнуховый', 'honey', 'glass', 1000, 4000),
    ('Мёд подсолнуховый', 'honey', 'glass',  500, 2200),
    ('Мёд подсолнуховый', 'honey', 'glass',  300, 1300),
    ('Мёд подсолнуховый', 'honey', 'glass',  150,  900)
ON CONFLICT DO NOTHING;

-- Мёд гречишный / glass
INSERT INTO products (name, category, container_type, weight_grams, price) VALUES
    ('Мёд гречишный', 'honey', 'glass', 1000, 4000),
    ('Мёд гречишный', 'honey', 'glass',  500, 2200),
    ('Мёд гречишный', 'honey', 'glass',  300, 1300),
    ('Мёд гречишный', 'honey', 'glass',  150,  900)
ON CONFLICT DO NOTHING;

-- Мёд жантачный / glass
INSERT INTO products (name, category, container_type, weight_grams, price) VALUES
    ('Мёд жантачный', 'honey', 'glass', 1000, 4000),
    ('Мёд жантачный', 'honey', 'glass',  500, 2200),
    ('Мёд жантачный', 'honey', 'glass',  300, 1300),
    ('Мёд жантачный', 'honey', 'glass',  150,  900)
ON CONFLICT DO NOTHING;

-- Мёд степной / glass
INSERT INTO products (name, category, container_type, weight_grams, price) VALUES
    ('Мёд степной', 'honey', 'glass', 1000, 4000),
    ('Мёд степной', 'honey', 'glass',  500, 2200),
    ('Мёд степной', 'honey', 'glass',  300, 1300),
    ('Мёд степной', 'honey', 'glass',  150,  900)
ON CONFLICT DO NOTHING;

-- Мёд горный / glass
INSERT INTO products (name, category, container_type, weight_grams, price) VALUES
    ('Мёд горный', 'honey', 'glass', 1000, 4000),
    ('Мёд горный', 'honey', 'glass',  500, 2200),
    ('Мёд горный', 'honey', 'glass',  300, 1300),
    ('Мёд горный', 'honey', 'glass',  150,  900)
ON CONFLICT DO NOTHING;

-- Мёд разнотравье / glass
INSERT INTO products (name, category, container_type, weight_grams, price) VALUES
    ('Мёд разнотравье', 'honey', 'glass', 1000, 4000),
    ('Мёд разнотравье', 'honey', 'glass',  500, 2200),
    ('Мёд разнотравье', 'honey', 'glass',  300, 1300),
    ('Мёд разнотравье', 'honey', 'glass',  150,  900)
ON CONFLICT DO NOTHING;

-- Мёд акациевый / glass
INSERT INTO products (name, category, container_type, weight_grams, price) VALUES
    ('Мёд акациевый', 'honey', 'glass', 1000, 6000),
    ('Мёд акациевый', 'honey', 'glass',  500, 3300),
    ('Мёд акациевый', 'honey', 'glass',  300, 2000),
    ('Мёд акациевый', 'honey', 'glass',  150, 1400)
ON CONFLICT DO NOTHING;

-- Мёд липовый / glass
INSERT INTO products (name, category, container_type, weight_grams, price) VALUES
    ('Мёд липовый', 'honey', 'glass', 1000, 6000),
    ('Мёд липовый', 'honey', 'glass',  500, 3300),
    ('Мёд липовый', 'honey', 'glass',  300, 2000),
    ('Мёд липовый', 'honey', 'glass',  150, 1400)
ON CONFLICT DO NOTHING;


-- ---------------------------------------------------------------------------
-- OTHER products
-- ---------------------------------------------------------------------------

-- Перга (bee bread) — 1 кг, 25 000 тг
INSERT INTO products (name, category, container_type, weight_grams, price, description) VALUES
    ('Перга', 'other', 'other', 1000, 25000, 'Пчелиная перга — уникальный природный продукт.')
ON CONFLICT DO NOTHING;

-- Пыльца (pollen) — 1 кг, 10 000 тг
INSERT INTO products (name, category, container_type, weight_grams, price, description) VALUES
    ('Пыльца', 'other', 'other', 1000, 10000, 'Цветочная пыльца, собранная пчёлами.')
ON CONFLICT DO NOTHING;

-- Прополис — 10 г, 1 000 тг
INSERT INTO products (name, category, container_type, weight_grams, price, description) VALUES
    ('Прополис', 'other', 'other', 10, 1000, 'Натуральный пчелиный прополис 10 г.')
ON CONFLICT DO NOTHING;

-- Сотовый мёд — 1.7–2 кг, 10 000 тг (stored as 1850 g average)
INSERT INTO products (name, category, container_type, weight_grams, price, description) VALUES
    ('Сотовый мёд', 'honey', 'other', 1850, 10000, 'Сотовый мёд в рамке, 1.7–2 кг.')
ON CONFLICT DO NOTHING;


-- =============================================================================
-- End of init.sql
-- =============================================================================
