import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.spa import SPAStaticFiles


@pytest.fixture()
def spa_client(tmp_path):
    (tmp_path / "index.html").write_text("<html>app shell</html>")
    (tmp_path / "logo.svg").write_text("<svg/>")
    app = FastAPI()

    @app.get("/api/ping")
    def ping():
        return {"ok": True}

    app.mount("/", SPAStaticFiles(directory=tmp_path, html=True), name="frontend")
    return TestClient(app)


def test_root_serves_index(spa_client):
    assert "app shell" in spa_client.get("/").text


def test_real_files_are_served_as_is(spa_client):
    assert spa_client.get("/logo.svg").text == "<svg/>"


@pytest.mark.parametrize("route", ["/notes", "/calendar", "/settings", "/some/deep/route"])
def test_client_routes_fall_back_to_the_app_shell(spa_client, route):
    response = spa_client.get(route)

    assert response.status_code == 200
    assert "app shell" in response.text


def test_defined_api_routes_still_work(spa_client):
    assert spa_client.get("/api/ping").json() == {"ok": True}


def test_unknown_api_paths_stay_404(spa_client):
    assert spa_client.get("/api/does-not-exist").status_code == 404
