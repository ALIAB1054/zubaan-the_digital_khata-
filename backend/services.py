"""
services.py
────────────
Business-logic helpers: name normalisation, fuzzy matching,
customer creation, balance lookups, and summary aggregations.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from rapidfuzz import fuzz

from supabase_client import supabase

# ────────────────────────────────────────────────────────────
# Name normalisation
# ────────────────────────────────────────────────────────────

def normalize_name(raw: str) -> str:
    """Trim, lowercase, collapse repeated whitespace."""
    return re.sub(r"\s+", " ", raw.strip().lower())


# ────────────────────────────────────────────────────────────
# Customer matching / creation
# ────────────────────────────────────────────────────────────

MATCH_THRESHOLD = 75  # minimum RapidFuzz score to accept a match


def find_or_create_customer(raw_name: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Given a raw customer name from the AI pipeline:
    1. If blank / None → return (None, None).
    2. Normalise and fuzzy-match against existing customers.
    3. Above threshold → return existing customer.
    4. Below threshold → create a new customer.

    Returns (customer_id, customer_name).
    """
    if not raw_name or raw_name.strip() == "":
        return None, None

    norm = normalize_name(raw_name)

    # Fetch all customers (fine for hackathon scale)
    resp = supabase.table("customers").select("id, name, normalized_name").execute()
    existing: List[Dict[str, Any]] = (resp.data if resp is not None else []) or []

    best_score = 0.0
    best_match: Optional[Dict[str, Any]] = None

    for cust in existing:
        score = fuzz.ratio(norm, cust["normalized_name"])
        if score > best_score:
            best_score = score
            best_match = cust

    if best_match and best_score >= MATCH_THRESHOLD:
        return best_match["id"], best_match["name"]

    # Create new customer
    new = (
        supabase.table("customers")
        .insert({"name": raw_name.strip(), "normalized_name": norm})
        .execute()
    )
    if new is None or not new.data:
        raise ValueError("Failed to create customer")
    row = new.data[0]
    return row["id"], row["name"]


# ────────────────────────────────────────────────────────────
# Transaction creation via RPC
# ────────────────────────────────────────────────────────────

def create_transaction(
    *,
    customer_id: Optional[str],
    customer_name_raw: Optional[str],
    item: Optional[str],
    quantity: Optional[str],
    amount: Decimal,
    currency: str,
    tx_type: str,
    language_detected: Optional[str],
    raw_transcript: Optional[str],
    audio_clip_url: Optional[str],
    client_transaction_id: Optional[UUID],
    occurred_at: Optional[datetime],
) -> Dict[str, Any]:
    """Call the create_zubaan_transaction RPC."""
    params = {
        "p_customer_id": customer_id,
        "p_customer_name_raw": customer_name_raw,
        "p_item": item,
        "p_quantity": quantity,
        "p_amount": float(amount),  # Supabase RPC expects JSON-serialisable
        "p_currency": currency,
        "p_type": tx_type,
        "p_language_detected": language_detected,
        "p_transcript_original": raw_transcript,
        "p_audio_clip_url": audio_clip_url,
        "p_client_transaction_id": str(client_transaction_id) if client_transaction_id else None,
        "p_occurred_at": occurred_at.isoformat() if occurred_at else None,
    }
    resp = supabase.rpc("create_zubaan_transaction", params).execute()
    return resp.data if resp is not None else {}


# ────────────────────────────────────────────────────────────
# Undo transaction via RPC
# ────────────────────────────────────────────────────────────

def undo_transaction(transaction_id: str) -> Dict[str, Any]:
    """Call the undo_zubaan_transaction RPC."""
    resp = supabase.rpc("undo_zubaan_transaction", {"p_transaction_id": transaction_id}).execute()
    return resp.data if resp is not None else {}


# ────────────────────────────────────────────────────────────
# Audio upload
# ────────────────────────────────────────────────────────────

def upload_audio(transaction_id: str, file_bytes: bytes, filename: str) -> str:
    """
    Upload audio to Supabase Storage and update the transaction row.
    Returns the public URL.
    """
    path = f"{transaction_id}/{filename}"

    # Upload to storage
    supabase.storage.from_("transaction-audio").upload(
        path,
        file_bytes,
        {"content-type": "audio/mpeg", "upsert": "true"},
    )

    # Build public URL
    public_url = supabase.storage.from_("transaction-audio").get_public_url(path)

    # Update the transaction row
    supabase.table("transactions").update(
        {"audio_clip_url": public_url}
    ).eq("id", transaction_id).execute()

    return public_url


# ────────────────────────────────────────────────────────────
# Balance lookup
# ────────────────────────────────────────────────────────────

def get_customer_balance(customer_id: str) -> Dict[str, Any]:
    """Return customer name + running balance."""
    cust = (
        supabase.table("customers")
        .select("id, name")
        .eq("id", customer_id)
        .single()
        .execute()
    )
    if cust is None or not cust.data:
        raise ValueError("Customer not found")
        
    bal = (
        supabase.table("balances")
        .select("running_balance")
        .eq("customer_id", customer_id)
        .maybe_single()
        .execute()
    )
    running = bal.data["running_balance"] if (bal is not None and bal.data) else 0
    return {
        "customer_id": cust.data["id"],
        "customer_name": cust.data["name"],
        "running_balance": running,
    }


# ────────────────────────────────────────────────────────────
# Customer list
# ────────────────────────────────────────────────────────────

