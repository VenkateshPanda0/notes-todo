# Flow

Flow is a lightweight, personal workspace for quickly capturing either a todo or a note. The first version keeps that decision explicit: you write something, then choose **Todo** or **Note**. It does not use AI to classify content.

## Milestone 1

This initial milestone establishes the repository and a minimal FastAPI service with a health endpoint. It intentionally does not yet include items, persistence, a user interface, authentication, search, or AI features.

## Project structure

```text
backend/   FastAPI service and backend tests
frontend/  Reserved for the future React + TypeScript application
```

## Run the backend

1. Install Python 3.11 or newer.
2. Create and activate a virtual environment.
3. Install the backend dependencies:

   ```bash
   python -m pip install -r backend/requirements.txt
   ```

4. Start the service:

   ```bash
   uvicorn app.main:app --app-dir backend --reload
   ```

5. Visit `http://127.0.0.1:8000/health`.

## Test

```bash
python -m pytest backend/tests
```

## API

`GET /health` returns:

```json
{
  "status": "ok"
}
```

## Next milestone

Add the minimum database configuration and the initial unified `Item` model, keeping todos and notes explicitly selected by the user.
