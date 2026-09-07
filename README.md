# Flow

### A fast, simple workspace for everything you need to remember.

Flow is a lightweight personal productivity application that combines **Todos and Notes into a single capture-first workspace**.

Instead of maintaining separate apps for things you need to do and things you simply want to remember, Flow gives you one place to write everything down.

You decide what it is.

> **Write → Choose Todo or Note → Save → Organize**

Flow intentionally keeps this decision explicit. The application does **not** attempt to guess whether something is a task or a note.

---

## Current Status

> **Development Status: Milestone 1 — Foundation**

The project is currently establishing its backend architecture and development workflow.

### Implemented

* FastAPI backend
* Health-check endpoint
* Backend test structure
* Project documentation
* Python dependency management
* Initial repository structure

### Coming Next

* SQLite database
* SQLAlchemy integration
* Unified `Item` model
* Todo creation and management
* Note creation and management
* React + TypeScript frontend
* Search and filtering
* Priorities and due dates
* Todo ↔ Note conversion

---

# Why Flow?

Most productivity applications force you to decide how to organize information before you capture it.

Flow is designed around a simpler interaction:

```text
                 ┌─────────────────┐
                 │  I need to      │
                 │  write something │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │  Capture it     │
                 └────────┬────────┘
                          │
                    ┌─────┴─────┐
                    ▼           ▼
                 TODO          NOTE
                    │           │
                    └─────┬─────┘
                          ▼
                    Flow Workspace
```

There is no automatic classification in the core application.

If you write:

> Finish DBMS Lab 4 tomorrow

you can explicitly select **Todo**.

If you write:

> Idea: investigate memory-based malware detection for UAV companion computers

you can explicitly select **Note**.

The application handles the organization. **You control the meaning.**

---

# Core Concept

Flow revolves around a single concept:

## Items

Everything captured by the user is an `Item`.

An item has a type:

```text
TODO
NOTE
```

Conceptually:

```text
Item
├── id
├── title
├── content
├── type
├── completed
├── priority
├── due_date
├── created_at
└── updated_at
```

The initial implementation intentionally starts with a smaller data model and expands it incrementally.

---

# Planned Features

## Todo Management

Create and manage tasks from the same capture interface.

Planned functionality:

* Create Todo
* Edit Todo
* Delete Todo
* Complete Todo
* Reopen Todo
* Priorities
* Due dates
* Tags
* Filtering

Example:

```text
☐ Finish DBMS Lab 4

Priority: High
Due: Tomorrow
Tag: University
```

---

## Notes

Keep information, ideas, references, research, and thoughts without treating them as tasks.

Example:

```text
UAV Malware Research

Investigate whether memory-based behavioral detection
could identify malicious activity on UAV companion computers.
```

Planned functionality:

* Create Note
* Edit Note
* Delete Note
* Search Notes
* Tags
* Timestamps

---

## Todo ↔ Note Conversion

An item should not be permanently locked into one type.

A Note can become a Todo:

```text
NOTE

Research PostgreSQL indexing
        ↓
[ Convert to Todo ]
        ↓
TODO

☐ Research PostgreSQL indexing
```

Likewise, a Todo can become a Note.

This keeps the workspace flexible as priorities change.

---

## Search

Flow will eventually provide a unified search across:

* Todos
* Notes
* Tags
* Content
* Titles

For example:

```text
Search: postgres
```

could return:

```text
TODO
☐ Review PostgreSQL indexing

NOTE
PostgreSQL MVCC Notes

TODO
Build PostgreSQL test database
```

The initial search implementation will use conventional database/text search.

---

## Filtering

Planned filters include:

```text
All
Todos
Notes
Pending
Completed
```

Additional filters can include:

* Priority
* Tags
* Due date
* Creation date

---

# Product Principles

Flow is intentionally built around a few principles.

### 1. Capture First

Writing something down should require minimal interaction.

### 2. Explicit Classification

The user decides whether something is a Todo or Note.

The initial version does not use AI to make this decision.

### 3. Minimal Interface

The application should remain focused on capturing and organizing information rather than becoming an overloaded productivity suite.

### 4. Local First

The initial version is designed to work locally with a lightweight SQLite database.

The architecture will allow PostgreSQL and cloud synchronization to be introduced later.

