# TaskFlow

**A fast, local-first workspace for Todos and Notes.**

TaskFlow lets you capture anything — a task or a thought — in one place. You explicitly choose **Todo** or **Note**; nothing is automatically classified.

Built with a React frontend and FastAPI backend, TaskFlow is packaged as a standalone Windows desktop application with local SQLite storage and no separate runtime installation required.

---

## Features

### Todos and Notes

Every item you create is explicitly a **Todo** or a **Note** — TaskFlow never guesses.

Both types support:

* Title
* Optional description

Todos additionally support:

* Priority: **Low / Medium / High**
* Optional due date
* Completion status

Notes do not have priority, due dates, or completion state because they are intended for capturing information rather than tracking work.

### Todo ↔ Note Conversion

Any item can switch between Todo and Note after creation.

For example:

* A note such as "Investigate X" can become an actionable Todo.
* A Todo that no longer requires action can be converted into a reference Note.

### Complete / Reopen

Todos can be completed and reopened at any time.

Completion state persists across the application and is reflected in:

* Active / Completed filters
* Completed view
* Calendar
* Todo lists

### All Tasks

The main Todo view provides:

* All Todos
* Active Todos
* Completed Todos
* Search
* Filtering

This view contains Todos only.

### Today / Upcoming

TaskFlow provides automatically filtered Todo views:

* **Today** — Todos due on the current local date
* **Upcoming** — Todos due on future dates

Date calculations use the device's **local time**, rather than UTC.

### Completed

A dedicated view containing completed Todos independently of the current filter state in the main Todo list.

### Notes

A separate section containing all items explicitly marked as Notes.

Notes remain separate from Todo-oriented views so reference material and actionable work do not become mixed together.

### Calendar

A monthly calendar displaying Todos with due dates.

Each day can display up to three tasks directly in the calendar cell, with an overflow count for additional tasks.

Tasks are color-coded according to priority.

The calendar supports:

* Previous / next month navigation
* Return to the current month
* Click a Todo to edit it
* Click an empty day to create a Todo
* Automatically pre-fill the selected date when creating a Todo

### Search

The Todo list includes live search.

Search results are updated as you type and match against:

* Todo title
* Todo description

### App Lock

TaskFlow supports an optional local password.

The password is:

* Stored only on the device
* Stored as a PBKDF2-derived hash
* Not transmitted to a server
* Not associated with an online account

When enabled, TaskFlow displays a lock screen when the application launches.

This is intended as a lightweight local safeguard rather than a full authentication or enterprise security system.

### Light / Dark / System Theme

TaskFlow supports three appearance modes:

* **Light**
* **Dark**
* **System**

System mode automatically follows the operating system's configured appearance preference.

### Local-First Storage

All application data is stored locally in SQLite.

No Todo or Note data is sent to an external server.

When packaged as a Windows executable, the database is stored at:

```text
%APPDATA%\TaskFlow\flow.db
```

The database is independent of the executable's location, allowing data to persist when the executable is moved or replaced.

---

## Architecture

```text
┌───────────────────────────────────────────┐
│               TaskFlow.exe                │
│                                           │
│   ┌─────────────────────────────────┐     │
│   │     pywebview — native window   │     │
│   │       (no browser chrome)        │     │
│   └────────────────┬────────────────┘     │
│                    │ loads                │
│   ┌────────────────▼────────────────┐     │
│   │      React + TypeScript UI      │     │
│   │        (built, static)          │     │
│   └────────────────┬────────────────┘     │
│                    │ HTTP / JSON          │
│   ┌────────────────▼────────────────┐     │
│   │          FastAPI backend        │     │
│   │    Routes → Schemas → Services  │     │
│   └────────────────┬────────────────┘     │
│                    │                      │
│   ┌────────────────▼────────────────┐     │
│   │       SQLAlchemy → SQLite       │     │
│   │      %APPDATA%\TaskFlow\flow.db │     │
│   └─────────────────────────────────┘     │
│                                           │
└───────────────────────────────────────────┘
```

The application consists of four primary layers:

1. **Native shell** — pywebview provides the desktop application window.
2. **Frontend** — React + TypeScript provides the user interface.
3. **Backend** — FastAPI handles application logic and the REST API.
4. **Database** — SQLAlchemy communicates with the local SQLite database.

The production application bundles the Python runtime, backend, and compiled frontend into a single Windows executable using PyInstaller.

