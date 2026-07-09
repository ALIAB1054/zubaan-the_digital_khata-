"""
Step 4: Wire everything together — this is your full audio-in to
response-out pipeline. Run this once transcribe_assemblyai.py and
extract.py both work individually.

Usage:
    python pipeline_test.py                  (uses default test_audio.m4a)
    python pipeline_test.py my_recording.m4a  (uses your specified file)
"""

import sys
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
    # Accept filename as a command-line argument, defaulting to test_audio.m4a
    audio_file = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\GOLDEN COMPUTER\Documents\Sound Recordings\Recording (2).m4a"

    result = run_pipeline(audio_file, target_language="english")
    print("\nFinal result:")
    print(result)