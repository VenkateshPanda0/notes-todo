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

### Command Palette

Press **Ctrl/⌘ + K** anywhere to jump to a page, find any note or todo, or capture a task in one line.

![Command palette](screenshots/command-palette.png)

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

### Local AI (optional)

Summaries, a daily plan and related-note suggestions, running on your own computer through Ollama.

![AI assistant in a note](screenshots/ai-assistant.png)

![Local AI settings](screenshots/ai-settings.png)

![Ask your notes](screenshots/ask-your-notes.png)

### Backup & Export

![Backup and export](screenshots/backup.png)

### Recurring todos

![Repeat settings](screenshots/recurring.png)

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

### Encrypted Unlock

When the database is encrypted, nothing is readable until the password is entered.

![Encrypted unlock](screenshots/encrypted-unlock.png)

### App Lock

![App Lock](screenshots/app-lock.jpg)
---

## Features

- **Quick Add** — type `call dentist next friday !high` and TaskFlow fills in the title, due date, and priority. See [Quick Add syntax](#quick-add-syntax).
- **Markdown notes** — headings, lists, code, tables and task lists, with a Write / Preview toggle. Output is sanitized, so pasted HTML can't run scripts.
- **Linked notes** — `[[Title]]` or `[[Title|label]]` links any note or todo to another. A **Linked from** panel shows backlinks, and clicking a link to a title that doesn't exist yet creates that note.
- **Graph view** — an interactive map of your links: hover to highlight neighbours, search to spotlight, drag to pin, scroll to zoom, click to open. Links to notes that don't exist yet appear as dashed placeholders you can click to create.
- **Local AI (optional, off by default)** — summarize a note, **ask questions about your own notes** (answers cite their sources), get a short **Plan my day** from overdue and due-soon todos, and find **related notes** by meaning. Runs on your computer through [Ollama](https://ollama.com); see [Local AI](#local-ai).
- **Tags** — add `#tags` to any item, then filter by tag with one click. Quick Add understands them too.
- **Command palette** — `Ctrl/⌘ + K` from anywhere: jump to any page, search every note and todo (titles and text), or type a task to add with the same natural-language parsing as Quick Add. Choose **Keyboard shortcuts** in it for the full list.
- **Keyboard shortcuts** — `Ctrl/⌘ + K` palette, `/` focuses Quick Add, `n` opens the full task form, `Esc` closes dialogs.
- **Todos & Notes** — explicitly choose the item type.
- **Title & Description** — optional descriptions for both.
- **Priority** — Low, Medium, or High for Todos.
- **Due Dates** — optional due dates for Todos.
- **Recurring todos** — repeat daily, every weekday, weekly, monthly, yearly or every N days/weeks/months/years. Completing a repeating todo creates the next one (month-end dates don't drift, and an overdue series catches up instead of piling up overdue copies).
- **Trash with Undo** — deleting moves an item to the Trash for 30 days; click **Undo** right after, or Restore / Delete forever from the Trash page. Trashed items stay out of search, the graph, AI answers and exports.
- **Complete / Reopen** — completion state persists across views.
- **Todo ↔ Note Conversion** — change an item's type after creation.
- **All Tasks** — view, search, and filter All / Active / Completed Todos.
- **Today** — what needs attention now: overdue todos (most overdue first) and todos due today, with a live count badge in the sidebar.
- **Upcoming** — Todos due on future dates.
- **Completed** — dedicated completed-Todo view.
- **Notes** — separate view for reference material.
- **Calendar** — monthly Todo calendar with priority indicators and due-date creation.
- **Search** — live search across Todo titles and descriptions.
- **App Lock & database encryption** — an optional password (PBKDF2-hashed) locks the app, and you can additionally **encrypt the data file itself** with it (AES-256 via SQLCipher). See [Privacy](#privacy--local-first-design).
- **Accessible** — fully keyboard-operable (skip link, focus-trapped dialogs that return focus, keyboard Calendar and Graph), labelled form fields and WCAG AA text contrast in both themes, checked with axe-core.
- **Themes** — Light, Dark, and System modes.
- **Backup, export & import** — automatic daily snapshots, plus export to JSON, to Markdown (one file per item, works with Obsidian), or as a database copy. Import from JSON or a zip of Markdown files. See [Backups](#backups-and-export).
- **Local-First Storage** — data is stored locally in SQLite.

Date filtering uses the device's **local date/time**, rather than UTC (and the Today badge stays right when the date rolls over while the app is open).

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
| `every day`, `every 3 days`, `every other week`, `every weekday`, `every monday`, `every month`, `every year` (or `daily` / `weekly` / `monthly` / `yearly` at the end) | Repeats; a todo with no date starts today (`every monday` starts on the next Monday) |
| `note: ...` | Creates a Note instead of a Todo (dates are left in the text) |

Example: `call dentist next friday !high #errands` → Todo "call dentist", due next Friday, High priority, tagged `errands`.

Words like "weekly report" or "monthly budget review" stay as titles: a bare `weekly`/`monthly` only counts as a repeat when it ends the text ("call mom weekly"), and notes never repeat.

Short weekday forms that are also everyday words (`mon`, `wed`, `sat`, `sun`) are intentionally not recognized, so a title like "sat on the chair" is left alone.

---

## Backups and export

Your data is one SQLite file, so TaskFlow makes it easy to keep copies and to leave with your data.

- **Automatic backups:** a snapshot is saved the first time you use TaskFlow each day, in a `backups` folder next to the database (`%APPDATA%\TaskFlow\backups` on Windows). The newest 7 are kept. Snapshots are taken with SQLite's online backup, so they are consistent even while the app is running. Restore one by replacing `flow.db` with it while TaskFlow is closed.
- **Export (Settings → Backup & export):**
  - **JSON**: everything, in a versioned file that TaskFlow can re-import.
  - **Markdown (.zip)**: one `.md` file per item in `Notes/` and `Todos/`, with YAML front matter (title, type, tags, priority, due date, completion). `[[links]]` are kept as they are, so it opens in Obsidian and similar tools.
  - **Database copy**: a consistent copy of the SQLite file.
- **Import:** a TaskFlow JSON export, or a zip of Markdown files (Obsidian-style front matter such as `tags: [a, b]` is understood; files without front matter become notes titled after the file).
  - **Merge** (default) adds what's missing and skips items that already exist, so importing the same file twice is harmless.
  - **Replace** swaps everything. TaskFlow saves a `before-import-…` safety copy first (the newest 3 are kept) and makes the change in a single transaction, so a failed import leaves your data untouched.

---

## Local AI

TaskFlow can use a model running on **your own computer** through [Ollama](https://ollama.com). It is **off by default** and nothing is sent to any cloud service.

**Set up**

1. Install Ollama and start it.
2. Pull a chat model and an embedding model:

   ```bash
   ollama pull llama3.2
   ollama pull nomic-embed-text
   ```

3. In TaskFlow open **Settings → Local AI** and tick **Enable local AI features**. Pick models there if you have several installed.

**What it does**

| Feature | Where | What happens |
| --- | --- | --- |
| **Summarize** | Open any note or todo | A short bullet summary appears. **Add to note** inserts it into the editor; nothing is saved until you save. |
| **Find related** | Open any note or todo | Items closest in meaning, using embeddings that are cached locally and only recomputed for notes you change. |
| **Ask your notes** | Sidebar → Ask your notes | Ask a question and get an answer built **only** from your own notes and todos, with numbered citations you can click to check the source. |
| **Plan my day** | All Tasks / Today | A short plan built from overdue, due-soon (next 3 days) and high-priority todos. |

**Privacy and safety**

- Requests go only to the Ollama server on this machine (`127.0.0.1:11434`). Settings shows a warning if Ollama is configured to be anywhere else (`TASKFLOW_OLLAMA_URL`).
- With AI turned off, the app never contacts Ollama to generate anything.
- Questions are answered only from the notes retrieved for that question, and the answer shows which ones were used. The conversation is not stored anywhere.
- The model only produces text for you to read. It cannot change, delete or create your data, and note contents are sent as data (not instructions), so text hidden in a note cannot make the AI do anything.
- Small local models can be wrong or miss things. Treat summaries and plans as suggestions.

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
│   ├── taskflow.ico
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
├── .github/workflows/  # CI and the release pipeline
├── scripts/            # Asset generation (icon, social preview)
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

```bash
# Backend (from the repository root)
python -m pytest backend/tests -v

# Frontend
cd frontend
npm test
```

The backend suite covers the API, migrations, backups, the launcher and the AI features (against a fake model). The frontend suite (Vitest + Testing Library) covers the Markdown/sanitizing pipeline, date logic and key components.

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

From the `backend` folder:

```bash
pyinstaller --noconfirm --clean --name TaskFlow --onefile --windowed --icon taskflow.ico --add-data "../frontend/dist;frontend/dist" launcher.py
```

The executable will be created at:

```text
backend/dist/TaskFlow.exe
```

The packaged application contains the Python runtime, backend, and compiled frontend. The end user does **not** need Python, Node.js, npm, or a separately running FastAPI server.

The app starts its local server on a **free port chosen at launch** (localhost only), so it never clashes with other software, and the window opens only once the server is ready.

> **WebView2:** TaskFlow uses Microsoft Edge WebView2 through pywebview. The target Windows system must have a compatible WebView2 runtime available (it is included with current Windows 10/11).

### 4. Verify the build (optional)

`TaskFlow.exe --smoke-test --report smoke.txt` starts the bundled server, exercises the API and database, checks that the UI and pywebview were packaged, writes the result to `smoke.txt`, and exits with code `0` on success. The release pipeline runs this on every build.

### Automated releases

Maintainers don't need to build by hand. Pushing a version tag builds the exe on Windows, smoke-tests it, and publishes a GitHub Release with a checksum:

```bash
git tag v0.1.0
git push origin v0.1.0
```

See [CONTRIBUTING.md](CONTRIBUTING.md#releasing) for details, including how to do a dry run.

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

The optional **App Lock** stores the password as a **PBKDF2-derived hash** on the device rather than as plaintext. When a lock is set, the local API requires a short-lived, in-memory **session token** (issued on unlock, revoked on lock or password change), and repeated wrong passwords are temporarily blocked.

### Database encryption (optional)

By default the SQLite file is a normal file: the App Lock keeps people out of the running application, but anyone with access to your user account can read `flow.db` directly. Turn on **Settings → App Lock → Database encryption** to encrypt the file itself with your app password (AES-256, via [SQLCipher](https://www.zetetic.net/sqlcipher/)).

What it does:

- The data file (and every backup made afterwards) is unreadable without the password: no notes, titles, tags or settings are visible in the file.
- The app starts **locked**; the password is what opens the database. **Lock now** closes it again and forgets the key.
- Enabling is safe: TaskFlow builds an encrypted copy, verifies it (integrity check, same tables, same row counts, same schema version), then swaps it in. The plain original is kept until the result is proven, and a crash at any point is repaired on the next start. Older *unencrypted* backups are securely deleted and replaced with an encrypted one.
- Changing your password re-encrypts the file and your backups. You can remove encryption again at any time.

What it does **not** do, so you can judge it honestly:

- **A forgotten password cannot be recovered.** There is no reset and no back door. Export a copy first if in doubt.
- While TaskFlow is unlocked, the key and your decrypted data are in memory; it protects data **at rest** (a copied or stolen file), not a compromised running computer.
- **Exports** (JSON, Markdown, "database copy" of a plain database) are plain files by design. Keep them somewhere safe.
- Deleting old plain files is best effort: SSD wear levelling and file-system journals can retain old blocks.
- It is opt-in. Builds without SQLCipher still work, but cannot encrypt.

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
- [x] Encrypted database at rest (optional, AES-256 via SQLCipher)
- [x] Quick Add with natural-language dates and priority
- [ ] Global capture hotkey (works while TaskFlow is in the background)
- [ ] Database backup & restore, import / export
- [x] Basic keyboard shortcuts (`/`, `n`, `Esc`); more to come

**Soon**
- [x] Markdown notes, tags, and note ↔ todo links with backlinks
- [x] Interactive graph view of linked notes
- [x] Recurring todos
- [x] Trash with restore and undo
- [ ] Desktop reminders
- [x] Versioned database migrations (existing databases upgrade in place)

**Later**
- [ ] macOS and Linux builds
- [x] On-device AI: summaries, daily plan and related notes (local, opt-in)
- [x] Ask your notes: answers grounded in your own notes, with citations
- [ ] Use embeddings to suggest `[[links]]` and tags while you write
- [ ] Optional end-to-end encrypted sync
- [x] Automated Windows releases (built, smoke-tested and published from a version tag)
- [ ] Automatic updates and code-signed releases

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
