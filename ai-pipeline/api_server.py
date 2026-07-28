import os, json, tempfile, traceback, re, shutil
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from fastapi import FastAPI, File, Form, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from groq import Groq

app = FastAPI(title="Zubaan Secure AI Pipeline")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Groq()

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(_SCRIPT_DIR, "recorded_audios")
os.makedirs(AUDIO_DIR, exist_ok=True)
app.mount("/audios", StaticFiles(directory=AUDIO_DIR), name="audios")

class LedgerEntry(BaseModel):
    customer: str
    items: str
    type: str
    amount: float
    transcript: str
    audio_filename: str = ""

# DYNAMIC PRIVACY ENHANCEMENT: Separate ledger database per client IP address
def get_secure_db_path(request: Request):
    # Retrieve client IP address behind proxies/ngrok if available
    client_host = request.headers.get("x-forwarded-for") or request.client.host
    if "," in client_host:
        client_host = client_host.split(",")[0].strip()
        
    safe_ip_string = re.sub(r'[^a-zA-Z0-9_-]', '_', client_host)
    return os.path.join(os.path.dirname(_SCRIPT_DIR), f"ledger_{safe_ip_string}.json")

def calculate_top_product(db_file_path: str):
    if not os.path.exists(db_file_path) or os.path.getsize(db_file_path) == 0:
        return "NONE YET"
    try:
        with open(db_file_path, "r", encoding="utf-8") as f:
            records = json.load(f)
            
        frequencies = {}
        garbage_tokens = {
        "kg", "kgs", "kilo", "kilos", "kilogram", "kilograms", "g", "gram", "grams", "liter", "liters", "ltr", "ml", 
        "rs", "rupees", "rupaay", "rupay", "packet", "pack", "bottle", "box", "boxes",
        "of", "to", "for", "with", "and", "the", "ka", "ki", "ke", "ko", "par",
        "none", "کوئی", "نہیں", "dozen", "dozens", "pieces", "pcs", "item", "items"
        }

        for r in records:
            item_raw = str(r.get("items", "")).strip().lower()
            if not item_raw:
                continue
            
            sub_items = [s.strip() for s in item_raw.replace(",", " ").split() if s.strip()]
            cleaned_tokens = []
            for token in sub_items:
                token_clean = "".join([c for c in token if c.isalpha()])
                
                # Normalize Plurals (e.g., eggs -> egg)
                if token_clean.endswith("es") and len(token_clean) > 3:
                    token_clean = token_clean[:-2]
                elif token_clean.endswith("s") and len(token_clean) > 2 and not token_clean.endswith("ss"):
                    token_clean = token_clean[:-1]
                    
                if token_clean and token_clean not in garbage_tokens:
                    cleaned_tokens.append(token_clean)
            
            if cleaned_tokens:
                core_product = " ".join(cleaned_tokens)
                frequencies[core_product] = frequencies.get(core_product, 0) + 1
                
        if not frequencies:
            return "NONE YET"
            
        max_count = max(frequencies.values())
        
        # THRESHOLD CHECK: Single entry is not enough to determine demand
        if max_count < 2:
            return "NONE YET"

        top_candidates = [item for item, count in frequencies.items() if count == max_count]
        
        # Handle Tie between multiple items
        if len(top_candidates) > 1:
            return "NO TOP ITEM"
            
        return top_candidates[0].upper() 
        
    except Exception as e:
        print(f"Error calculating metrics: {str(e)}")
        return "NONE YET"

# Direct Route to serve index.html directly from FastAPI!
@app.get("/")
async def serve_frontend():
    # Looks for index.html in the same directory or frontend subdirectory
    local_index = os.path.join(_SCRIPT_DIR, "index.html")
    frontend_index = os.path.join(_SCRIPT_DIR, "frontend", "index.html")
    
    if os.path.exists(local_index):
        return FileResponse(local_index)
    elif os.path.exists(frontend_index):
        return FileResponse(frontend_index)
    else:
        return JSONResponse(status_code=404, content={"error": "index.html file not found in directory"})

