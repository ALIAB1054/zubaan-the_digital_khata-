"""
API server for Person 3 (frontend) to call.

Wraps the full pipeline (transcribe -> extract -> generate confirmation)
behind a single HTTP endpoint, so the frontend never has to touch Python,
Groq, or AssemblyAI directly — just send audio, get JSON back.

Run this with:
    uvicorn api_server:app --reload --port 8000

Person 3 then calls: POST http://localhost:8000/process-audio
  - form field "audio": the recorded audio file (m4a, mp3, wav, etc.)
  - optional form field "speech_language": "urdu" / "english" / "arabic" / "punjabi"
        (the language the SHOPKEEPER SPOKE IN — forcing this gives more
        reliable script output than leaving it to auto-detect, e.g.
        prevents Urdu speech from being transcribed in Hindi/Devanagari
        script by mistake. Defaults to "urdu".)
  - optional form field "target_language": "Urdu" / "English" / "Arabic" / "Punjabi"
        (the language the CONFIRMATION RESPONSE should be generated in —
        independent from speech_language)
"""

import os
import tempfile

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from transcribe_assemblyai import transcribe_audio
from extract import extract_transaction
from generate_response import generate_confirmation

app = FastAPI(title="Zubaan AI Pipeline API")

# Allows Person 3's frontend (running on a different port/domain during
# development) to actually call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this to your real frontend URL before deploying
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Quick check that the server is running — Person 3 can call this first."""
    return {"status": "ok", "message": "Zubaan AI pipeline is running"}


@app.post("/process-audio")
async def process_audio(
    audio: UploadFile = File(...),
    speech_language: str = Form("urdu"),
    target_language: str = Form("Urdu"),
):
    """
    Main endpoint. Takes an uploaded audio file, runs the full pipeline,
    and returns the transcript, structured transaction data, and a
    natural-language confirmation — everything the frontend needs to
    show the confirm-before-save card.
    """
    # Save the uploaded file to a temporary location so our existing
    # functions (which expect a file path) can work with it unchanged.
    suffix = os.path.splitext(audio.filename)[1] or ".m4a"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        contents = await audio.read()
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        # Forcing speech_language (instead of None) gives reliable script
        # output — e.g. guarantees Urdu script instead of occasionally
        # defaulting to Hindi/Devanagari for Urdu speech.
        transcript = transcribe_audio(tmp_path, language=speech_language, convert=True)
        transaction = extract_transaction(transcript)
        confirmation = generate_confirmation(transaction, target_language=target_language)

        return JSONResponse({
            "success": True,
            "transcript": transcript,
            "transaction": transaction,
            "confirmation_text": confirmation,
        })

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )

    finally:
        # Clean up the temporary file regardless of success/failure
        if os.path.exists(tmp_path):
            os.remove(tmp_path)