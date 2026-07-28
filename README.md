<div align="center">

# 🎙️ Zubaan — The Digital Khata

**An AI-Powered Voice & Multi-lingual Accounting Ledger**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Whisper](https://img.shields.io/badge/OpenAI-Whisper-412991?style=for-the-badge&logo=openai&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

<p align="center">
  Simplify ledger book-keeping using voice commands, automated speech-to-text transcription, and intelligent transaction extraction.
</p>

---

</div>

## 📌 Overview

**Zubaan** is a smart digital khata designed to bridge the gap in digital ledger management. Users can record voice notes regarding transactions, which are automatically processed through an AI pipeline to reconstruct audio, transcribe text using Whisper STT, and update the ledger database in real-time.

---

## ✨ Key Features

- 🗣️ **Voice-to-Ledger Processing**: Instant parsing of spoken transactions.
- 🛡️ **Silence Guardrail**: Noise filtering and reconstruction pipeline for accurate audio parsing.
- 🗄️ **Automated Ledger Management**: Syncs directly with backend database structures.
- 📊 **Multi-Format Support**: Handles varied audio formats and structured json ledger outputs.

---

## 🛠️ Tech Stack

- **Backend / API**: Python, FastAPI / Uvicorn
- **AI / Speech Recognition**: OpenAI Whisper STT, Hugging Face
- **Database**: Supabase / PostgreSQL / JSON DB
- **Environment & Tools**: Git, VS Code, Ngrok

---

## 🚀 Quick Start

### 1. Prerequisites
Ensure you have Python 3.10+ installed on your system.

```bash
python --version
