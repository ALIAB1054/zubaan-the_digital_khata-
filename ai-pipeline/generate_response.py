import os
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

RESPONSE_PROMPT = """You are a friendly voice assistant confirming a shopkeeper's transaction.
Given this structured transaction data, write ONE short, natural confirmation sentence
in {target_language}, the way a helpful assistant would speak it out loud.
Do not include any JSON or explanation, just the sentence.

Transaction data:
{data}
"""


def generate_confirmation(transaction: dict, target_language: str = "Urdu") -> str:
    prompt = RESPONSE_PROMPT.format(
        target_language=target_language,
        data=json.dumps(transaction, ensure_ascii=False),
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )

    return response.choices[0].message.content.strip()


if __name__ == "__main__":
    sample_transaction = {
        "customer": "Ahmed",
        "item": "sugar",
        "quantity": "2kg",
        "amount": 50,
        "type": "credit_given",
        "language_detected": "ur-pa-mixed",
    }

    for lang in ["Urdu", "English", "Arabic"]:
        confirmation = generate_confirmation(sample_transaction, target_language=lang)
        print(f"\n[{lang}] {confirmation}")