@app.get("/get-ledger")
async def get_ledger(request: Request):
    try:
        db_file = get_secure_db_path(request)
        if not os.path.exists(db_file) or os.path.getsize(db_file) == 0:
            return JSONResponse({"records": [], "top_product": "None yet"})
        with open(db_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                return JSONResponse({"records": data, "top_product": calculate_top_product(db_file)})
            except json.JSONDecodeError:
                return JSONResponse({"records": [], "top_product": "None yet"})
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/save-ledger")
async def save_ledger(entry: LedgerEntry, request: Request):
    try:
        db_file = get_secure_db_path(request)
        ledger_data = []
        if os.path.exists(db_file) and os.path.getsize(db_file) > 0:
            try:
                with open(db_file, "r", encoding="utf-8") as f:
                    ledger_data = json.load(f)
            except json.JSONDecodeError:
                pass

        final_audio_filename = entry.audio_filename
        
        if entry.audio_filename and os.path.exists(os.path.join(AUDIO_DIR, entry.audio_filename)):
            clean_customer_name = re.sub(r'[^a-zA-Z0-9_-]', '_', entry.customer.strip().lower()) or "unknown"
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"{clean_customer_name}_{timestamp_str}.webm"
            
            old_filepath = os.path.join(AUDIO_DIR, entry.audio_filename)
            new_filepath = os.path.join(AUDIO_DIR, new_filename)
            
            try:
                os.rename(old_filepath, new_filepath)
                final_audio_filename = new_filename
            except Exception as rename_error:
                print(f"File rename exception: {str(rename_error)}")

        target_customer = entry.customer.strip().lower()
        is_repayment = False

        # CLEAN RECONCILIATION LOGIC
        if entry.type == "cash_sale" or "udhaar" in entry.items.lower() or "cleared" in entry.items.lower():
            for record in ledger_data:
                existing_customer = str(record.get("customer", "")).strip().lower()
                
                # Match active udhaar entry for the same customer
                if existing_customer == target_customer and record.get("type") == "udhaar":
                    existing_amount = float(record.get("amount", 0))
                    payment_amount = float(entry.amount)
                    
                    # Clean base items text without duplicate tags
                    base_items = str(record.get("items", ""))
                    base_items = re.sub(r'\s*\((Remaining Udhaar|Paid/Cleared)\)', '', base_items, flags=re.IGNORECASE).strip()

                    if payment_amount >= existing_amount:
                        # Full Repayment: Change type to cash_sale and attach single clean tag
                        record["type"] = "cash_sale"
                        record["items"] = f"{base_items} (Paid/Cleared)"
                        record["amount"] = existing_amount
                    else:
                        # Partial Repayment: Reduce balance without cluttering items string
                        record["amount"] = existing_amount - payment_amount
                        record["items"] = base_items
                    
                    record["transcript"] = f"Payment Received: {entry.transcript}"
                    is_repayment = True
                    break

        # If it's a completely new sale or new udhaar entry
        if not is_repayment:
            new_entry = {
                "customer": entry.customer,
                "items": entry.items,
                "type": entry.type,
                "amount": entry.amount,
                "transcript": entry.transcript,
                "audio_filename": final_audio_filename,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            ledger_data.append(new_entry)
        
        with open(db_file, "w", encoding="utf-8") as f:
            json.dump(ledger_data, f, ensure_ascii=False, indent=4)
            
        return JSONResponse({"success": True, "top_product": calculate_top_product(db_file)})
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.delete("/delete-ledger/{index}")
async def delete_ledger(index: int, request: Request):
    try:
        db_file = get_secure_db_path(request)
        if not os.path.exists(db_file):
            return JSONResponse(status_code=404, content={"error": "Database empty"})
        with open(db_file, "r", encoding="utf-8") as f:
            ledger_data = json.load(f)
        
        if 0 <= index < len(ledger_data):
            target_entry = ledger_data[index]
            filename_to_clear = target_entry.get("audio_filename", "")
            if filename_to_clear:
                target_path = os.path.join(AUDIO_DIR, filename_to_clear)
                if os.path.exists(target_path):
                    try: os.remove(target_path)
                    except: pass
            
            ledger_data.pop(index)
            with open(db_file, "w", encoding="utf-8") as f:
                json.dump(ledger_data, f, ensure_ascii=False, indent=4)
            return JSONResponse({"success": True, "top_product": calculate_top_product(db_file)})
        return JSONResponse(status_code=400, content={"error": "Invalid Index"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/process-audio")
async def process_audio(
    file: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
    speech_language: Optional[str] = Form("Urdu"),
    language: Optional[str] = Form("Urdu"),
    response_language: Optional[str] = Form("Urdu")
):
    try:
        # Pick whichever file key frontend sent
        audio_file_obj = file or audio
        if not audio_file_obj:
            return JSONResponse(status_code=400, content={"error": "No audio file provided"})

        actual_lang = speech_language or language or "Urdu"
        
        # Save temp audio file
        audio_bytes = await audio_file_obj.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        lang_map = {
            "urdu": "ur",
            "english": "en",
            "arabic": "ar",
            "punjabi": "pa"
        }
        mapped_lang = lang_map.get(actual_lang.lower(), "ur")

        # Customize prompt based on language for better accuracy
        if mapped_lang in ["ur", "pa"]:
            prompt = "یہ پاکستانی دکان کا کھاتہ ہے۔ ادھار، نقد، روپے، کلو۔ Pakistani retail khata audio log entry. Contains terms like udhaar, cash, rupay, aur, bhi."
        else:
            prompt = "Pakistani retail khata audio log entry in English. Contains terms like udhaar, cash, rupay."

        # 1. WHISPER SPEECH-TO-TEXT WITH RECONSTRUCTION & SILENCE GUARDRAIL
        with open(tmp_path, "rb") as audio_file:
            transcription_obj = client.audio.transcriptions.create(
                file=(os.path.basename(tmp_path), audio_file.read()),
                model="whisper-large-v3",
                prompt=prompt,
                language=mapped_lang
            )
            
        transcript = transcription_obj.text.strip()

        # Silence / Noise Guardrail check (Ignore hallucinations)
        lower_transcript = transcript.lower().strip()
        hallucinations = [
            "thank you.", "thank you", "thanks.", "subscribe", "subscribe.", 
            "bye.", "amén.", "you", "yeah.", "ok.", "okay.", "test.", "testing."
        ]
        
        if not transcript or len(transcript) < 3 or lower_transcript in hallucinations:
            return JSONResponse({
                "success": False,
                "error": "Background noise ignored. No clear khata entry detected.",
                "transcript": transcript
            })

        # 2. STRICT SYSTEM PROMPT FOR LLAM-3 EXTRACTION
        system_content = (
            "You are a strict financial ledger AI parser for retail shops. Extract structured JSON from shopkeeper audio transcript.\n"
            "CRITICAL RULES:\n"
            "1. Output ONLY valid raw JSON with keys: 'customer', 'items', 'type', 'amount'. No markdown code blocks, no extra text.\n"
            "2. 'customer': ALWAYS extract the customer's name mentioned in the sentence (e.g. 'Ali', 'Hamza', 'Ahmad'). Standardise to clean English Title Case. Look for preposition patterns like 'to Ali', 'for Ali', 'Ali ko'. Default to 'Unknown' ONLY if no name exists at all.\n"
            "3. 'items': Extract the product items and quantities mentioned (e.g., '2 kg milk', 'sugar'). If no quantity is stated, extract product name (e.g., 'milk'). If settling debt/payment with no items mentioned, set 'Payment Cleared'. Default to 'General Items' if missing.\n"
            "4. 'amount': Must be an INTEGER or FLOAT in PKR. Convert word numbers to digits (e.g. 'two' -> 2, 'five hundred' -> 500). IF NO PRICE OR RS IS EXPLICITLY STATED in transcript, ESTIMATE REASONABLE TOTAL OR DEFAULT TO 0. DO NOT BREAK OTHER FIELDS IF AMOUNT IS MISSING.\n"
            "5. 'type': Set to 'udhaar' if credit/debt is implied or stated ('udhaar', 'khata', 'due', 'to Ali'). Set to 'cash_sale' if paid/cash/repayment ('cash', 'paid', 'wapas', 'de diye').\n\n"
            "FEW-SHOT EXAMPLES:\n"
            "Transcript: 'Provide two kg milk to Ali'\n"
            "JSON: {\"customer\": \"Ali\", \"items\": \"2 kg milk\", \"type\": \"udhaar\", \"amount\": 0}\n\n"
            "Transcript: 'Ali ko 200 rupay ka doodh cash par do'\n"
            "JSON: {\"customer\": \"Ali\", \"items\": \"milk\", \"type\": \"cash_sale\", \"amount\": 200}"
        )

        llm_response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": f"Audio Transcript: {transcript}"}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )

        extracted_json = json.loads(llm_response.choices[0].message.content)
        
        # Safeguard: if LLM returns items as list or dict, convert to a readable string
        items_val = extracted_json.get("items", "")
        if isinstance(items_val, list):
            extracted_json["items"] = ", ".join(
                i.get("name", str(i)) if isinstance(i, dict) else str(i) for i in items_val
            )
        elif isinstance(items_val, dict):
            extracted_json["items"] = ", ".join(f"{v}" for k, v in items_val.items())
        else:
            extracted_json["items"] = str(items_val)
        
        # Save temp audio file name for playing in UI logs
        audio_filename = f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.webm"
        saved_audio_path = os.path.join(AUDIO_DIR, audio_filename)
        with open(saved_audio_path, "wb") as f:
            f.write(audio_bytes)

        return JSONResponse({
            "success": True,
            "transcript": transcript,
            "transaction": extracted_json,
            "audio_filename": audio_filename
        })

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)