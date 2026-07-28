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
2. Installation & Setup

Clone the repository and install necessary dependencies:
Bash

# Clone repository
git clone [https://github.com/ALIAB1054/zubaan-the_digital_khata-.git](https://github.com/ALIAB1054/zubaan-the_digital_khata-.git)

# Navigate to project directory
cd zubaan-the_digital_khata-

# Create & activate virtual environment (optional but recommended)
python -m venv venv
# On Windows:
venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

3. Run the Server

Start the API pipeline server locally:
Bash

python ai-pipeline/api_server.py

📂 Project Architecture
Plaintext

zubaan-the_digital_khata/
├── ai-pipeline/          # Speech processing & Whisper API server
├── backend/              # Supabase & DB sync modules
├── recorded_audios/      # Audio buffer and temporary wave logs
└── ledger_db.json        # Local fallback database store

🤝 Contributors

Thanks to the contributors behind this project!
📄 License

This project is licensed under the MIT License - see the LICENSE file for details.


---

### Step 3: Pro-Tips for Extra Visual Polish

1. **Architecture Diagram / Screenshots**:
   Repo ke andar ek `assets/` folder banayein, usme demo screenshot ya UI ka workflow image daalein. README mein insert karne ke liye:
   `![Demo](assets/demo.png)`
2. **Badges Customized**:
   [Shields.io](https://shields.io/) se aap customize badges banasakte hain (jaise build status, version, stars etc).
3. **Repository Details Sidebar**:
   GitHub repo page ke right side par **About** section ke sath ⚙️ icon par click ka
⚠️ Known Limitations

    Requires standard system audio drivers and ffmpeg binaries pre-configured on host platforms.

    Heavy GPU acceleration (CUDA) is recommended for real-time transcription on larger parameter models.

    Highly distorted audio with severe clipping may require additional front-end filtering.

🤝 Team / Credits

Built with ❤️ by Rashid Aziz and project collaborators.
