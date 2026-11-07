# RunbookMind

RunbookMind is an on‑call incident‑response AI assistant that **remembers every past incident** and **gets smarter with each resolution**. It leverages Hindsight memory (vector store + reasoning) and a Groq LLM to suggest root causes, first‑action recommendations, and alternative actions for new alerts.

## Features
- Ingest historical incidents into a Hindsight memory bank.
- Analyse a new alert: recall similar incidents, run a LLM‑guided reasoning step and return a structured JSON answer.
- Capture engineer feedback (worked / partially worked / didn’t work) and store it as new memories.
- Memory ON / OFF toggle with side‑by‑side comparison for demos.
- Memory inspector that shows the recalled facts for each answer.
- Simple learning‑metric chart (accuracy over time).

## Architecture
```
+----------------------+        +-------------------------+
|  Streamlit UI        | <----> |  FastAPI Backend        |
|  - Alert form        |  HTTP  |  /ingest  /analyze      |
|  - Memory ON/OFF     |        |  /feedback /ask         |
+----------------------+        +-----------+-------------+
                                  |                   |
                          +-------v------+    +-------v-------+
                          |  Hindsight   |    |  Groq LLM     |
                          |  retain      |    |  (gpt‑oss‑120b)|
                          |  recall      |    +---------------+
                          |  reflect     |
                          +--------------+
```

## Quick Start (Windows)
1. **Prerequisites** – Python 3.13 (installed via Anaconda) – already set up in this repo.
2. **Install dependencies**
   ```powershell
   cd d:\runbookmind
   & "C:\ProgramData\anaconda3\python.exe" -m pip install -r requirements.txt
   ```
3. **Create a Hindsight memory bank** (run once)
   ```powershell
   & "C:\ProgramData\anaconda3\python.exe" backend/init_bank.py
   ```
4. **Load synthetic incidents**
   ```powershell
   & "C:\ProgramData\anaconda3\python.exe" -m backend.ingest
   ```
5. **Start the API**
   ```powershell
   uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```
6. **Run the UI** (in a new terminal)
   ```powershell
   streamlit run frontend\app.py
   ```
7. Open the UI at `http://localhost:8501` and start experimenting!

