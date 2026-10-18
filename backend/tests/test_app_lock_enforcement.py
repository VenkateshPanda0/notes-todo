from backend.app.services import session as session_service


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _setup(client, password: str = "secret1") -> str:
    return client.post("/api/auth/setup", json={"password": password}).json()["token"]


def test_items_are_open_when_no_password_is_set(client):
    assert client.get("/api/items").status_code == 200


def test_items_require_a_session_once_a_password_is_set(client):
    _setup(client)

    response = client.get("/api/items")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_every_item_route_is_protected(client):
    _setup(client)

    calls = [
        client.post("/api/items", json={"title": "x", "item_type": "TODO"}),
        client.get("/api/items"),
        client.get("/api/items/1"),
        client.patch("/api/items/1", json={"title": "y"}),
        client.delete("/api/items/1"),
        client.post("/api/items/1/complete"),
        client.post("/api/items/1/reopen"),
        client.post("/api/items/1/convert"),
    ]

    assert [c.status_code for c in calls] == [401] * len(calls)


def test_items_accessible_with_token_from_setup(client):
    token = _setup(client)

    response = client.get("/api/items", headers=_auth(token))

    assert response.status_code == 200


def test_items_accessible_with_token_from_unlock(client):
    _setup(client)
    token = client.post("/api/auth/unlock", json={"password": "secret1"}).json()["token"]

    response = client.get("/api/items", headers=_auth(token))

    assert response.status_code == 200


def test_invalid_or_malformed_tokens_are_rejected(client):
    _setup(client)

    for headers in (
        _auth("not-a-real-token"),
        {"Authorization": "Basic abc"},
        {"Authorization": "Bearer"},
    ):
        assert client.get("/api/items", headers=headers).status_code == 401


def test_lock_endpoint_revokes_the_session(client):
    token = _setup(client)

    lock = client.post("/api/auth/lock", headers=_auth(token))
    after = client.get("/api/items", headers=_auth(token))

    assert lock.status_code == 204
    assert after.status_code == 401


def test_change_password_requires_a_session(client):
    _setup(client)

    response = client.post(
        "/api/auth/change-password",
        json={"current_password": "secret1", "new_password": "secret2"},
    )

    assert response.status_code == 401


def test_change_password_revokes_old_tokens_and_returns_a_new_one(client):
    old_token = _setup(client)

    response = client.post(
        "/api/auth/change-password",
        json={"current_password": "secret1", "new_password": "secret2"},
        headers=_auth(old_token),
    )
    new_token = response.json()["token"]

    assert client.get("/api/items", headers=_auth(old_token)).status_code == 401
    assert client.get("/api/items", headers=_auth(new_token)).status_code == 200


def test_status_and_health_stay_public_when_locked(client):
    _setup(client)

    assert client.get("/api/auth/status").status_code == 200
    assert client.get("/health").status_code == 200


def test_repeated_wrong_passwords_trigger_a_lockout(client):
    _setup(client)

    for _ in range(session_service.MAX_FAILED_ATTEMPTS):
        assert client.post("/api/auth/unlock", json={"password": "wrong"}).status_code == 401

    blocked = client.post("/api/auth/unlock", json={"password": "secret1"})

    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0


def test_successful_unlock_resets_the_failure_counter(client):
    _setup(client)

    for _ in range(session_service.MAX_FAILED_ATTEMPTS - 1):
        client.post("/api/auth/unlock", json={"password": "wrong"})
    client.post("/api/auth/unlock", json={"password": "secret1"})
    for _ in range(session_service.MAX_FAILED_ATTEMPTS - 1):
        assert client.post("/api/auth/unlock", json={"password": "wrong"}).status_code == 401