def get_all_customers() -> List[Dict[str, Any]]:
    """Return all customers with their running balance."""
    custs = supabase.table("customers").select("id, name, normalized_name").execute()
    bals = supabase.table("balances").select("customer_id, running_balance").execute()

    bal_map = {b["customer_id"]: b["running_balance"] for b in ((bals.data if bals is not None else []) or [])}

    result = []
    for c in ((custs.data if custs is not None else []) or []):
        result.append({
            "id": c["id"],
            "name": c["name"],
            "normalized_name": c["normalized_name"],
            "running_balance": bal_map.get(c["id"], 0),
        })
    return result


# ────────────────────────────────────────────────────────────
# Transaction list
# ────────────────────────────────────────────────────────────

def get_transactions(
    customer_id: Optional[str] = None,
    include_deleted: bool = False,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Newest transactions first, with optional filters."""
    query = supabase.table("transactions").select("*")

    if customer_id:
        query = query.eq("customer_id", customer_id)
    if not include_deleted:
        query = query.eq("deleted", False)

    query = query.order("occurred_at", desc=True).limit(limit)
    resp = query.execute()
    return (resp.data if resp is not None else []) or []


# ────────────────────────────────────────────────────────────
# Duplicate check for sync
# ────────────────────────────────────────────────────────────

def find_existing_by_client_id(client_transaction_id: UUID) -> Optional[Dict[str, Any]]:
    """Return an existing transaction if a matching client_transaction_id is found."""
    resp = (
        supabase.table("transactions")
        .select("*")
        .eq("client_transaction_id", str(client_transaction_id))
        .maybe_single()
        .execute()
    )
    return resp.data if (resp is not None and resp.data) else None


# ────────────────────────────────────────────────────────────
# Summaries
# ────────────────────────────────────────────────────────────

def _total_outstanding() -> Decimal:
    """Sum of all running_balance values."""
    resp = supabase.table("balances").select("running_balance").execute()
    return sum(Decimal(str(r["running_balance"])) for r in ((resp.data if resp is not None else []) or []))


def today_summary() -> Dict[str, Any]:
    """Sales / credit / payment totals for today (UTC)."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    resp = (
        supabase.table("transactions")
        .select("amount, type")
        .eq("deleted", False)
        .gte("occurred_at", f"{today_str}T00:00:00+00:00")
        .lte("occurred_at", f"{today_str}T23:59:59+00:00")
        .execute()
    )
    rows = (resp.data if resp is not None else []) or []

    cash = Decimal(0)
    credit = Decimal(0)
    payment = Decimal(0)

    for r in rows:
        amt = Decimal(str(r["amount"]))
        if r["type"] == "cash_sale":
            cash += amt
        elif r["type"] == "credit_given":
            credit += amt
        elif r["type"] == "payment_received":
            payment += amt

    total_sales = cash + credit  # cash_sale + credit_given

    return {
        "today_sales_total": total_sales,
        "cash_sales_total": cash,
        "credit_given_total": credit,
        "payment_received_total": payment,
        "transaction_count": len(rows),
        "total_outstanding_balance": _total_outstanding(),
    }


def monthly_summary() -> Dict[str, Any]:
    """Aggregate for current + previous month."""
    now = datetime.now(timezone.utc)
    cur_year, cur_month = now.year, now.month

    if cur_month == 1:
        prev_year, prev_month = cur_year - 1, 12
    else:
        prev_year, prev_month = cur_year, cur_month - 1

    cur_start = f"{cur_year}-{cur_month:02d}-01T00:00:00+00:00"
    prev_start = f"{prev_year}-{prev_month:02d}-01T00:00:00+00:00"

    # Current month
    cur_resp = (
        supabase.table("transactions")
        .select("amount, type, item")
        .eq("deleted", False)
        .gte("occurred_at", cur_start)
        .execute()
    )
    cur_rows = (cur_resp.data if cur_resp is not None else []) or []

    # Previous month
    prev_resp = (
        supabase.table("transactions")
        .select("amount, type")
        .eq("deleted", False)
        .gte("occurred_at", prev_start)
        .lt("occurred_at", cur_start)
        .execute()
    )
    prev_rows = (prev_resp.data if prev_resp is not None else []) or []

    def _aggregate(rows: List[Dict[str, Any]]):
        cash = credit = payment = Decimal(0)
        for r in rows:
            amt = Decimal(str(r["amount"]))
            if r["type"] == "cash_sale":
                cash += amt
            elif r["type"] == "credit_given":
                credit += amt
            elif r["type"] == "payment_received":
                payment += amt
        return cash + credit, credit, payment, len(rows)

    c_sales, c_credit, c_pay, c_count = _aggregate(cur_rows)
    p_sales, p_credit, p_pay, p_count = _aggregate(prev_rows)

    # Fast-moving items: top 5 items by count this month
    item_counts: Dict[str, int] = {}
    for r in cur_rows:
        it = r.get("item")
        if it:
            item_counts[it] = item_counts.get(it, 0) + 1

    fast_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "current_month_sales_total": c_sales,
        "previous_month_sales_total": p_sales,
        "current_month_credit_given_total": c_credit,
        "previous_month_credit_given_total": p_credit,
        "current_month_payment_received_total": c_pay,
        "previous_month_payment_received_total": p_pay,
        "current_month_transaction_count": c_count,
        "previous_month_transaction_count": p_count,
        "total_outstanding_balance": _total_outstanding(),
        "fast_moving_items": [{"item": k, "count": v} for k, v in fast_items],
    }
