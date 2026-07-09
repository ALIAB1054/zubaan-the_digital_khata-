"""
Step 1: Transcribe an audio file using Groq's Whisper large-v3.
Test this file first, on its own, before connecting it to anything else.
"""

import os
from dotenv import load_dotenv
from groq import Groq
from pydub import AudioSegment

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# User picks one of these before recording — no auto-detect.
# Whisper's official language codes for each option:
LANGUAGE_CODES = {
    "urdu": "ur",
    "english": "en",
    "punjabi": "pa",
    "arabic": "ar",
    "pashto": "ps",   # swap in if your team uses Pashto instead of Punjabi
    "sindhi": "sd",   # swap in if your team uses Sindhi instead of Punjabi
}


def convert_to_wav(input_path: str, output_path: str = "converted_audio.wav") -> str:
    """
    Converts any input audio (m4a, mp3, etc.) to 16kHz mono WAV —
    the format Whisper performs best on. Requires ffmpeg installed.
    """
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_frame_rate(16000).set_channels(1)
    audio.export(output_path, format="wav")
    return output_path


def transcribe_audio(file_path: str, language: str = "urdu", convert: bool = True) -> str:
    """
    Takes a path to an audio file (wav, mp3, m4a, etc.) and the language
    the user selected in the UI (e.g. "urdu", "english", "punjabi", "arabic").
    Converts to 16kHz mono WAV first (recommended) unless convert=False.
    Returns the transcribed text.
    """
    lang_code = LANGUAGE_CODES.get(language.lower())
    if not lang_code:
        raise ValueError(
            f"Unsupported language '{language}'. Choose from: {list(LANGUAGE_CODES.keys())}"
        )

    if convert:
        file_path = convert_to_wav(file_path)

    with open(file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            file=(file_path, audio_file.read()),
            model="whisper-large-v3",
            response_format="text",
            language=lang_code,  # forced, not auto-detected — user chose this
        )
    return transcription


if __name__ == "__main__":
    # Record a short test clip yourself saying something like:
    # "Ahmed ko do kilo chini pachas rupay udhaar di"
    # Save it as test_audio.m4a (or .mp3) in this same folder.

    test_file = r"c:\Users\GOLDEN COMPUTER\Documents\Sound Recordings\Recording (2).m4a"  # change this to match your test file name
    selected_language = "english"  # change this to match what you actually spoke

    if os.path.exists(test_file):
        result = transcribe_audio(test_file, language=selected_language, convert=True)
        print(f"Transcribed text ({selected_language}):")
        print(result)
    else:
        print(f"Put a test audio file named '{test_file}' in this folder first.")