-- =============================================================
-- Zubaan – Digital Khata  •  Supabase Schema
-- Paste this entire file into the Supabase SQL Editor and run.
-- =============================================================

-- Enable the uuid-ossp extension (usually already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---------------------------------------------------------
-- 1. CUSTOMERS
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS customers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL,
    normalized_name TEXT NOT NULL UNIQUE,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- ---------------------------------------------------------
-- 2. TRANSACTIONS
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id           UUID REFERENCES customers(id),
    customer_name_raw     TEXT,
    item                  TEXT,
    quantity              TEXT,
    amount                NUMERIC NOT NULL,
    currency              TEXT DEFAULT 'PKR',
    type                  TEXT NOT NULL CHECK (type IN ('credit_given', 'payment_received', 'cash_sale')),
    language_detected     TEXT,
    transcript_original   TEXT,
    audio_clip_url        TEXT,
    client_transaction_id UUID UNIQUE,
    occurred_at           TIMESTAMPTZ DEFAULT now(),
    created_at            TIMESTAMPTZ DEFAULT now(),
    flagged_disputed      BOOLEAN DEFAULT FALSE,
    deleted               BOOLEAN DEFAULT FALSE,
    deleted_at            TIMESTAMPTZ
);

-- Index for fast lookups by customer
CREATE INDEX IF NOT EXISTS idx_transactions_customer_id ON transactions(customer_id);

-- Index for duplicate-check during sync
CREATE INDEX IF NOT EXISTS idx_transactions_client_tx_id ON transactions(client_transaction_id)
    WHERE client_transaction_id IS NOT NULL;

