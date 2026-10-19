"""Desktop launcher: runs the local API in-process and shows the UI in a native window.

    TaskFlow.exe                 open the app
    TaskFlow.exe --smoke-test    start the server, check it end to end, exit 0 (ok) or 1 (failed)

The server listens on a free port chosen at startup (never a fixed one), bound to localhost only,
and the window opens only once the server is ready.
"""

import argparse
import json
import logging
import os
import socket
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

import uvicorn

HOST = "127.0.0.1"
STARTUP_TIMEOUT_SECONDS = 20.0


@dataclass
class RunningServer:
    server: uvicorn.Server
    thread: threading.Thread
    port: int

    @property
    def url(self) -> str:
        return f"http://{HOST}:{self.port}"

    def stop(self, timeout: float = 5.0) -> None:
        self.server.should_exit = True
        self.thread.join(timeout)


def _serve(server: uvicorn.Server, sock: socket.socket) -> None:
    try:
        server.run(sockets=[sock])
    except SystemExit:
        # uvicorn exits with a status code when startup fails; start_server reports that itself.
        pass


def start_server(app, timeout: float = STARTUP_TIMEOUT_SECONDS) -> RunningServer:
    """Serve `app` on a free localhost port and return once it accepts requests."""
    # Bind the socket ourselves and hand it to uvicorn so the port cannot be taken in between.
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((HOST, 0))
    port = sock.getsockname()[1]

    # log_config=None: uvicorn's default logging config assumes a console and crashes in a
    # windowed (no stdout) executable.
    config = uvicorn.Config(app, log_config=None, log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=_serve, args=(server, sock), daemon=True)
    thread.start()

    deadline = time.monotonic() + timeout
    while not server.started:
        if not thread.is_alive():
            raise RuntimeError("The local server stopped while starting up.")
        if time.monotonic() > deadline:
            server.should_exit = True
            raise RuntimeError(f"The local server did not start within {timeout:.0f} seconds.")
        time.sleep(0.05)
    return RunningServer(server=server, thread=thread, port=port)


def _get(url: str) -> tuple[int, str]:
    with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310 (localhost only)
        return response.status, response.read().decode("utf-8", errors="replace")


def run_smoke_test(app, *, require_frontend: bool, require_webview: bool) -> list[str]:
    """Exercise a running server end to end. Returns a list of failures (empty means success)."""
    failures: list[str] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        if not condition:
            failures.append(f"{name}{': ' + detail if detail else ''}")

    if require_webview:
        try:
            import webview  # noqa: F401
        except Exception as exc:  # noqa: BLE001 - any import failure means a broken bundle
            failures.append(f"pywebview is not importable: {exc!r}")

    try:
        running = start_server(app)
    except Exception as exc:  # noqa: BLE001
        return [*failures, f"server did not start: {exc!r}"]

    try:
        status, body = _get(f"{running.url}/health")
        check("GET /health", status == 200 and json.loads(body) == {"status": "ok"}, body)

        # Creating and reading an item proves the database and ORM work in this build.
        request = urllib.request.Request(
            f"{running.url}/api/items",
            data=json.dumps({"title": "smoke test", "type": "NOTE", "tags": ["smoke"]}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
            created = json.loads(response.read())
        check("POST /api/items", response.status == 201 and created["title"] == "smoke test")
        status, body = _get(f"{running.url}/api/items/{created['id']}/backlinks")
        check("GET backlinks", status == 200 and json.loads(body) == [], body)
        status, body = _get(f"{running.url}/api/graph")
        check("GET /api/graph", status == 200 and len(json.loads(body)["nodes"]) == 1, body)

        # Take a backup and list it: proves SQLite snapshots work in this build.
        request = urllib.request.Request(f"{running.url}/api/backup/auto/run", method="POST")
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
            listing = json.loads(response.read())
        check("POST /api/backup/auto/run", response.status == 200 and listing["enabled"] and len(listing["backups"]) >= 1, str(listing))
        status, body = _get(f"{running.url}/api/backup/export.json")
        check("GET /api/backup/export.json", status == 200 and json.loads(body)["format"] == "taskflow-export")

        # Works without Ollama installed; proves the AI endpoints and httpx are in this build.
        status, body = _get(f"{running.url}/api/ai/status")
        check("GET /api/ai/status", status == 200 and json.loads(body)["enabled"] is False, body)

        if require_frontend:
            status, body = _get(f"{running.url}/")
            check("GET / serves the app", status == 200 and 'id="root"' in body)
            status, body = _get(f"{running.url}/notes")
            check("GET /notes falls back to the app", status == 200 and 'id="root"' in body)
    except urllib.error.HTTPError as exc:
        failures.append(f"{exc.url} returned HTTP {exc.code}")
    except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:
        failures.append(f"request failed: {exc!r}")
    finally:
        running.stop()
    return failures


def configure_file_logging() -> None:
    """A windowed executable has no console, so write warnings and errors to a log file."""
    from app.db.session import app_data_dir

    logging.basicConfig(
        filename=os.path.join(app_data_dir(), "taskflow.log"),
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def run_gui(app) -> int:
    import webview  # imported lazily so --smoke-test and tests never need a display

    # Exports are downloads (blob links); WebView2 blocks them unless pywebview allows downloads.
    webview.settings["ALLOW_DOWNLOADS"] = True

    running = start_server(app)
    try:
        webview.create_window("TaskFlow", running.url, width=1100, height=750, min_size=(700, 500))
        webview.start()
    finally:
        running.stop()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="TaskFlow")
    parser.add_argument("--smoke-test", action="store_true", help="verify the build, then exit")
    parser.add_argument("--report", help="with --smoke-test, also write the result to this file")
    args = parser.parse_args(argv)

    frozen = bool(getattr(sys, "frozen", False))

    if args.smoke_test:
        # Use a throwaway database; this must be set before the app (and its engine) is imported.
        smoke_dir = tempfile.mkdtemp(prefix="taskflow-smoke-")
        os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(smoke_dir, 'smoke.db')}"
    elif frozen:
        configure_file_logging()

    from app.main import app  # noqa: E402 - must come after DATABASE_URL is decided

    if args.smoke_test:
        # A packaged build must contain the UI and pywebview; a source checkout may lack either.
        failures = run_smoke_test(
            app,
            require_frontend=frozen or os.getenv("TASKFLOW_SMOKE_REQUIRE_FRONTEND") == "1",
            require_webview=frozen and os.getenv("TASKFLOW_SMOKE_SKIP_WEBVIEW") != "1",
        )
        report = "SMOKE TEST PASSED" if not failures else "SMOKE TEST FAILED:\n" + "\n".join(failures)
        if args.report:
            with open(args.report, "w", encoding="utf-8") as handle:
                handle.write(report + "\n")
        print(report, file=sys.stderr if failures else sys.stdout)
        return 1 if failures else 0

    try:
        return run_gui(app)
    except Exception:
        logging.getLogger("taskflow").exception("TaskFlow failed to start")
        raise


if __name__ == "__main__":
    sys.exit(main())
