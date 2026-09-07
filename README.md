# TaskFlow

**A fast, local-first workspace for Todos and Notes.**

TaskFlow lets you capture anything — a task or a thought — in one place. You explicitly choose **Todo** or **Note**; nothing is automatically classified.

Built with a React frontend and FastAPI backend, TaskFlow is designed as a local-first Windows desktop application with SQLite persistence and a native `pywebview` shell.

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

* A note such as `Investigate X` can become an actionable Todo.
* A Todo that no longer requires action can be converted into a reference Note.

### Complete / Reopen

Todos can be completed and reopened at any time.

Completion state persists and is reflected across the application's Todo views and calendar.

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

Date calculations use the device's local date and time rather than assuming UTC.

### Completed

A dedicated view containing completed Todos independently of the current filter state.

### Notes

A separate section containing all items explicitly marked as Notes.

Notes remain separate from Todo-oriented views so reference material and actionable work do not become mixed together.

### Calendar

A monthly calendar displaying Todos with due dates.

Each day can display up to three tasks directly in the calendar cell, with an overflow count for additional tasks.

Tasks are color-coded according to priority.

The calendar supports:

* Previous / next month navigation
* Returning to the current month
* Opening a Todo for editing
* Creating a Todo from an empty calendar day
* Automatically pre-filling the selected due date

### Search

The Todo list includes live search.

Search results update as you type and match against:

* Todo title
* Todo description

### App Lock

TaskFlow supports an optional local password.

The password is stored on-device as a PBKDF2-derived hash and is not sent to a remote service.

When enabled, TaskFlow displays a lock screen when the application launches.

The app lock is intended as a lightweight local safeguard rather than a full authentication or enterprise security mechanism.

### Light / Dark / System Theme

TaskFlow supports three appearance modes:

* **Light**
* **Dark**
* **System**

System mode follows the operating system's configured appearance preference.

### Local-First Storage

TaskFlow stores application data locally in SQLite.

Normal Todo and Note data is not sent to an external cloud service.

For packaged Windows builds, the database is stored at:

```text
%APPDATA%\TaskFlow\flow.db
```

The database is kept separately from the executable so application data can persist independently of the location of `TaskFlow.exe`.

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
│   │    API → Schemas → Services     │     │
│   └────────────────┬────────────────┘     │
│                    │                      │
│   ┌────────────────▼────────────────┐     │
│   │       SQLAlchemy → SQLite       │     │
│   │      %APPDATA%\TaskFlow\flow.db │     │
│   └─────────────────────────────────┘     │
│                                           │
└───────────────────────────────────────────┘
```

The application is organized into four primary layers:

1. **Native shell** — `pywebview` provides the desktop window.
2. **Frontend** — React + TypeScript provides the user interface.
3. **Backend** — FastAPI provides the application API and backend logic.
4. **Database** — SQLAlchemy provides the ORM layer over SQLite.

The desktop launcher starts the local backend and loads the compiled frontend into the native window.

---

## Technology Stack

| Layer           | Technology              |
| --------------- | ----------------------- |
| UI shell        | pywebview               |
| Desktop runtime | Microsoft Edge WebView2 |
| Frontend        | React                   |
| Language        | TypeScript              |
| Build tool      | Vite                    |
| Styling         | Tailwind CSS            |
| Backend         | FastAPI                 |
| Validation      | Pydantic                |
| ORM             | SQLAlchemy              |
| Storage         | SQLite                  |
| Packaging       | PyInstaller             |
| Target platform | Windows                 |

---

## Project Structure

```text
TaskFlow/
│
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py
│   │   │   ├── deps.py
│   │   │   └── items.py
│   │   │
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   └── session.py
│   │   │
│   │   ├── models/
│   │   │   ├── app_settings.py
│   │   │   └── item.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── auth.py
│   │   │   └── item.py
│   │   │
│   │   ├── services/
│   │   │   ├── auth.py
│   │   │   └── items.py
│   │   │
│   │   └── main.py
│   │
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth_api.py
│   │   ├── test_database.py
│   │   ├── test_health.py
│   │   └── test_items_api.py
│   │
│   ├── launcher.py
│   └── requirements.txt
│
└── frontend/
    ├── public/
    │   ├── favicon.svg
    │   └── icons.svg
    │
    ├── src/
    │   ├── api/
    │   │   └── client.ts
    │   │
    │   ├── components/
    │   │   ├── Button.tsx
    │   │   ├── Input.tsx
    │   │   ├── PriorityBadge.tsx
    │   │   ├── Sidebar.tsx
    │   │   ├── TaskModal.tsx
    │   │   └── TaskRow.tsx
    │   │
    │   ├── contexts/
    │   │   ├── LockContext.tsx
    │   │   └── ThemeContext.tsx
    │   │
    │   ├── pages/
    │   │   ├── CalendarView.tsx
    │   │   ├── Dashboard.tsx
    │   │   ├── LockScreen.tsx
    │   │   └── Settings.tsx
    │   │
    │   ├── types/
    │   │   └── item.ts
    │   │
    │   ├── App.tsx
    │   ├── index.css
    │   └── main.tsx
    │
    ├── index.html
    ├── package.json
    ├── package-lock.json
    ├── vite.config.ts
    └── tsconfig*.json
