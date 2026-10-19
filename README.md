# TaskFlow

**A fast, local-first workspace for Todos and Notes.**

TaskFlow lets you capture anything — a task or a thought — in one place. You explicitly choose **Todo** or **Note**; nothing is automatically classified.

> **Your tasks and notes, entirely on your machine.** No account. No cloud. No tracking.

[Website](https://venkateshpanda0.github.io/notes-todo/) · [Download](https://github.com/VenkateshPanda0/notes-todo/releases) · [Contributing](CONTRIBUTING.md) · [Roadmap](#roadmap)

Built with **React + TypeScript**, **FastAPI**, **SQLAlchemy**, and **SQLite**, TaskFlow is packaged as a standalone Windows desktop application using **pywebview** and **PyInstaller**.

---

## Screenshots

### All Tasks

![All Tasks](screenshots/all-tasks.jpg)

### Quick Add

Type naturally and see how it's understood before you press Enter.

![Quick Add](screenshots/quick-add.png)

### Markdown Notes & Links

Write notes in Markdown, link them together with `[[Title]]`, and see what links back.

![Markdown notes with wiki-links](screenshots/notes-markdown.png)

![Backlinks](screenshots/backlinks.png)

### Graph View

See how everything connects. Notes and todos are nodes, `[[links]]` are edges.

![Graph view](screenshots/graph.png)

### Today

![Today](screenshots/today.jpg)

### Upcoming

![Upcoming](screenshots/upcoming.jpg)

### Completed

![Completed](screenshots/completed.jpg)

### Calendar

![Calendar](screenshots/calendar.jpg)

### Settings

![Settings](screenshots/settings.jpg)

### App Lock

![App Lock](screenshots/app-lock.jpg)
---

## Features

- **Quick Add** — type `call dentist next friday !high` and TaskFlow fills in the title, due date, and priority. See [Quick Add syntax](#quick-add-syntax).
- **Markdown notes** — headings, lists, code, tables and task lists, with a Write / Preview toggle. Output is sanitized, so pasted HTML can't run scripts.
- **Linked notes** — `[[Title]]` or `[[Title|label]]` links any note or todo to another. A **Linked from** panel shows backlinks, and clicking a link to a title that doesn't exist yet creates that note.
- **Graph view** — an interactive map of your links: hover to highlight neighbours, search to spotlight, drag to pin, scroll to zoom, click to open. Links to notes that don't exist yet appear as dashed placeholders you can click to create.
- **Tags** — add `#tags` to any item, then filter by tag with one click. Quick Add understands them too.
- **Keyboard shortcuts** — `/` focuses Quick Add, `n` opens the full task form, `Esc` closes it.
- **Todos & Notes** — explicitly choose the item type.
- **Title & Description** — optional descriptions for both.
- **Priority** — Low, Medium, or High for Todos.
- **Due Dates** — optional due dates for Todos.
- **Complete / Reopen** — completion state persists across views.
- **Todo ↔ Note Conversion** — change an item's type after creation.
- **All Tasks** — view, search, and filter All / Active / Completed Todos.
- **Today** — Todos due on the current local date.
- **Upcoming** — Todos due on future dates.
- **Completed** — dedicated completed-Todo view.
- **Notes** — separate view for reference material.
- **Calendar** — monthly Todo calendar with priority indicators and due-date creation.
- **Search** — live search across Todo titles and descriptions.
- **App Lock** — optional local password protected with PBKDF2 hashing.
- **Themes** — Light, Dark, and System modes.
- **Local-First Storage** — data is stored locally in SQLite.

Date filtering uses the device's **local date/time**, rather than UTC.

---

## Quick Add syntax

The Quick Add bar at the top of each view understands a small, predictable set of phrases. Anything it doesn't recognize stays in the title, and a live preview shows what will be created.

| Write this | You get |
| --- | --- |
| `today`, `tomorrow`, `tmr` | Due today / tomorrow |
| `friday`, `next friday`, `on friday` | Due the next Friday (never today) |
| `next week` | Due next Monday |
| `in 3 days`, `in 2 weeks` | Due that many days/weeks from now |
| `dec 25`, `25th of december`, `2026-12-25` | Due that date (rolls to next year if it has passed) |
| `!high`, `!med`, `!low` (or `!h`, `!m`, `!l`) | Priority |
| `#work`, `#ideas` | Tags (must start with a letter, so `#123` stays plain text) |
| `note: ...` | Creates a Note instead of a Todo (dates are left in the text) |

Example: `call dentist next friday !high #errands` → Todo "call dentist", due next Friday, High priority, tagged `errands`.

Short weekday forms that are also everyday words (`mon`, `wed`, `sat`, `sun`) are intentionally not recognized, so a title like "sat on the chair" is left alone.

---

## Architecture

```text
┌───────────────────────────────────────────┐
│               TaskFlow.exe                │
│                                           │
│   ┌─────────────────────────────────┐     │
│   │     pywebview — native window   │     │
│   └────────────────┬────────────────┘     │
│                    │ loads                │
│   ┌────────────────▼────────────────┐     │
│   │      React + TypeScript UI      │     │
│   └────────────────┬────────────────┘     │
│                    │ HTTP / JSON          │
│   ┌────────────────▼────────────────┐     │
│   │          FastAPI backend        │     │
│   │    API → Schemas → Services     │     │
│   └────────────────┬────────────────┘     │
│                    │                      │
│   ┌────────────────▼────────────────┐     │
│   │       SQLAlchemy → SQLite       │     │
│   │      %APPDATA%\TaskFlow\flow.db │     │
│   └─────────────────────────────────┘     │
└───────────────────────────────────────────┘
```

TaskFlow consists of four primary layers:

1. **Native Shell** — `pywebview`
2. **Frontend** — React + TypeScript
3. **Backend** — FastAPI
4. **Database** — SQLAlchemy + SQLite

The launcher starts the local backend and loads the compiled frontend into the native desktop window.

---

## Technology Stack

| Layer           | Technology              |
| --------------- | ------------------------ |
| UI Shell        | pywebview                |
| Desktop Runtime | Microsoft Edge WebView2  |
| Frontend        | React + TypeScript       |
| Build Tool      | Vite                     |
| Styling         | Tailwind CSS             |
| Backend         | FastAPI + Pydantic       |
| ORM             | SQLAlchemy               |
| Database        | SQLite                   |
| Packaging       | PyInstaller               |
| Platform        | Windows 10/11             |

---

## Project Structure

```text
TaskFlow/
├── LICENSE
├── README.md
├── CONTRIBUTING.md
├── .env.example
├── .gitignore
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py
│   │   │   ├── deps.py
│   │   │   └── items.py
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   └── session.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   │
│   ├── tests/
│   ├── launcher.py
│   └── requirements.txt
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── contexts/
│   │   ├── pages/
│   │   ├── types/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.ts
│   └── tsconfig*.json
│
├── screenshots/        # README images
└── docs/               # Landing page (GitHub Pages)
    ├── index.html
    └── assets/
```

---

## Development Setup

### Prerequisites

Install:

- Python 3.x
- Node.js + npm
- Git
- Microsoft Edge WebView2

Python and Node.js are required for development/building, but are not required on the target machine after the application has been packaged.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Backend

Open a second terminal:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

## Running Tests

The backend includes tests for API functionality, authentication, database behavior, health checks, and item operations.

```bash
# from the repository root
python -m pytest backend/tests -v
```

---

## Building the Windows `.exe`

TaskFlow can be packaged into a standalone Windows executable using **PyInstaller**.

### 1. Build the Frontend

From the repository root:

```bash
cd frontend
npm install
npm run build
cd ..
```

This creates the production frontend bundle:

```text
frontend/dist/
```

### 2. Set Up the Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Build TaskFlow

If `taskflow.ico` is available:

```bash
pyinstaller --name TaskFlow --onefile --windowed --icon taskflow.ico --add-data "../frontend/dist;frontend/dist" launcher.py
```

Without an icon:

```bash
pyinstaller --name TaskFlow --onefile --windowed --add-data "../frontend/dist;frontend/dist" launcher.py
```

The executable will be created at:

```text
backend/dist/TaskFlow.exe
```

The packaged application contains the Python runtime, backend, and compiled frontend. The end user does **not** need Python, Node.js, npm, or a separately running FastAPI server.

> **WebView2:** TaskFlow uses Microsoft Edge WebView2 through pywebview. The target Windows system must have a compatible WebView2 runtime available.

---

## Running the Built Application

After building:

```text
backend/dist/TaskFlow.exe
```

Double-click `TaskFlow.exe` to launch TaskFlow.

There is no separate server process to start.

---

## Application Data

TaskFlow stores persistent application data outside the executable:

```text
%APPDATA%\TaskFlow\flow.db
```

On a typical Windows installation:

```text
C:\Users\<username>\AppData\Roaming\TaskFlow\flow.db
```

The database is independent of the executable's location, so moving `TaskFlow.exe` does not move or delete the existing application data.

---

## First Run

Because locally built executables are not normally code-signed, Windows may display a **Microsoft Defender SmartScreen** warning.

If Windows displays:

```text
Windows protected your PC
```

and you trust the executable, select:

**More info → Run anyway**

For public production releases, appropriate Windows code signing is recommended.

---

## Privacy & Local-First Design

TaskFlow is designed to operate locally without:

- An online account
- A cloud database
- A hosted backend
- Internet connectivity for normal operation

Todo and Note data remains in the local SQLite database.

The optional App Lock stores the password as a **PBKDF2-derived hash** on the device rather than as plaintext. When a lock is set, the local API requires a short-lived, in-memory **session token** (issued on unlock, revoked on lock or password change), and repeated wrong passwords are temporarily blocked.

> **The database file itself is not encrypted yet.** App Lock keeps other apps and casual snoopers out of the running application, but anyone with access to your user account can still read `flow.db` directly. Encrypting the database is on the roadmap. Don't rely on App Lock for sensitive data until then.

---

## Design Philosophy

### Explicit over automatic

The user decides whether an item is a Todo or Note. TaskFlow does not automatically classify captured content.

### Local over cloud

Data is persisted locally instead of requiring an online account or cloud synchronization.

### Minimal over feature-heavy

The core workflow is:

```text
Capture → Organize → Act
```

TaskFlow focuses on this workflow rather than becoming a full project-management platform.

---

## Roadmap

**Next**
- [x] Enforced App Lock (session tokens, brute-force throttling)
- [ ] Encrypted database at rest
- [x] Quick Add with natural-language dates and priority
- [ ] Global capture hotkey (works while TaskFlow is in the background)
- [ ] Database backup & restore, import / export
- [x] Basic keyboard shortcuts (`/`, `n`, `Esc`); more to come

**Soon**
- [x] Markdown notes, tags, and note ↔ todo links with backlinks
- [x] Interactive graph view of linked notes
- [ ] Recurring Todos and desktop reminders
- [x] Versioned database migrations (existing databases upgrade in place)

**Later**
- [ ] macOS and Linux builds
- [ ] On-device AI (summaries, semantic search) — local only
- [ ] Optional end-to-end encrypted sync
- [ ] Automatic updates and signed Windows releases

Have an idea? [Open an issue](https://github.com/VenkateshPanda0/notes-todo/issues/new/choose). See [CONTRIBUTING.md](CONTRIBUTING.md) to get started.

---

## License

TaskFlow is licensed under the **MIT License**.

Copyright (c) 2026 Venkatesh Panda

See the [`LICENSE`](LICENSE) file for the complete license text.

---

## Author

**Venkatesh Panda**

GitHub: [VenkateshPanda0](https://github.com/VenkateshPanda0)