-- ---------------------------------------------------------
-- 3. BALANCES
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS balances (
    customer_id     UUID PRIMARY KEY REFERENCES customers(id),
    running_balance NUMERIC DEFAULT 0,
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- =========================================================
-- ROW LEVEL SECURITY  (demo-only – wide-open for hackathon)
-- =========================================================

-- -- DEMO ONLY: allow all operations for authenticated AND anonymous users.
-- -- Replace these with proper per-user policies before production.

ALTER TABLE customers     ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions  ENABLE ROW LEVEL SECURITY;
ALTER TABLE balances      ENABLE ROW LEVEL SECURITY;

-- customers --
CREATE POLICY "demo_customers_select" ON customers FOR SELECT USING (true);  -- DEMO ONLY
CREATE POLICY "demo_customers_insert" ON customers FOR INSERT WITH CHECK (true);  -- DEMO ONLY
CREATE POLICY "demo_customers_update" ON customers FOR UPDATE USING (true);  -- DEMO ONLY
CREATE POLICY "demo_customers_delete" ON customers FOR DELETE USING (true);  -- DEMO ONLY

-- transactions --
CREATE POLICY "demo_transactions_select" ON transactions FOR SELECT USING (true);  -- DEMO ONLY
CREATE POLICY "demo_transactions_insert" ON transactions FOR INSERT WITH CHECK (true);  -- DEMO ONLY
CREATE POLICY "demo_transactions_update" ON transactions FOR UPDATE USING (true);  -- DEMO ONLY
CREATE POLICY "demo_transactions_delete" ON transactions FOR DELETE USING (true);  -- DEMO ONLY

-- balances --
CREATE POLICY "demo_balances_select" ON balances FOR SELECT USING (true);  -- DEMO ONLY
CREATE POLICY "demo_balances_insert" ON balances FOR INSERT WITH CHECK (true);  -- DEMO ONLY
CREATE POLICY "demo_balances_update" ON balances FOR UPDATE USING (true);  -- DEMO ONLY
CREATE POLICY "demo_balances_delete" ON balances FOR DELETE USING (true);  -- DEMO ONLY


-- =========================================================
-- STORAGE BUCKET  (run once – idempotent)
-- =========================================================

-- Create the bucket for audio clips.
-- In Supabase dashboard: Storage → New Bucket → name: transaction-audio, Public: ON
-- If you prefer SQL:
INSERT INTO storage.buckets (id, name, public)
VALUES ('transaction-audio', 'transaction-audio', true)
ON CONFLICT (id) DO NOTHING;

-- DEMO ONLY: allow anyone to upload / read audio files
CREATE POLICY "demo_audio_upload" ON storage.objects
    FOR INSERT WITH CHECK (bucket_id = 'transaction-audio');  -- DEMO ONLY

CREATE POLICY "demo_audio_read" ON storage.objects
    FOR SELECT USING (bucket_id = 'transaction-audio');  -- DEMO ONLY


-- =========================================================
-- RPC: create_zubaan_transaction
-- Atomically: insert transaction → upsert balance → return row
-- =========================================================

CREATE OR REPLACE FUNCTION create_zubaan_transaction(
    p_customer_id           UUID,
    p_customer_name_raw     TEXT,
    p_item                  TEXT,
    p_quantity              TEXT,
    p_amount                NUMERIC,
    p_currency              TEXT,
    p_type                  TEXT,
    p_language_detected     TEXT,
    p_transcript_original   TEXT,
    p_audio_clip_url        TEXT,
    p_client_transaction_id UUID,
    p_occurred_at           TIMESTAMPTZ
)
RETURNS JSON
LANGUAGE plpgsql
AS $$
DECLARE
    v_tx       transactions%ROWTYPE;
    v_balance  NUMERIC := 0;
    v_delta    NUMERIC := 0;
BEGIN
    -- 1. Insert the transaction
    INSERT INTO transactions (
        customer_id, customer_name_raw, item, quantity,
        amount, currency, type, language_detected,
        transcript_original, audio_clip_url,
        client_transaction_id, occurred_at
    ) VALUES (
        p_customer_id, p_customer_name_raw, p_item, p_quantity,
        p_amount, p_currency, p_type, p_language_detected,
        p_transcript_original, p_audio_clip_url,
        p_client_transaction_id, COALESCE(p_occurred_at, now())
    )
    RETURNING * INTO v_tx;

    -- 2-3. Update balance only when there is a customer
    IF p_customer_id IS NOT NULL AND p_type != 'cash_sale' THEN
        -- Compute delta
        IF p_type = 'credit_given' THEN
            v_delta := p_amount;
        ELSIF p_type = 'payment_received' THEN
            v_delta := -1 * p_amount;
        END IF;

        -- Upsert balance row
        INSERT INTO balances (customer_id, running_balance, updated_at)
        VALUES (p_customer_id, v_delta, now())
        ON CONFLICT (customer_id) DO UPDATE
            SET running_balance = balances.running_balance + v_delta,
                updated_at      = now();

        -- Read current balance
        SELECT running_balance INTO v_balance
        FROM balances
        WHERE customer_id = p_customer_id;
    END IF;

    -- 4. Return transaction + balance
    RETURN json_build_object(
        'transaction', row_to_json(v_tx),
        'running_balance', v_balance
    );
END;
$$;


-- =========================================================
-- RPC: undo_zubaan_transaction
-- Atomically: validate → soft-delete → reverse balance
-- No time restriction – undo is allowed at any time.
-- =========================================================

CREATE OR REPLACE FUNCTION undo_zubaan_transaction(
    p_transaction_id UUID
)
RETURNS JSON
LANGUAGE plpgsql
AS $$
DECLARE
    v_tx       transactions%ROWTYPE;
    v_delta    NUMERIC := 0;
    v_balance  NUMERIC := 0;
BEGIN
    -- 1. Fetch the transaction (lock the row)
    SELECT * INTO v_tx
    FROM transactions
    WHERE id = p_transaction_id
    FOR UPDATE;

    -- 2. Return error if not found
    IF NOT FOUND THEN
        RAISE EXCEPTION 'UNDO_NOT_FOUND: Transaction % not found', p_transaction_id;
    END IF;

    -- 3. Return error if already deleted
    IF v_tx.deleted THEN
        RAISE EXCEPTION 'UNDO_ALREADY_DELETED: Transaction % is already deleted', p_transaction_id;
    END IF;

    -- 4-5. Soft-delete (preserve original row data, transcript, audio_clip_url)
    UPDATE transactions
    SET deleted    = TRUE,
        deleted_at = now()
    WHERE id = p_transaction_id;

    -- 6. Reverse balance effect
    IF v_tx.customer_id IS NOT NULL AND v_tx.type != 'cash_sale' THEN
        -- credit_given reversal → decrease balance
        -- payment_received reversal → increase balance
        IF v_tx.type = 'credit_given' THEN
            v_delta := -1 * v_tx.amount;
        ELSIF v_tx.type = 'payment_received' THEN
            v_delta := v_tx.amount;
        END IF;

        UPDATE balances
        SET running_balance = running_balance + v_delta,
            updated_at      = now()
        WHERE customer_id = v_tx.customer_id;

        SELECT running_balance INTO v_balance
        FROM balances
        WHERE customer_id = v_tx.customer_id;
    END IF;

    -- 7. Return the undone transaction and updated balance
    RETURN json_build_object(
        'transaction', row_to_json(v_tx),
        'transaction_id', p_transaction_id,
        'deleted', TRUE,
        'running_balance', v_balance
    );
END;
$$;
