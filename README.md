# TaskFlow

**A fast, local-first workspace for Todos and Notes.**

TaskFlow lets you capture anything — a task or a thought — in one place. You explicitly choose **Todo** or **Note**; nothing is automatically classified.

Built with **React + TypeScript**, **FastAPI**, **SQLAlchemy**, and **SQLite**, TaskFlow is packaged as a standalone Windows desktop application using **pywebview** and **PyInstaller**.

---

## Screenshots

### All Tasks

![All Tasks](docs/screenshots/all-tasks.png)

### Today

![Today](docs/screenshots/today.png)

### Upcoming

![Upcoming](docs/screenshots/upcoming.png)

### Completed

![Completed](docs/screenshots/completed.png)

### Calendar

![Calendar](docs/screenshots/calendar.png)

### Settings

![Settings](docs/screenshots/settings.png)

### App Lock

![App Lock](docs/screenshots/lock-screen.png)

---

## Features

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
└── docs/
    └── screenshots/
        ├── all-tasks.png
        ├── today.png
        ├── upcoming.png
        ├── completed.png
        ├── calendar.png
        ├── settings.png
        └── lock-screen.png
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
cd backend
python -m pytest tests -v
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

The optional App Lock stores the password as a **PBKDF2-derived hash** on the device rather than as plaintext.

> App Lock is intended as a lightweight local safeguard and should not be considered enterprise-grade authentication or encryption.

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

- [ ] Keyboard shortcuts
- [ ] Recurring Todos
- [ ] Todo tags / categories
- [ ] Database backup & restore
- [ ] Import / export
- [ ] Drag-and-drop organization
- [ ] Additional calendar interactions
- [ ] Automatic updates
- [ ] Signed Windows releases

---

## License

TaskFlow is licensed under the **MIT License**.

Copyright (c) 2026 Venkatesh Panda

See the [`LICENSE`](LICENSE) file for the complete license text.

---

## Author

**Venkatesh Panda**

GitHub: [VenkateshPanda0](https://github.com/VenkateshPanda0)