### 5. Incremental Engineering

Flow is being developed feature-by-feature rather than generated as one large application.

Each major feature should be independently implemented, tested, reviewed, and committed.

---

# Architecture

The planned architecture separates the frontend, API, business logic, and persistence layers.

```text
┌──────────────────────────────────────────────┐
│                    Browser                   │
│                                              │
│            React + TypeScript                │
└──────────────────────┬───────────────────────┘
                       │
                       │ HTTP / JSON
                       ▼
┌──────────────────────────────────────────────┐
│                  FastAPI                     │
│                                              │
│  API Routes → Schemas → Services             │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│                 SQLAlchemy                   │
│                                              │
│                 Data Layer                   │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│                   SQLite                     │
│                                              │
│              Local Persistence               │
└──────────────────────────────────────────────┘
```

The frontend communicates with the backend through the API rather than accessing the database directly.

This keeps the system modular and makes future changes to the persistence layer easier.

---

# Technology Stack

## Backend

| Technology | Purpose               |
| ---------- | --------------------- |
| Python     | Backend language      |
| FastAPI    | REST API framework    |
| Pydantic   | Data validation       |
| SQLAlchemy | ORM / database access |
| SQLite     | Initial database      |
| pytest     | Backend testing       |

## Frontend

| Technology   | Purpose                        |
| ------------ | ------------------------------ |
| React        | UI framework                   |
| TypeScript   | Type-safe frontend development |
| Vite         | Frontend build tooling         |
| Tailwind CSS | UI styling                     |
| Vitest       | Frontend testing               |

The frontend stack will be introduced in a later milestone.

---

# Repository Structure

Current repository:

```text
flow/
│
├── backend/
│   ├── app/
│   │   └── main.py
│   │
│   ├── tests/
│   │
│   └── requirements.txt
│
├── frontend/
│   └── ...
│
├── .gitignore
└── README.md
```

As the application develops, the structure is expected to evolve toward:

```text
flow/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   │
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── types/
│   │   └── utils/
│   │
│   ├── package.json
│   └── ...
│
├── .gitignore
└── README.md
```

The architecture will evolve as functionality is introduced rather than being over-engineered from the beginning.

---

# Getting Started

## Prerequisites

* Python 3.11+
* Git

Node.js will be required once the React frontend is introduced.

---

## Clone the Repository

```bash
git clone <repository-url>
cd flow
```

---

## Backend Setup

Create a virtual environment:

```bash
python -m venv .venv
```

### Windows

```bash
.venv\Scripts\activate
```

### Linux / macOS

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r backend/requirements.txt
```

---

# Run the Backend

Start the FastAPI development server:

```bash
uvicorn app.main:app --app-dir backend --reload
```

The server will be available at:

```text
http://127.0.0.1:8000
```

---

# API

## Health Check

### `GET /health`

Returns the current health status of the backend.

Example response:

```json
{
  "status": "ok"
}
```

The health endpoint is intentionally minimal in Milestone 1.

Additional API endpoints will be introduced as application functionality is implemented.

---

# Testing

Run the backend test suite:

```bash
python -m pytest backend/tests
```

Tests are developed alongside functionality rather than being deferred until the end of the project.

---

# Development Workflow

Flow is being developed incrementally.

A typical feature follows this workflow:

```text
Requirement
     ↓
Design
     ↓
Implementation
     ↓
Tests
     ↓
Review
     ↓
Git Commit
     ↓
