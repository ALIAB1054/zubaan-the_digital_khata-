"""
Step 4: Wire everything together — this is your full audio-in to
response-out pipeline. Run this once transcribe_assemblyai.py and
extract.py both work individually.
"""

import sys
import os

# SYSTEM LEVEL BYPASS: Keys ko direct script ke shuru mein initialize kar diya
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

from transcribe_assemblyai import transcribe_audio
from extract import extract_transaction
from generate_response import generate_confirmation

def run_pipeline(audio_file_path: str, target_language: str = "Urdu") -> dict:
    print(f"1. Transcribing audio ({audio_file_path})...")
    transcript = transcribe_audio(audio_file_path)
    print(f"   -> {transcript}")

    print("2. Extracting structured data...")
    transaction = extract_transaction(transcript)
    print(f"   -> {transaction}")

    print("3. Generating spoken confirmation...")
    confirmation = generate_confirmation(transaction, target_language=target_language)
    print(f"   -> {confirmation}")

    return {
        "transcript": transcript,
        "transaction": transaction,
        "confirmation_text": confirmation,
    }

if __name__ == "__main__":
    audio_file = "ai-pipeline/converted_audio.wav"

    result = run_pipeline(audio_file, target_language="English")
    print("\nFinal result:")
    print(result)