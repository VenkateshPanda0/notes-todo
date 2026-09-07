# Flow

**A fast, local-first workspace for Todos and Notes.**

Flow (branded **TaskFlow** in the UI) lets you capture anything — a task or
a thought — in one place. You explicitly choose Todo or Note; nothing is
auto-classified. Built with a React frontend and a FastAPI backend, and
packaged as a single standalone Windows desktop app with no external
dependencies at runtime.

---

## Features

### Todos and Notes
Every item you create is explicitly a **Todo** or a **Note** — Flow never
guesses. Each has a title and an optional description. Todos additionally
carry a **priority** (Low / Medium / High) and an optional **due date**;
Notes carry neither, since they're for capturing information rather than
tracking work.

### Todo ↔ Note conversion
Any item can switch type after creation — open it, toggle Todo/Note, save.
Useful when a note ("investigate X") turns into an actual task, or a task
gets demoted to a reference note.

### Complete / reopen
Todos can be checked off and unchecked at any time. Completed state
persists and is reflected across every view (Active/Completed filters,
the Completed sidebar page, and the Calendar).

### All Tasks
The main list — search, and filter by All / Active / Completed. This view
shows Todos only.

### Today / Upcoming
Automatically filtered views: **Today** shows Todos due on the current
date, **Upcoming** shows Todos due on any future date, both computed from
your local device time (not UTC), so they're correct regardless of time
zone.

### Completed
A dedicated view of every completed Todo, independent of the All Tasks
filter state.

### Notes
A separate section listing every item marked as a Note, kept out of the
Todo-oriented views so tasks and reference material don't mix.

### Calendar
A monthly grid view of all Todos with due dates. Each day cell shows up to
three tasks (color-coded by priority) with an overflow count for the rest.
Click a task to edit it; click empty space on a day to create a new task
pre-filled with that due date. Navigate months with prev/next, or jump
back to the current month with **Today**.

### Search
A live search box on the main list filters by title and description as
you type.

### App lock
An optional local password (PBKDF2-hashed, stored only on-device — no
accounts, no cloud). When set, the app shows a lock screen on every
launch until the correct password is entered. Since nothing here is
synced or sensitive beyond personal task data, this is a lightweight
local safeguard rather than full authentication.

### Light / Dark / System theme
Switchable in Settings, with System following your OS-level preference
automatically.

### Local-first storage
All data lives in a local SQLite database — nothing is sent to any
server. When packaged as the desktop `.exe`, the database lives at
`%APPDATA%\TaskFlow\flow.db`, independent of where the app itself is run
from, so your data survives moving or reinstalling the executable.

---

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