Next Feature
```

Each meaningful feature should have a focused Git commit.

Example:

```text
Initial Flow project setup
Create FastAPI application
Add health endpoint
Add database configuration
Create Item model
Add Todo creation endpoint
Add Note creation endpoint
Add item retrieval endpoint
Add Todo completion
Add React application
Build dashboard
Connect frontend to API
Add search
```

The Git history is intended to document the evolution of the application.

---

# Development Roadmap

## Milestone 1 — Foundation

**Status: In Progress**

* [x] Repository structure
* [x] Backend setup
* [x] FastAPI application
* [x] Health endpoint
* [x] Backend test structure
* [x] Initial documentation

---

## Milestone 2 — Persistence

**Status: Planned**

* [ ] SQLite configuration
* [ ] SQLAlchemy integration
* [ ] Database initialization
* [ ] Initial `Item` model
* [ ] Database tests

---

## Milestone 3 — Todo API

**Status: Planned**

* [ ] Todo creation
* [ ] Todo retrieval
* [ ] Todo editing
* [ ] Todo deletion
* [ ] Todo completion
* [ ] Todo reopening
* [ ] API validation
* [ ] Backend tests

---

## Milestone 4 — Notes API

**Status: Planned**

* [ ] Note creation
* [ ] Note retrieval
* [ ] Note editing
* [ ] Note deletion
* [ ] Note search
* [ ] Backend tests

---

## Milestone 5 — Frontend

**Status: Planned**

* [ ] React + TypeScript setup
* [ ] Application shell
* [ ] Dashboard
* [ ] Capture interface
* [ ] Todo interface
* [ ] Notes interface
* [ ] API integration
* [ ] Loading states
* [ ] Error states
* [ ] Responsive design

---

## Milestone 6 — Organization

**Status: Planned**

* [ ] Search
* [ ] Filtering
* [ ] Priorities
* [ ] Due dates
* [ ] Tags
* [ ] Sorting
* [ ] Completed Todo section

---

## Milestone 7 — Productivity Features

**Status: Planned**

* [ ] Todo ↔ Note conversion
* [ ] Keyboard shortcuts
* [ ] Pinning
* [ ] Archiving
* [ ] Recently updated items
* [ ] Improved dashboard organization

---

## Milestone 8 — Intelligence

**Status: Future**

AI is deliberately excluded from the initial application.

Potential future capabilities include:

* Note summarization
* Automatic tag suggestions
* Date extraction
* Converting notes into multiple Todos
* Semantic search
* Natural-language queries

These features will only be considered after the deterministic core application is stable.

---

# Design Direction

The final interface should feel like a **personal workspace**, not a complicated enterprise project-management platform.

The primary interaction should remain:

```text
             ┌──────────────────┐
             │ Write something   │
             └────────┬─────────┘
                      │
              ┌───────┴───────┐
              ▼               ▼
           ✓ TODO           NOTE
              │               │
              └───────┬───────┘
                      ▼
                    FLOW
```

The interface should prioritize:

* speed
* clarity
* readability
* minimal interaction
* keyboard accessibility
* responsive design

---

# Non-Goals

Flow is not intended to initially become:

* a full project-management platform
* a team collaboration tool
* an AI assistant
* a calendar replacement
* a chat application
* a complex knowledge-management system

The initial goal is much simpler:

> **Give one person a fast place to capture and organize Todos and Notes.**

---

# Future Possibilities

Once the core application is stable, Flow could evolve into a broader personal information system.

Possible future directions:

```text
                FLOW
                  │
       ┌──────────┼──────────┐
       │          │          │
     Todos      Notes      Search
       │          │          │
       └──────────┼──────────┘
                  │
              Intelligence
                  │
       ┌──────────┼──────────┐
       │          │          │
    Semantic    AI        Analytics
     Search   Features     & Insights
```

Potential long-term capabilities include:

* Cross-device synchronization
* PostgreSQL
* Authentication
* Cloud deployment
* PWA / mobile support
* Attachments
* Markdown notes
* Semantic search
* AI-assisted organization
* Natural-language interaction

These are deliberately outside the scope of the first version.

---

# Engineering Goals

Flow is also a software-engineering learning project.

The project aims to demonstrate practical experience with:

* REST API design
* Backend architecture
* Database modeling
* ORM usage
* Type-safe frontend development
* Automated testing
* Git workflows
* GitHub development
* API integration
* Error handling
* Responsive UI design
* Incremental feature development
* Technical documentation

The goal is not simply to produce an application.

The goal is to build it properly.

---

# License

License information will be added before the first public release.

---

# Project Status

**Flow is currently under active development.**

The current release represents the initial backend foundation. Features described in the roadmap are planned and may change as the application evolves.

---

## Built Incrementally

Flow is intentionally being developed one feature at a time, with each meaningful change tested and tracked through Git.

```text
Plan
 ↓
Build
 ↓
Test
 ↓
Review
 ↓
Commit
 ↓
Repeat
```

**Flow — capture it now. Organize it your way.**
