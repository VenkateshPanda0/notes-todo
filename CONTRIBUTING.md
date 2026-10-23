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
cd frontend && npm run lint && npm test && npm run build
```

CI runs the same checks, so please make sure they pass locally first.

## Changing the database schema

TaskFlow keeps users' data in a local SQLite file, so a schema change must upgrade **existing** databases without losing data. `Base.metadata.create_all` only creates missing tables; it never alters existing ones.

1. Change the models.
2. In `backend/app/db/migrations.py`, bump `LATEST_SCHEMA_VERSION` and, if you alter an existing table (for example adding a column), register an upgrade function for that version in `_UPGRADES`.
3. Add a test in `backend/tests/test_migrations.py` that builds an old-format database, upgrades it, and checks the existing rows survive.

Use the `_add_columns` helper in `migrations.py` for `ALTER TABLE ... ADD COLUMN`: it is safe to re-run. Before any upgrade TaskFlow copies the old database to `backups/before-upgrade-vN-<time>.db` (the newest 3 are kept), so a failed upgrade never costs a user their data.

A database from a *newer* TaskFlow than the running app is refused rather than risked.

## The database layer

`backend/app/db/manager.py` owns the connection: a plain database opens at startup, an encrypted one stays closed until the password arrives (`get_db` yields `None` and `require_unlocked` answers 401). Don't create engines elsewhere. Deleting an item is a *soft* delete (`deleted_at`, purged after 30 days): any new query over items must filter `deleted_at IS NULL`. Encryption (`db/crypto.py`) must keep three promises: never modify the source file while converting, always verify a converted file before swapping it in, and never accept an empty password (SQLCipher treats `''` as "no encryption"). Tests for it need `pip install sqlcipher3-wheels` and are slow on purpose (SQLCipher's key derivation is expensive).

## Guidelines

- Keep PRs focused: one change per PR.
- Add or update tests for behavior changes: `pytest` for the backend, Vitest (`npm test`) for frontend logic and components.
- Keep the interface accessible: label form fields, make interactive things real buttons/links (not clickable `div`s), and use the `*-ink` colour tokens for text so contrast holds in light and dark mode.
- Follow the existing layering: `api` (routes) → `schemas` → `services` (logic) → `models`. Keep route handlers thin.
- Match the surrounding code style. Don't reformat unrelated code.
- TaskFlow is intentionally **local-first**: features must work offline and must not require an account. Optional network features are fine if they are opt-in.

## Design principles

1. **Explicit over automatic**: the user decides what is a Todo and what is a Note.
2. **Local over cloud**: data stays on the user's machine by default.
3. **Minimal over feature-heavy**: capture, organize, act.

## License

By contributing you agree that your contributions are licensed under the [MIT License](LICENSE).

## Releasing

Releases are built and published by [`.github/workflows/release.yml`](.github/workflows/release.yml).

1. Make sure `main` is green and contains what you want to ship.
2. Tag and push:

   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

3. The workflow runs the tests, builds `TaskFlow.exe` on a Windows runner with PyInstaller, runs `TaskFlow.exe --smoke-test` against the built exe, and only then publishes a GitHub Release with the exe and a `.sha256` checksum. Release notes are generated from merged changes.

**Dry run:** in the repository's Actions tab choose *Release → Run workflow*. It builds and smoke-tests the exe and attaches it to the run as an artifact, without creating a release.

If the smoke test fails, the log shows which check failed (server start, API, database, bundled UI, or pywebview) and includes `taskflow.log` from the runner.

To change the app icon or social preview image, edit `scripts/make_assets.py` and run `python scripts/make_assets.py` (needs `pip install pillow`).
