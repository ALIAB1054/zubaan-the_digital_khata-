"""
extract.py - Updated for Strict Urdu Nasta'liq
"""
import os
import json
from dotenv import load_dotenv
from groq import Groq

# API Key initialization
API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=API_KEY)

def clean_transaction(data):
    result = {"customer": "Unknown", "items": "None", "amount": 0, "type": "cash_sale"}
    if not isinstance(data, dict): return result
    
    result["customer"] = str(data.get("customer") or "Unknown").strip()
    result["items"] = str(data.get("items") or data.get("item") or "None").strip()
    
    try:
        amount = data.get("amount", 0)
        if isinstance(amount, str):
            amount = ''.join(c for c in amount.replace(",", "") if c.isdigit() or c == '.')
        result["amount"] = float(amount)
    except:
        result["amount"] = 0
    
    trans_type = str(data.get("type") or "cash_sale").lower()
    result["type"] = "udhaar" if "udhaar" in trans_type or "credit" in trans_type else "cash_sale"
    return result

def extract_transaction(transcript):
    if not transcript: return clean_transaction({})

    prompt = f"""
    Extract transaction from transcript: {transcript}.
    1. Return ONLY JSON.
    2. Customer names and Items MUST be in URDU Nasta'liq script. NEVER use Hindi/Devanagari.
    3. Type="udhaar" if credit/loan is mentioned, else "cash_sale".
    JSON Format: {{"customer":"", "items":"", "amount":0, "type":"cash_sale"}}
    """
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are an expert in Urdu. Always output values in Urdu Nasta'liq script."},
                {"role": "user", "content": prompt}
            ]
        )
        return clean_transaction(json.loads(response.choices[0].message.content))
    except Exception as e:
        print("Groq Error:", e)
        return clean_transaction({})