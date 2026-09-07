# Flow

### A fast, simple workspace for everything you need to remember.

Flow (branded **TaskFlow** in the UI) is a lightweight personal productivity
app that combines Todos and Notes into a single capture-first workspace.
Instead of separate apps for tasks and things you want to remember, Flow
gives you one place to write everything down — you decide what it is.

> **Write → Choose Todo or Note → Save → Organize**

---

## Current Status

> **Development Status: Frontend complete, packaging in progress**

### Implemented

- FastAPI backend with SQLite persistence (via SQLAlchemy)
- Unified `Item` model (Todo or Note), with priority, due dates, completion
- Full CRUD API: create, list (filterable), get, update, delete
- Todo completion / reopening
- Todo ↔ Note conversion
- Local app-password lock (PBKDF2-hashed, no accounts/OAuth — nothing
  sensitive is stored, so a simple local lock was chosen over full auth)
- React + TypeScript + Vite + Tailwind frontend
  - Dashboard with search, All/Active/Completed filters
  - Today / Upcoming / Completed / **Notes** sidebar views
  - **Calendar view** — monthly grid showing Todos by due date, click a day
    to add a task, click a task to edit it
  - Add/Edit task modal with Todo/Note toggle, priority, due date
  - Light / Dark / System theme
  - Settings — app lock setup, theme

### Coming Next

- PyInstaller packaging into a standalone Windows `.exe`
- Tags, sorting, global search across Notes
- Dashboard section polish

---

## Why Flow?

Most productivity apps force you to decide how to organize information
before you capture it. Flow keeps that decision explicit — there's no
automatic classification. You write something down, then choose Todo or
Note. The app doesn't guess.

---

## Architecture

```
┌──────────────────────────────────────────────┐
│                    Browser                   │
│            React + TypeScript                │
└──────────────────────┬───────────────────────┘
                       │ HTTP / JSON
                       ▼
┌──────────────────────────────────────────────┐
│                  FastAPI                     │
│  API Routes → Schemas → Services             │
└──────────────────────┬───────────────────────┘
                       ▼
┌──────────────────────────────────────────────┐
│                 SQLAlchemy                   │
└──────────────────────┬───────────────────────┘
                       ▼
┌──────────────────────────────────────────────┐
│                   SQLite                     │
└──────────────────────────────────────────────┘
```

## Technology Stack

| Layer    | Technology                                  |
| -------- | -------------------------------------------- |
| Backend  | Python, FastAPI, Pydantic, SQLAlchemy, SQLite, pytest |
| Frontend | React, TypeScript, Vite, Tailwind CSS        |
| Packaging| PyInstaller (bundles frontend + backend into one `.exe`) |

---

## Getting Started (development)

### Prerequisites

- Python 3.11+
- Node.js 18+
- Git

### Clone

```
git clone https://github.com/VenkateshPanda0/notes-todo.git
cd notes-todo
```

### Backend

```
python -m venv .venv
.venv\Scripts\activate          # Windows
python -m pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

Backend runs at `http://127.0.0.1:8000`.

### Frontend

In a separate terminal:

```
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173` and talks to the backend above.

### Tests

```
python -m pytest backend/tests
```

---

## Packaging into a Windows .exe

The goal: a single double-clickable `.exe` that runs the whole app (React
UI + FastAPI backend + SQLite) with no separate `npm`/`uvicorn` steps —
FastAPI serves the built React app directly, and PyInstaller bundles
everything, including the Python interpreter, into one executable.

### Step 1 — Build the React frontend to static files

```
cd frontend
npm run build
```

This produces `frontend/dist/` — plain HTML/CSS/JS, no dev server needed.

### Step 2 — Serve the built frontend from FastAPI

In `backend/app/main.py`, mount the built frontend as static files so
FastAPI serves both the API and the UI from one process:

```python
from fastapi.staticfiles import StaticFiles
import os

FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")

app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
```

Mount this **after** your `/api/...` routers are registered, so API routes
still take priority over the static file fallback.

### Step 3 — Write a launcher script

Create `backend/launcher.py`:

```python
import threading
import time
import webbrowser

import uvicorn

from app.main import app

def open_browser():
    time.sleep(1.5)  # give uvicorn a moment to start
    webbrowser.open("http://127.0.0.1:8000")

if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

This starts the server and opens the user's default browser to it —
no visible terminal workflow needed once packaged.

### Step 4 — Install PyInstaller

```
pip install pyinstaller
```

### Step 5 — Build the executable

From the `backend/` directory:

```
pyinstaller --name TaskFlow --onefile --add-data "../frontend/dist;frontend/dist" launcher.py
```

- `--onefile` bundles everything into a single `.exe`
- `--add-data "SRC;DEST"` bundles the built frontend files into the package
  (note the `;` separator — that's Windows-specific; use `:` on macOS/Linux)
- If you mounted `FRONTEND_DIST` with a relative path in Step 2, you'll
  need to adjust it to use `sys._MEIPASS` when running from a PyInstaller
  bundle, since bundled apps unpack to a temp folder at runtime:

```python
import sys
import os

if getattr(sys, "_MEIPASS", None):
    FRONTEND_DIST = os.path.join(sys._MEIPASS, "frontend", "dist")
else:
    FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
```

The output `.exe` lands in `backend/dist/TaskFlow.exe`.

### Step 6 — Test on a clean profile

Copy `TaskFlow.exe` somewhere outside your dev folder (e.g. Desktop) and
run it directly — this catches path assumptions that only work because
you're inside the project directory. Confirm:
- the browser opens automatically
- tasks/notes persist between runs (SQLite file location matters here —
  by default it may try to write next to the `.exe`; consider pointing it
  at a user-writable location like `%APPDATA%\TaskFlow\flow.db` instead)
- the app lock still works

### Known packaging gotchas

- **SQLite file path**: if your `DATABASE_URL` is a relative path, it'll
  resolve relative to wherever the `.exe` is run from — not the project
  folder. Pin it explicitly, ideally to `%APPDATA%`.
- **CORS**: once frontend and backend are served from the same origin
  (`127.0.0.1:8000` for both), you can drop the `localhost:5173` CORS
  exception used in development.
- **Antivirus false positives**: PyInstaller `--onefile` binaries are
  commonly flagged by Windows Defender/SmartScreen on first run since
  they're unsigned and self-extracting. This is expected for an unsigned
  student project `.exe` — not a sign something's broken.

---

## Development Workflow

Flow is built incrementally — one feature at a time, tested and committed.

```
Requirement → Design → Implementation → Tests → Review → Git Commit → Next Feature
```

---

## Non-Goals

Flow is not intended to become a full project-management platform, a team
collaboration tool, an AI assistant, or a calendar replacement (the
Calendar view here is for visualizing your own due dates, not external
calendar integration).

---

## License

MIT