```

---

## Development Setup

### Prerequisites

For development, install:

* Python
* Node.js
* npm
* Git
* Microsoft Edge WebView2

The packaged Windows executable does not require Python or Node.js to be installed separately.

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

Create a Python virtual environment:

```bash
cd backend
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the FastAPI development server:

```bash
uvicorn app.main:app --reload
```

---

## Running Tests

The backend includes tests for API, authentication, database, health-check, and item functionality.

Run the complete backend test suite with:

```bash
cd backend
python -m pytest tests -v
```

---

## Building the Windows Executable

TaskFlow can be packaged into a standalone Windows executable using PyInstaller.

### 1. Build the frontend

From the repository root:

```bash
cd frontend
npm install
npm run build
cd ..
```

This generates the production frontend bundle in:

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

### 3. Build the executable

If an application icon is available:

```bash
pyinstaller --name TaskFlow --onefile --windowed --icon taskflow.ico --add-data "../frontend/dist;frontend/dist" launcher.py
```

Without an icon:

```bash
pyinstaller --name TaskFlow --onefile --windowed --add-data "../frontend/dist;frontend/dist" launcher.py
```

The resulting executable is created at:

```text
backend/dist/TaskFlow.exe
```

The packaged executable contains the application runtime, backend, and compiled frontend needed to launch TaskFlow as a desktop application.

---

## Application Data

TaskFlow keeps persistent application data outside the executable.

The SQLite database is stored at:

```text
%APPDATA%\TaskFlow\flow.db
```

This means the database is independent of the location of `TaskFlow.exe`.

For example:

```text
TaskFlow.exe
      │
      └── Application data
            └── %APPDATA%\TaskFlow\flow.db
```

Moving the executable does not by itself move the application database.

---

## First Run

Unsigned locally built Windows executables may trigger a Microsoft Defender SmartScreen warning.

You may see:

> Windows protected your PC

For an executable that you built and trust, Windows provides:

**More info → Run anyway**

Public releases should ideally be distributed with appropriate code signing.

---

## Privacy

TaskFlow is designed around local-first data storage.

Normal application data is stored in the local SQLite database rather than a hosted cloud database.

The application is designed to operate without:

* An online account
* A cloud database
* A separately hosted backend
* Internet connectivity for normal local operation

The local database remains on the user's machine.

---

## Design Philosophy

TaskFlow is intentionally designed around a small set of predictable interactions.

### Explicit over automatic

The user decides whether an item is a Todo or a Note.

TaskFlow does not automatically classify captured content.

### Local over cloud

The application prioritizes local persistence instead of requiring an online account or cloud synchronization service.

### Minimal over feature-heavy

The core workflow is:

```text
Capture → Organize → Act
```

TaskFlow focuses on this workflow without attempting to become a full project-management platform.

---

## Roadmap

Possible future improvements include:

* [ ] Keyboard shortcuts
* [ ] Recurring Todos
* [ ] Todo tags or categories
* [ ] Database backup and restore
* [ ] Import / export
* [ ] Drag-and-drop organization
* [ ] Additional calendar interactions
* [ ] Automatic application updates
* [ ] Signed Windows releases

The roadmap may change as the project evolves.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
