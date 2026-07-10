# Zubaan – Digital Khata Backend

> Voice-first digital ledger for Pakistani shopkeepers.  
> This is the **Person 2** backend: FastAPI + Supabase Postgres + Supabase Storage.

---

## 1 · Supabase Project Setup

1. Go to [supabase.com](https://supabase.com) → **New Project**.
2. Pick a name, set a database password, choose a region close to Pakistan (e.g. Mumbai).
3. Once the project is created, grab these from **Settings → API**:
   - `Project URL` → `SUPABASE_URL`
   - `service_role` key (under **Project API keys**) → `SUPABASE_SERVICE_ROLE_KEY`

> ⚠️ The **service_role** key bypasses RLS – never expose it in frontend code.

---

## 2 · Run the SQL Schema

1. Open the Supabase dashboard → **SQL Editor**.
2. Click **New Query**.
3. Paste the **entire** contents of [`supabase_schema.sql`](./supabase_schema.sql).
4. Click **Run**.

This creates:

| Object | What it does |
|---|---|
| `customers` table | Stores customer names with normalized variants |
| `transactions` table | Every sale / credit / payment |
| `balances` table | Per-customer running balance |
| RLS policies | Demo-only open policies (replace before production) |
| `transaction-audio` bucket | Supabase Storage bucket for audio clips |
| `create_zubaan_transaction` | Atomic RPC: insert tx + upsert balance |
| `undo_zubaan_transaction` | Atomic RPC: soft-delete tx + reverse balance |

---

## 3 · Create the Storage Bucket

The SQL schema already creates the `transaction-audio` bucket.  
If it doesn't appear, create it manually:

1. Supabase dashboard → **Storage**.
2. **New Bucket** → Name: `transaction-audio` → Public: **ON**.

---

## 4 · Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```dotenv
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
```

---

## 5 · Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

> Use a virtual environment (`python -m venv venv` → `venv\Scripts\activate` on Windows).

---

## 6 · Run the API

```bash
uvicorn main:app --reload --port 8001
```

Open [http://localhost:8001/docs](http://localhost:8001/docs) for the interactive Swagger UI.

---

## 7 · Curl Examples

### Health Check

```bash
curl http://localhost:8001/health
```

### Create a Transaction

```bash
curl -X POST http://localhost:8001/transaction \
  -H "Content-Type: application/json" \
  -d '{
    "customer": "Ahmed",
    "item": "sugar",
    "quantity": "2 kg",
    "amount": 50,
    "currency": "PKR",
    "type": "credit_given",
    "language_detected": "ur",
    "raw_transcript": "احمد کو دو کلو چینی پچاس روپے ادھار دی"
  }'
```

### Upload Audio for a Transaction

```bash
curl -X POST http://localhost:8001/transaction/audio \
  -F "transaction_id=<TRANSACTION_UUID>" \
  -F "file=@recording.webm"
```

### Check Customer Balance

```bash
curl http://localhost:8001/customer/<CUSTOMER_UUID>/balance
```

### List All Customers

```bash
curl http://localhost:8001/customers
```

### List Transactions

```bash
# Latest 50 (default)
curl http://localhost:8001/transactions

# For a specific customer, including deleted
curl "http://localhost:8001/transactions?customer_id=<UUID>&include_deleted=true&limit=20"
```

### Undo a Transaction

```bash
curl -X POST http://localhost:8001/transaction/<TRANSACTION_UUID>/undo
```

### Today's Summary

```bash
curl http://localhost:8001/summary/today
```

### Monthly Summary

```bash
curl http://localhost:8001/summary/monthly
```

### Sync Offline Queue

```bash
curl -X POST http://localhost:8001/sync \
  -H "Content-Type: application/json" \
  -d '{
    "transactions": [
      {
        "customer": "Bilal",
        "item": "flour",
        "quantity": "5 kg",
        "amount": 120,
        "type": "credit_given",
        "client_transaction_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "occurred_at": "2025-07-09T10:30:00+05:00"
      },
      {
        "customer": "Bilal",
        "amount": 100,
        "type": "payment_received",
        "client_transaction_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "occurred_at": "2025-07-09T11:00:00+05:00"
      }
    ]
  }'
```

---

## Folder Structure

```
backend/
├── main.py               ← FastAPI app & routes
├── supabase_client.py    ← Supabase client init
├── schemas.py            ← Pydantic request / response models
├── services.py           ← Business logic (fuzzy match, RPC calls, summaries)
├── supabase_schema.sql   ← SQL to paste in Supabase SQL Editor
├── requirements.txt      ← Python dependencies
├── .env.example          ← Template for environment variables
└── README.md             ← This file
```

---

## Tech Stack

| Layer | Tool |
|---|---|
| API framework | FastAPI |
| Database | Supabase Postgres |
| File storage | Supabase Storage |
| Python DB client | supabase-py |
| Validation | Pydantic |
| Fuzzy matching | RapidFuzz |
| Server | Uvicorn |

---

## Notes for Hackathon

- **RLS policies are demo-only** – they allow all access. Replace with per-user policies before shipping.
- The `undo` endpoint has **no time restriction** – transactions can be undone at any time.
- The `service_role` key is used server-side only. The frontend should use the `anon` key for its own Supabase client.
- All money values use `NUMERIC` / `Decimal` – never floats.
