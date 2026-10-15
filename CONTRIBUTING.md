# Contributing to TaskFlow

Thanks for your interest! TaskFlow is a small, local-first todo and notes app, and contributions of all sizes are welcome: bug reports, ideas, docs, and code.

## Ways to help

- **Report a bug** or **request a feature** using the issue templates.
- Pick up an issue labelled `good first issue`.
- Improve the docs or screenshots.
- Help test on other platforms (macOS/Linux support is on the roadmap).

## Development setup

You need Python 3.11+ and Node.js.

```bash
# Frontend
cd frontend
npm install
npm run dev

# Backend (second terminal)
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The Vite dev server runs on `http://localhost:5173` and talks to the API on port 8000.

## Before you open a pull request

```bash
python -m pytest backend/tests -v        # run from the repo root
cd frontend && npm run lint && npm run build
```

CI runs the same checks, so please make sure they pass locally first.

## Guidelines

- Keep PRs focused: one change per PR.
- Add or update tests for backend behavior changes.
- Follow the existing layering: `api` (routes) → `schemas` → `services` (logic) → `models`. Keep route handlers thin.
- Match the surrounding code style. Don't reformat unrelated code.
- TaskFlow is intentionally **local-first**: features must work offline and must not require an account. Optional network features are fine if they are opt-in.

## Design principles

1. **Explicit over automatic**: the user decides what is a Todo and what is a Note.
2. **Local over cloud**: data stays on the user's machine by default.
3. **Minimal over feature-heavy**: capture, organize, act.

## License

By contributing you agree that your contributions are licensed under the [MIT License](LICENSE).
