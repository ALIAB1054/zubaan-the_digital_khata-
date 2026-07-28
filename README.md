# 🗣️ Zubaan — The Digital Khata
### An AI-Powered Voice & Multi-Lingual Accounting Ledger

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![OpenAI Whisper](https://img.shields.io/badge/OpenAI-Whisper-412991?style=flat&logo=openai&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

> Simplify ledger book-keeping using voice commands, automated speech-to-text transcription, and intelligent transaction extraction.

---

## 📌 Overview

**Zubaan** is a smart digital khata designed to bridge the gap in digital ledger management. Instead of typing entries, users record a short voice note describing a transaction — Zubaan's AI pipeline reconstructs the audio, transcribes it using OpenAI's **Whisper** speech-to-text model, and automatically updates the ledger database in real time.

## 🔴 The Problem

Most small business owners and shopkeepers still maintain their accounts in a handwritten **khata** (ledger book) — fast for them, but invisible to any digital system. Conventional accounting apps assume users are comfortable typing structured entries in an unfamiliar interface. Zubaan removes that barrier: if you can say it, Zubaan can log it.

## ⚙️ How It Works

1. **Record** — the user records a short voice note describing a transaction.
2. **Clean** — a silence-guardrail filters background noise and reconstructs the audio for accurate parsing.
3. **Transcribe** — OpenAI Whisper STT converts the cleaned audio into text.
4. **Extract** — the AI pipeline parses the transcript into structured transaction data.
5. **Sync** — the entry is written to the backend ledger (Supabase / PostgreSQL), with a local JSON store as an offline fallback.

## ✨ Key Features

- 🎙️ **Voice-to-Ledger Processing** — instant parsing of spoken transactions.
- 🔇 **Silence Guardrail** — noise filtering and reconstruction pipeline for accurate audio parsing.
- 📊 **Automated Ledger Management** — syncs directly with backend database structures.
- 🗂️ **Multi-Format Support** — handles varied audio formats and structured JSON ledger outputs.

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend / API | Python, FastAPI, Uvicorn |
| AI / Speech Recognition | OpenAI Whisper STT, Hugging Face |
| Database | Supabase / PostgreSQL, JSON (local fallback) |
| Environment & Tools | Git, VS Code, Ngrok |

## 🚀 Quick Start

### 1. Prerequisites
Ensure you have **Python 3.10+** installed on your system.

### 2. Installation & Setup

```bash
# Clone the repository
git clone https://github.com/ALIAB1054/zubaan-the-digital_khata-.git

# Navigate to the project directory
cd zubaan-the-digital_khata-

# Create & activate a virtual environment (optional but recommended)
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Server

```bash
python ai-pipeline/api_server.py
```

## 📁 Project Architecture

```
zubaan-the-digital_khata/
├── ai-pipeline/        # Speech processing & Whisper API server
├── backend/             # Supabase & DB sync modules
├── recorded_audio/      # Audio buffer and temporary save logs
└── ledger_db.json       # Local fallback database store
```

## ⚠️ Known Limitations

- Requires standard system audio drivers and `ffmpeg` binaries pre-configured on host platforms.
- Heavy GPU acceleration (CUDA) is recommended for real-time transcription on larger parameter models.
- Highly distorted audio with severe clipping may require additional front-end filtering.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome. Feel free to open a pull request or start a discussion.

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## 👥 Team / Credits

Built with ❤️ by team **BC Crew**.
