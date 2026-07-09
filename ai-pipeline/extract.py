"""
Step 2: Take transcribed text and extract structured transaction data
using a Groq-hosted LLM (Llama 3.3 70B). Test this on its own with
sample text before wiring it to transcribe.py.
"""

import os
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

EXTRACTION_PROMPT = """You are extracting structured transaction data from spoken shopkeeper notes.
The input may mix Urdu, Punjabi, English, and Arabic in the same sentence.

Return ONLY valid JSON, no explanation, no markdown formatting, matching this shape:
{{
  "customer": "<name transliterated into Latin/English script (e.g. 'Ahmed', not 'احمد'), or null if not mentioned>",
  "item": "<item name in English, or null>",
  "quantity": "<quantity with unit, or null>",
  "amount": <number, or null>,
  "type": "<one of: credit_given, payment_received, cash_sale>",
  "language_detected": "<short code like ur, pa, en, ar, or mixed>"
}}

Important guidance on transaction type — shopkeeper slang is often ambiguous,
use these examples to classify correctly:
- Phrases like "اٹھا دی" (uthaa di), "ادھار دی" (udhaar di), "کھاتے میں لکھ دی"
  (khaate mein likh di) mean the shopkeeper GAVE GOODS ON CREDIT to the
  customer — classify as "credit_given", even though no explicit word for
  "credit" may be said.
- Phrases like "نقد بیچی" (naqad becha), "cash mein di", "cash liya" mean an
  immediate cash transaction — classify as "cash_sale".
- Phrases like "حساب صاف کر دیا" (hisaab saaf kar dia), "پیسے واپس دیے"
  (paise wapas diye), "قرض ادا کیا" (loan paid) mean the customer PAID BACK
  money they previously owed — classify as "payment_received".

Example:
Text: "احمد کو دس کلو چینی میں نے پچاس روپے میں اٹھا دی"
Correct output: {{"customer": "Ahmed", "item": "sugar", "quantity": "10 kg", "amount": 50, "type": "credit_given", "language_detected": "ur"}}
(Note: "اٹھا دی" here means goods were given on credit, NOT a cash sale.)

Text to extract from:
"{text}"
"""


def extract_transaction(transcript: str) -> dict:
    prompt = EXTRACTION_PROMPT.format(text=transcript)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )

    raw = response.choices[0].message.content.strip()
    # Clean up in case the model wraps output in ```json fences
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print("Could not parse JSON. Raw model output was:")
        print(raw)
        return {}


if __name__ == "__main__":
    # Test with the real sentence that previously misclassified as cash_sale
    # and returned the name in Urdu script instead of Latin script
    test_sentences = [
        'I sold 100 extra one for ₹50,000.',
    ]

    for sentence in test_sentences:
        print(f"\nInput: {sentence}")
        result = extract_transaction(sentence)
        print("Extracted:", json.dumps(result, indent=2, ensure_ascii=False))
        