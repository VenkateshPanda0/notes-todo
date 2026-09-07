# Flow

**A fast, local-first workspace for Todos and Notes.**

Flow (branded **TaskFlow** in the UI) lets you capture anything — a task or
a thought — in one place. You explicitly choose Todo or Note; nothing is
auto-classified. Built with a React frontend and a FastAPI backend, and
packaged as a single standalone Windows desktop app with no external
dependencies at runtime.

---

## Architecture

```
┌───────────────────────────────────────────┐
│              TaskFlow.exe                 │
│                                            │
│   ┌─────────────────────────────────┐     │
│   │   pywebview — native window     │     │
│   │   (no browser chrome)           │     │
│   └────────────────┬────────────────┘     │
│                     │ loads               │
│   ┌─────────────────▼────────────────┐    │
│   │     React + TypeScript UI        │    │
│   │     (built, static, bundled)     │    │
│   └────────────────┬──────────────────┘   │
│                     │ HTTP / JSON          │
│   ┌─────────────────▼──────────────────┐  │
│   │           FastAPI backend          │  │
│   │   Routes → Schemas → Services      │  │
│   └────────────────┬──────────────────┘   │
│                     │                      │
│   ┌─────────────────▼──────────────────┐  │
│   │     SQLAlchemy → SQLite            │  │
│   │  %APPDATA%\TaskFlow\flow.db        │  │
│   └─────────────────────────────────────┘ │
└───────────────────────────────────────────┘
```

Everything — Python runtime, backend, and the built frontend — is bundled
into one `.exe` via PyInstaller. There is no separate server process or
install step for the person running it: double-click, and it opens as a
native window with data persisted between runs.

| Layer      | Technology                                  |
| ---------- | -------------------------------------------- |
| UI shell   | pywebview (native window, Edge WebView2)     |
| Frontend   | React, TypeScript, Vite, Tailwind CSS         |
| Backend    | FastAPI, Pydantic, SQLAlchemy                 |
| Storage    | SQLite (`%APPDATA%\TaskFlow\flow.db`)         |
| Packaging  | PyInstaller (`--onefile`)                    |

---

## Building the .exe

Run these from the repo root, in order.

```bash
# 1. Build the frontend into static files
cd frontend
npm install
npm run build
cd ..

# 2. Install backend + packaging dependencies
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 3. Build the standalone executable
pyinstaller --name TaskFlow --onefile --windowed --icon taskflow.ico --add-data "../frontend/dist;frontend/dist" launcher.py
```

The finished app is at `backend/dist/TaskFlow.exe` — fully self-contained,
runs on any Windows 10/11 machine with no Python or Node install required.

> `--icon taskflow.ico` is optional — omit it if you haven't made an icon
> file yet. `--windowed` suppresses the console window, since the app runs
> inside its own pywebview window.

### First run

Windows SmartScreen may flag the `.exe` as unrecognized since it isn't
code-signed — this is expected for an unsigned build. Click **More info →
Run anyway**.
