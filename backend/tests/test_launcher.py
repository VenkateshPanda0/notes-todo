import importlib.util
import json
import urllib.request

import pytest
from fastapi import FastAPI

from backend.app.main import app as real_app
from backend.launcher import HOST, run_smoke_test, start_server


def fetch(url: str):
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.status, response.read().decode()


def test_server_listens_on_a_free_localhost_port_and_serves_requests():
    running = start_server(FastAPI())
    try:
        assert running.port not in (0, 8000)
        assert running.server.config.host != "0.0.0.0"
        assert running.url == f"http://{HOST}:{running.port}"
        # FastAPI() has no routes, so a 404 JSON response still proves it is serving.
        with pytest.raises(urllib.error.HTTPError) as err:
            fetch(running.url + "/nothing")
        assert err.value.code == 404
    finally:
        running.stop()
    assert not running.thread.is_alive()


def test_two_servers_get_different_ports():
    first, second = start_server(FastAPI()), start_server(FastAPI())
    try:
        assert first.port != second.port
    finally:
        first.stop()
        second.stop()


def test_server_start_failure_is_reported_not_hung():
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def failing_lifespan(_):
        raise RuntimeError("boom")
        yield  # pragma: no cover

    with pytest.raises(RuntimeError, match="stopped while starting"):
        start_server(FastAPI(lifespan=failing_lifespan), timeout=10)


def test_smoke_test_passes_against_the_real_app(db_session_factory):
    from backend.app.api.deps import get_db

    def override():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    real_app.dependency_overrides[get_db] = override
    try:
        failures = run_smoke_test(real_app, require_frontend=False, require_webview=False)
    finally:
        real_app.dependency_overrides.clear()

    assert failures == []


def test_smoke_test_reports_a_missing_frontend():
    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    failures = run_smoke_test(app, require_frontend=True, require_webview=False)

    assert any("/api/items" in f and "404" in f for f in failures)


@pytest.mark.skipif(importlib.util.find_spec("webview") is not None, reason="pywebview is installed")
def test_smoke_test_flags_a_bundle_missing_pywebview():
    failures = run_smoke_test(FastAPI(), require_frontend=False, require_webview=True)

    assert any("pywebview" in f for f in failures)