There is no separate server process for the end user. Launching `TaskFlow.exe` starts the application and opens the native desktop window.

---

## Technology Stack

| Layer                | Technology              |
| -------------------- | ----------------------- |
| UI shell             | pywebview               |
| Desktop runtime      | Microsoft Edge WebView2 |
| Frontend             | React                   |
| Language             | TypeScript              |
| Build tool           | Vite                    |
| Styling              | Tailwind CSS            |
| Backend              | FastAPI                 |
| API validation       | Pydantic                |
| ORM / database layer | SQLAlchemy              |
| Database             | SQLite                  |
| Packaging            | PyInstaller             |
| Platform             | Windows 10 / 11         |

---

## Project Structure

```text
TaskFlow/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── types/
│   ├── package.json
│   └── vite.config.ts
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── models/
│   │   └── db/
│   ├── tests/
│   ├── launcher.py
│   └── requirements.txt
│
├── docs/
├── LICENSE
└── README.md
```

---

## Development Setup

### Prerequisites

For development, install:

* Python 3.10+
* Node.js
* npm
* Git
* Microsoft Edge WebView2

The packaged application does not require Python or Node.js to be installed separately.

---

### Frontend

From the repository root:

```bash
cd frontend
npm install
npm run dev
```

This starts the Vite development server.

---

### Backend

Create and activate a Python virtual environment:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
```

Install the backend dependencies:

```bash
pip install -r requirements.txt
```

Start the FastAPI development server:

```bash
uvicorn app.main:app --reload
```

---

## Running Tests

Run the backend test suite with:

```bash
cd backend
python -m pytest tests -v
```

The test suite covers the application's backend behavior, including API and database functionality.

---

## Building the Windows Executable

The production executable is created using **PyInstaller**.

Run the following commands from the repository root.

### 1. Build the frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

This creates the production frontend bundle in:

```text
frontend/dist/
```

### 2. Prepare the backend environment

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Build TaskFlow.exe

If an application icon is available:

```bash
pyinstaller --name TaskFlow --onefile --windowed --icon taskflow.ico --add-data "../frontend/dist;frontend/dist" launcher.py
```

If no icon is available:

```bash
pyinstaller --name TaskFlow --onefile --windowed --add-data "../frontend/dist;frontend/dist" launcher.py
```

The resulting executable will be located at:

```text
backend/dist/TaskFlow.exe
```

The packaged application contains:

* Python runtime
* FastAPI backend
* Backend dependencies
* Built React frontend
* Application launcher

The end user does not need to install Python or Node.js separately.

---

## Application Data

TaskFlow stores persistent application data in:

```text
%APPDATA%\TaskFlow\flow.db
```

This location is intentionally separate from the executable.

Therefore:

```text
TaskFlow.exe
     │
     └── Application data
          └── %APPDATA%\TaskFlow\flow.db
```

Moving the executable does not move or delete the database.

---

## First Run

Because locally built TaskFlow executables are not code-signed, Windows SmartScreen may display a warning when the application is launched.

Windows may display:

> Windows protected your PC

If you trust the executable you built, select:

**More info → Run anyway**

A production release distributed publicly should ideally use a properly configured code-signing certificate.

---

## Privacy

TaskFlow follows a local-first architecture.

Normal application data is stored locally in SQLite rather than being sent to a remote service.

The application does not require:

* An online account
* A cloud database
* A hosted backend
* Internet connectivity for normal local operation

Todos, Notes, and application state remain on the local machine.

---

## Design Philosophy

TaskFlow intentionally keeps its interaction model simple.

### Explicit over automatic

The user decides whether something is a Todo or a Note.

TaskFlow does not attempt to infer intent using:

* AI classification
* Natural-language classification
* Automatic categorization

### Local over cloud

The application is designed around local persistence rather than mandatory cloud synchronization.

### Minimal over feature-heavy

TaskFlow focuses on the core workflow:

```text
Capture → Organize → Act
```

without requiring a large project-management system.

---

## Roadmap

Potential future improvements may include:

* [ ] Keyboard shortcuts
* [ ] Drag-and-drop Todo organization
* [ ] Recurring Todos
* [ ] Todo categories / tags
* [ ] Database backup and restore
* [ ] Import / export
* [ ] Improved calendar interactions
* [ ] Application update mechanism
* [ ] Signed Windows releases

The roadmap is subject to change as the project evolves.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
