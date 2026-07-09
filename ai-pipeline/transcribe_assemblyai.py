"""
Step 1 (v2): Transcribe an audio file using AssemblyAI's Universal-3-5 Pro
model via the SYNC API — single request, no polling, much faster for
short clips (a few seconds of shopkeeper speech) than the async API.
Same input/output shape as before, so nothing downstream
(extract.py, generate_response.py, pipeline_test.py) needs to change.
"""

import os
from dotenv import load_dotenv
import assemblyai as aai
from pydub import AudioSegment
from aksharamukha import transliterate

load_dotenv()

aai.settings.api_key = os.environ.get("ASSEMBLYAI_API_KEY")

# Universal-3-5 Pro's officially pinnable languages include "hi" (Hindi)
# but not "ur" (Urdu) as a separate code — since Hindi and Urdu are the
# same spoken language (Hindustani) with different scripts, we support
# BOTH as real options: "hindi" pins to hi and keeps Devanagari script
# (useful for Indian users/judges), "urdu" pins to hi and converts the
# output to Urdu/Nastaliq script (for Pakistani shopkeeper users).
LANGUAGE_CODES = {
    "hindi": "hi",     # pin to Hindi, keep native Devanagari script
    "urdu": "hi",       # pin to Hindi for accuracy, convert script to Urdu after
    "english": "en",
    "punjabi": None,    # not officially pinnable; falls back to code-switch mode
    "arabic": "ar",
}

CODE_SWITCHING_PROMPT = (
    "Shopkeeper business transaction, spoken in Hindi, Urdu, Punjabi, "
    "English, and Arabic, sometimes mixed in the same sentence. "
    "Transcribe Punjabi using Shahmukhi (Perso-Arabic) script, as spoken "
    "in Pakistan, not Gurmukhi script. "
    "Keep English and Arabic words in their own respective scripts."
)


def convert_to_wav(input_path: str, output_path: str = "converted_audio.wav") -> str:
    """
    Converts any input audio (m4a, mp3, webm, etc.) to 16kHz mono
    16-bit PCM WAV — the exact format AssemblyAI's Sync API requires.
    Requires ffmpeg installed.
    """
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)  # 2 bytes = 16-bit
    audio.export(output_path, format="wav")
    return output_path


def devanagari_to_urdu(text: str) -> str:
    """
    Converts Hindi (Devanagari script) text to Urdu (Perso-Arabic/Nastaliq
    script). Only called when the user explicitly picks "urdu" as their
    language — "hindi" skips this and keeps the native script.
    """
    return transliterate.process("Devanagari", "Urdu", text)


def transcribe_audio(
    file_path: str,
    language: str = None,
    convert: bool = True,
) -> str:
    """
    Takes a path to a SHORT audio file (a few seconds, under 120s) and
    returns the transcript using the Sync API.
    - language="hindi": pins to Hindi, keeps Devanagari script as-is.
    - language="urdu": pins to Hindi for accuracy, converts result to
      Urdu/Nastaliq script.
    - language="english" / "arabic": pins directly.
    - language=None or "punjabi": lets the model code-switch natively
      (no script conversion applied).
    """
    if convert:
        file_path = convert_to_wav(file_path)

    config_kwargs = {
        "model": "universal-3-5-pro",
        "prompt": CODE_SWITCHING_PROMPT,
    }

    needs_urdu_conversion = False

    if language:
        lang_key = language.lower()
        lang_code = LANGUAGE_CODES.get(lang_key)
        if lang_code:
            config_kwargs["language_code"] = lang_code
        if lang_key == "urdu":
            needs_urdu_conversion = True

    config = aai.SyncTranscriptionConfig(**config_kwargs)
    result = aai.SyncTranscriber().transcribe(file_path, config=config)

    text = result.text

    if needs_urdu_conversion:
        text = devanagari_to_urdu(text)

    return text


if __name__ == "__main__":
    test_file = "test_audio.m4a"

    if os.path.exists(test_file):
        # Try both to compare directly:
        print("As Hindi (Devanagari script):")
        print(transcribe_audio(test_file, language="hindi", convert=True))

        print("\nAs Urdu (converted to Nastaliq script):")
        print(transcribe_audio(test_file, language="urdu", convert=True))
    else:
        print(f"Put a test audio file named '{test_file}' in this folder first.")