# F.R.I.D.A.Y. by Tsakane

![F.R.I.D.A.Y. HUD Interface](media/hud_screenshot.png)

F.R.I.D.A.Y. (Fully Responsive Intelligent Digital Assistant for You) is a custom, Tony Stark-inspired AI assistant evolved with multi-model brain cores, resilient failover routing, and rich speech synthesis control. It features both a desktop-based **LiveKit Voice Agent** and a sleek **FastAPI Web Client** with a real-time Systems Diagnostics console.

---

## Core Features (Current State)

### 🧠 Multi-Model Switcher (Neural Core)
You can dynamically hot-swap F.R.I.D.A.Y.'s reasoning core on the fly via the Web UI Settings panel. It supports:
*   **Groq** (Llama 3.3-70b-versatile) — *Default*
*   **Gemini** (Gemini 3.5 Flash)
*   **OpenAI** (GPT-4o)

### 🔄 Resilient Provider Fallover (LLM Chain)
Never worry about daily API rate limits (like Gemini 429 quota blocks) again. If your chosen model fails, F.R.I.D.A.Y. automatically reroutes the request in real time through the next available provider in the chain (e.g., falling back to Groq) and logs the failover warnings directly in the Systems Diagnostics Log.

### 🗣️ Phonetic Pronunciation Override
Custom speech synthesis rules ensure F.R.I.D.A.Y. speaks correctly:
*   **Spelling:** Displayed as **Tsakane** in all chat bubbles and transcriptions.
*   **Pronunciation:** Vocalized phonetically as **"Sekani"** across both the Web client's speech synthesis and the LiveKit streaming audio pipeline.

### 🌐 World Monitor & Zimbabwean News Integration
F.R.I.D.A.Y. is connected to a live global intelligence system. Asking *"What's happening in the world?"* or *"Can you tell me what is going on around the world?"* triggers:
1.  A longer, more detailed news brief (5–7 sentences), specifically checking for local news regarding **Zimbabwe** via **The Herald Zimbabwe** RSS feed (falling back to *"no outstanding international news regarding Zimbabwe as of now"* if none is found).
2.  An immediate browser launch opening the **World Monitor** app configured directly with pre-selected layer filters (Conflicts, Bases, Hotspots, Nuclear, Sanctions, Weather, etc.).
3.  A conclusion cue: *"I have opened the world monitor app for you, boss"* while she continues speaking in the background.

### 💾 Persistent SQLite Memory
All chat history and long-term profile preferences are backed by a local SQLite instance (`friday.db`):
*   **Chat Restoration:** Reloading Microsoft Edge automatically fetches past conversation history via `GET /api/history` and restores message bubbles on screen.
*   **Fact Memorization:** Exposes tools for F.R.I.D.A.Y. to explicitly remember facts about you (e.g., *"remember that my favorite language is Python"*). Memories are injected dynamically into the system instructions at session startup.

### 🖥️ Desktop Automation & Systems Diagnostics
F.R.I.D.A.Y. acts as a system administrator dashboard:
*   **Application Launcher:** Asynchronously starts local applications (Notepad, Calculator, Paint, Edge, etc.) in the background without blocking the backend.
*   **Safe File Finder:** Case-insensitive, recursion-depth-limited filesystem search to find project files without lagging.
*   **Task List Analyzer:** Parses running processes and returns a table of the heaviest memory-hogging tasks currently active.
*   **Cyber Security Netstat Scan:** Scans system sockets and ports, outputting active `LISTENING` and `ESTABLISHED` TCP/UDP connections.

### 🌍 Web Search & Article Crawling
F.R.I.D.A.Y. has real-time internet awareness built on free, keyless protocols:
*   **DuckDuckGo HTML Scraping:** Queries the official DuckDuckGo HTML-only endpoint to search the web without needing paid API keys or hitting query rate limits.
*   **HTML Noise Stripping:** Downloads webpages and cleans them using `BeautifulSoup4`. It strips away scripts, styles, navigation bars, headers, footers, and sidebars, delivering pure body text (truncated to 5,000 characters) to optimize LLM reasoning and conserve context tokens.

---

## Project Structure

```text
friday-tony-stark-demo/
├── server.py           # Starts the FastMCP Tool Server (SSE on port 8000)
├── web_friday.py       # FastAPI web server backend (SSE client + REST APIs on port 8050)
├── agent_friday.py     # LiveKit voice agent script (WebRTC speech agent)
├── start.bat           # Unified launcher script
├── .env                # App API credentials and defaults
├── friday.db           # SQLite local database file (ignored by Git)
│
└── friday/             # Core Package
    ├── database.py     # Database schema, init, and CRUD helper functions
    ├── config.py       # App settings and environment variables
    │
    └── tools/          # MCP Tools
        ├── __init__.py # Tool registrations loader
        ├── web.py      # Search web, fetch URL, get world news, open world monitor
        ├── system.py   # Get current time, get system info
        ├── utils.py    # Formatting JSON, word count helper
        ├── memory.py   # save_user_memory, list_user_memories, delete_user_memory
        └── systems.py  # open_application, search_local_files, get_active_processes, get_network_connections
```

---

## Quick Start

### 1. Prerequisites
*   Python ≥ 3.11
*   [`uv`](https://github.com/astral-sh/uv) (Python package runner)
*   Microsoft Edge (for the HUD display)

### 2. Launch F.R.I.D.A.Y.
Double-click or run the unified batch launcher:
```powershell
.\start.bat
```
This script will automatically:
1.  Fire up the **Friday MCP Tool Server** in a separate command window.
2.  Start the **Friday Web Client** server on `http://127.0.0.1:8050/`.
3.  Launch **Microsoft Edge** pointing directly to your HUD control interface.

---

## Configuration (`.env`)

Configure your API keys in the `.env` file at the project root:

```ini
# LLM Providers Configuration
OPENAI_API_KEY=your_openai_key
GROQ_API_KEY=your_groq_key
GOOGLE_API_KEY=your_gemini_key

# Default Brain Core Settings
LLM_PROVIDER=groq
STT_PROVIDER=whisper
TTS_PROVIDER=gemini-tts
```
