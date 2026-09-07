def test_status_reports_unlocked_when_no_password_set(client):
    response = client.get("/api/auth/status")

    assert response.status_code == 200
    assert response.json() == {"is_locked": False}


def test_setup_password_then_status_reports_locked(client):
    setup = client.post("/api/auth/setup", json={"password": "secret1"})
    status = client.get("/api/auth/status")

    assert setup.status_code == 204
    assert status.json() == {"is_locked": True}


def test_setup_password_twice_is_rejected(client):
    client.post("/api/auth/setup", json={"password": "secret1"})

    response = client.post("/api/auth/setup", json={"password": "secret2"})

    assert response.status_code == 409


def test_unlock_with_correct_password_succeeds(client):
    client.post("/api/auth/setup", json={"password": "secret1"})

    response = client.post("/api/auth/unlock", json={"password": "secret1"})

    assert response.status_code == 204


def test_unlock_with_incorrect_password_fails(client):
    client.post("/api/auth/setup", json={"password": "secret1"})

    response = client.post("/api/auth/unlock", json={"password": "wrong"})

    assert response.status_code == 401


def test_unlock_with_no_password_configured_fails(client):
    response = client.post("/api/auth/unlock", json={"password": "anything"})

    assert response.status_code == 409


def test_change_password_with_correct_current_password(client):
    client.post("/api/auth/setup", json={"password": "secret1"})

    response = client.post(
        "/api/auth/change-password",
        json={"current_password": "secret1", "new_password": "secret2"},
    )
    unlock_new = client.post("/api/auth/unlock", json={"password": "secret2"})
    unlock_old = client.post("/api/auth/unlock", json={"password": "secret1"})

    assert response.status_code == 204
    assert unlock_new.status_code == 204
    assert unlock_old.status_code == 401


def test_change_password_with_incorrect_current_password_fails(client):
    client.post("/api/auth/setup", json={"password": "secret1"})

    response = client.post(
        "/api/auth/change-password",
        json={"current_password": "wrong", "new_password": "secret2"},
    )

    assert response.status_code == 401


def test_change_password_with_no_password_configured_fails(client):
    response = client.post(
        "/api/auth/change-password",
        json={"current_password": "anything", "new_password": "secret2"},
    )

    assert response.status_code == 409
