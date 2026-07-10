"""
schemas.py
──────────
Pydantic models for request / response validation.
"""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ── Incoming AI-pipeline payload ─────────────────────────────

class TransactionIn(BaseModel):
    """
    Shape coming from the AI transcription pipeline + optional
    frontend fields.
    """
    customer: Optional[str] = None
    item: Optional[str] = None
    quantity: Optional[str] = None
    amount: Decimal
    currency: str = "PKR"
    type: Literal["credit_given", "payment_received", "cash_sale"]
    language_detected: Optional[str] = None
    raw_transcript: Optional[str] = None

    # Optional fields the frontend may attach
    audio_clip_url: Optional[str] = None
    occurred_at: Optional[datetime] = None
    client_transaction_id: Optional[UUID] = None

    @field_validator("customer", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: Any) -> Any:
        """Treat empty / whitespace-only customer names as None."""
        if isinstance(v, str) and v.strip() == "":
            return None
        return v


# ── Sync payload (offline queue) ─────────────────────────────

class SyncItem(BaseModel):
    """One entry in the offline sync batch."""
    customer: Optional[str] = None
    item: Optional[str] = None
    quantity: Optional[str] = None
    amount: Decimal
    currency: str = "PKR"
    type: Literal["credit_given", "payment_received", "cash_sale"]
    language_detected: Optional[str] = None
    raw_transcript: Optional[str] = None
    audio_clip_url: Optional[str] = None
    occurred_at: Optional[datetime] = None
    client_transaction_id: Optional[UUID] = None

    @field_validator("customer", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: Any) -> Any:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v


class SyncRequest(BaseModel):
    transactions: List[SyncItem]


# ── Responses ────────────────────────────────────────────────

class TransactionOut(BaseModel):
    success: bool
    transaction: dict
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    running_balance: Decimal = Decimal(0)


class UndoOut(BaseModel):
    success: bool
    transaction: dict
    transaction_id: str
    deleted: bool
    running_balance: Decimal = Decimal(0)


class BalanceOut(BaseModel):
    customer_id: str
    customer_name: str
    running_balance: Decimal = Decimal(0)


class CustomerWithBalance(BaseModel):
    id: str
    name: str
    normalized_name: str
    running_balance: Decimal = Decimal(0)


class SyncResultItem(BaseModel):
    client_transaction_id: Optional[str] = None
    success: bool
    duplicate: Optional[bool] = None
    transaction_id: Optional[str] = None
    error: Optional[str] = None


class SyncResponse(BaseModel):
    results: List[SyncResultItem]


class TodaySummary(BaseModel):
    today_sales_total: Decimal = Decimal(0)
    cash_sales_total: Decimal = Decimal(0)
    credit_given_total: Decimal = Decimal(0)
    payment_received_total: Decimal = Decimal(0)
    transaction_count: int = 0
    total_outstanding_balance: Decimal = Decimal(0)


class FastMovingItem(BaseModel):
    item: str
    count: int


class MonthlySummary(BaseModel):
    current_month_sales_total: Decimal = Decimal(0)
    previous_month_sales_total: Decimal = Decimal(0)
    current_month_credit_given_total: Decimal = Decimal(0)
    previous_month_credit_given_total: Decimal = Decimal(0)
    current_month_payment_received_total: Decimal = Decimal(0)
    previous_month_payment_received_total: Decimal = Decimal(0)
    current_month_transaction_count: int = 0
    previous_month_transaction_count: int = 0
    total_outstanding_balance: Decimal = Decimal(0)
    fast_moving_items: List[FastMovingItem] = []


class HealthResponse(BaseModel):
    status: str = "ok"
    message: str = "Zubaan backend is running"


class AudioUploadOut(BaseModel):
    success: bool
    audio_url: str
    transaction_id: str
