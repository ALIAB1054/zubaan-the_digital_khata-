"""
main.py
───────
FastAPI application for Zubaan – the Digital Khata backend.
Run with:  uvicorn main:app --reload --port 8001
"""

from __future__ import annotations

from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

import services
from schemas import (
    AudioUploadOut,
    BalanceOut,
    CustomerWithBalance,
    HealthResponse,
    MonthlySummary,
    SyncItem,
    SyncRequest,
    SyncResponse,
    SyncResultItem,
    TodaySummary,
    TransactionIn,
    TransactionOut,
    UndoOut,
)

# ── App ──────────────────────────────────────────────────────

app = FastAPI(
    title="Zubaan API",
    description="Voice-first digital ledger backend for Pakistani shopkeepers.",
    version="0.1.0",
)

# CORS – allow localhost frontends during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ───────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse()


# ── Create Transaction ───────────────────────────────────────

@app.post("/transaction", response_model=TransactionOut)
def create_transaction(payload: TransactionIn):
    """
    Receive a confirmed transaction from the frontend.
    Find / create customer, then atomically insert via RPC.
    """
    # Customer matching
    customer_id, customer_name = services.find_or_create_customer(payload.customer)

    # Call RPC
    result = services.create_transaction(
        customer_id=customer_id,
        customer_name_raw=payload.customer,
        item=payload.item,
        quantity=payload.quantity,
        amount=payload.amount,
        currency=payload.currency,
        tx_type=payload.type,
        language_detected=payload.language_detected,
        raw_transcript=payload.raw_transcript,
        audio_clip_url=payload.audio_clip_url,
        client_transaction_id=payload.client_transaction_id,
        occurred_at=payload.occurred_at,
    )

    tx = result.get("transaction", {}) if isinstance(result, dict) else {}
    balance = result.get("running_balance", 0) if isinstance(result, dict) else 0

    return TransactionOut(
        success=True,
        transaction=tx,
        customer_id=customer_id,
        customer_name=customer_name,
        running_balance=Decimal(str(balance)),
    )


# ── Upload Audio ─────────────────────────────────────────────

@app.post("/transaction/audio", response_model=AudioUploadOut)
async def upload_audio(
    transaction_id: str = Form(...),
    file: UploadFile = File(...),
):
    """Upload an audio clip and attach it to a transaction."""
    file_bytes = await file.read()
    filename = file.filename or "audio.webm"

    try:
        url = services.upload_audio(transaction_id, file_bytes, filename)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return AudioUploadOut(
        success=True,
        audio_url=url,
        transaction_id=transaction_id,
    )


# ── Customer Balance ─────────────────────────────────────────

@app.get("/customer/{customer_id}/balance", response_model=BalanceOut)
def customer_balance(customer_id: str):
    try:
        data = services.get_customer_balance(customer_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return BalanceOut(**data)


# ── All Customers ────────────────────────────────────────────

@app.get("/customers", response_model=List[CustomerWithBalance])
def list_customers():
    return services.get_all_customers()


# ── Transaction List ─────────────────────────────────────────

@app.get("/transactions")
def list_transactions(
    customer_id: Optional[str] = Query(None),
    include_deleted: bool = Query(False),
    limit: int = Query(50, ge=1, le=500),
):
    return services.get_transactions(
        customer_id=customer_id,
        include_deleted=include_deleted,
        limit=limit,
    )


# ── Undo Transaction ────────────────────────────────────────

@app.post("/transaction/{transaction_id}/undo", response_model=UndoOut)
def undo_transaction(transaction_id: str):
    """
    Soft-delete a transaction and reverse its balance effect.
    No time restriction – undo is allowed at any time.
    """
    try:
        result = services.undo_transaction(transaction_id)
    except Exception as exc:
        err = str(exc)
        if "UNDO_NOT_FOUND" in err:
            raise HTTPException(status_code=404, detail=err)
        if "UNDO_ALREADY_DELETED" in err:
            raise HTTPException(status_code=400, detail=err)
        raise HTTPException(status_code=400, detail=err)

    tx = result.get("transaction", {}) if isinstance(result, dict) else {}

    return UndoOut(
        success=True,
        transaction=tx,
        transaction_id=result.get("transaction_id", transaction_id),
        deleted=result.get("deleted", True),
        running_balance=Decimal(str(result.get("running_balance", 0))),
    )


# ── Today Summary ────────────────────────────────────────────

@app.get("/summary/today", response_model=TodaySummary)
def summary_today():
    return services.today_summary()


# ── Monthly Summary ──────────────────────────────────────────

@app.get("/summary/monthly", response_model=MonthlySummary)
def summary_monthly():
    return services.monthly_summary()


# ── Sync Offline Queue ───────────────────────────────────────

@app.post("/sync", response_model=SyncResponse)
def sync_offline(payload: SyncRequest):
    """
    Accept an array of offline-queued transactions.
    • Sort by occurred_at before processing.
    • Skip duplicates by client_transaction_id.
    • Process each independently – one failure doesn't block the rest.
    """
    items: List[SyncItem] = sorted(
        payload.transactions,
        key=lambda t: t.occurred_at or "1970-01-01T00:00:00+00:00",
    )

    results: List[SyncResultItem] = []

    for item in items:
        cid = str(item.client_transaction_id) if item.client_transaction_id else None
        try:
            # Duplicate check
            if item.client_transaction_id:
                existing = services.find_existing_by_client_id(item.client_transaction_id)
                if existing:
                    results.append(
                        SyncResultItem(
                            client_transaction_id=cid,
                            success=True,
                            duplicate=True,
                            transaction_id=existing["id"],
                            error=None,
                        )
                    )
                    continue

            # Find / create customer
            customer_id, _name = services.find_or_create_customer(item.customer)

            # Create transaction
            result = services.create_transaction(
                customer_id=customer_id,
                customer_name_raw=item.customer,
                item=item.item,
                quantity=item.quantity,
                amount=item.amount,
                currency=item.currency,
                tx_type=item.type,
                language_detected=item.language_detected,
                raw_transcript=item.raw_transcript,
                audio_clip_url=item.audio_clip_url,
                client_transaction_id=item.client_transaction_id,
                occurred_at=item.occurred_at,
            )

            tx = result.get("transaction", {}) if isinstance(result, dict) else {}
            results.append(
                SyncResultItem(
                    client_transaction_id=cid,
                    success=True,
                    duplicate=False,
                    transaction_id=tx.get("id"),
                    error=None,
                )
            )
        except Exception as exc:
            results.append(
                SyncResultItem(
                    client_transaction_id=cid,
                    success=False,
                    duplicate=False,
                    transaction_id=None,
                    error=str(exc),
                )
            )

    return SyncResponse(results=results)
