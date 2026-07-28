"""
Step 1 (v8): Transcribes clean audio segments directly to native language scripts.
Fully updated to support AssemblyAI's new Universal Speech Models layout parameters.
"""

import os
from dotenv import load_dotenv
import assemblyai as aai

load_dotenv()

aai.settings.api_key = os.environ.get("ASSEMBLYAI_API_KEY") or "f959fec49c394f409ad57868e6db5c62"

LANGUAGE_CODES = {
    "urdu": "ur",
    "hindi": "hi",
    "english": "en",
    "arabic": "ar",
    "punjabi": "pa"
}

PURE_URDU_PROMPT = (
    "This is a shopkeeper ledger cash record transaction spoken in Pakistani Urdu or mixed Urdu-English. "
    "Transcribe the entire audio strictly using the standard Urdu Arabic alphabet script (Nastaliq/Shahmukhi characters). "
    "Do not use any Devanagari, Hindi characters, or Indian script letters under any circumstances. "
    "Example transcription output style: احمد نے پانچ سو روپے نقد دیے۔"
)

def transcribe_audio(file_path: str, language: str = "english", convert: bool = True):

    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)

    lang_key = language.lower()
    lang_code = LANGUAGE_CODES.get(lang_key)

    # --- FIXED: USING THE NEW ASSEMBLYAI UNIVERSAL MODEL CONFIGURATION MATRICES ---
    config_kwargs = {}

    if lang_code:
        config_kwargs["language_code"] = lang_code
        if lang_code == "ur":
            config_kwargs["prompt"] = PURE_URDU_PROMPT

    # Clean configuration layout injection
    config = aai.TranscriptionConfig(**config_kwargs)
    transcriber = aai.Transcriber()

    # Audio translation transmission
    transcript = transcriber.transcribe(
        file_path,
        config=config
    )

    print("=" * 60)
    print("Transcript Status :", transcript.status)
    print("Transcript Text :", transcript.text)
    print("=" * 60)

    if transcript.status == aai.TranscriptStatus.error:
        raise Exception(transcript.error)

    return transcript.text

if __name__ == "__main__":
    print("Zubaan Multi-Language Production Transcription Engine Ready.")