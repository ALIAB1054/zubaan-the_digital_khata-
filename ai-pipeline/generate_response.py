"""
generate_response.py
Zubaan AI — Robust Confirmation Generator Matrix
"""
import os

def generate_confirmation(transaction, target_language="Urdu"):
    # --- FIXED: ChatGPT Data Type Securites & Items Mapping Matrix ---
    customer = str(transaction.get("customer") or "Unknown")
    amount = float(transaction.get("amount") or 0)
    trans_type = str(transaction.get("type") or "cash_sale")
    item = str(transaction.get("items") or "None")

    lang = target_language.lower()

    if lang == "urdu":
        if trans_type == "udhaar":
            return f"{customer} ke khate mein {amount} rupay udhaar likh diye gaye hain."
        else:
            return f"{customer} se {amount} rupay naqd wasool ho gaye hain."
            
    elif lang == "english":
        if trans_type == "udhaar":
            return f"Added {amount} PKR to credit/udhaar for {customer}."
        else:
            return f"Recorded cash payment of {amount} PKR from {customer}."
            
    elif lang == "arabic":
        if trans_type == "udhaar":
            return f"تم تسجيل دين بقيمة {amount} لـ {customer}."
        else:
            return f"تم استلام {amount} نقداً من {customer}."
            
    elif lang == "punjabi":
        if trans_type == "udhaar":
            return f"{customer} de khate vich {amount} rupaye udhaar likh ditte ne."
        else:
            return f"{customer} walon {amount} rupaye cash mil gaye ne."

    # Default fallback setup
    return f"Transaction recorded for {customer}: {amount} PKR."