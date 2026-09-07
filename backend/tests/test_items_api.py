def create_todo(client, title="Finish DBMS Lab 4", content=""):
    response = client.post(
        "/api/items", json={"title": title, "content": content, "type": "TODO"}
    )
    assert response.status_code == 201
    return response.json()


def create_note(client, title="UAV research", content="Investigate memory-based detection"):
    response = client.post(
        "/api/items", json={"title": title, "content": content, "type": "NOTE"}
    )
    assert response.status_code == 201
    return response.json()


# --- Creation -----------------------------------------------------------


def test_create_todo_happy_path(client):
    item = create_todo(client)

    assert item["title"] == "Finish DBMS Lab 4"
    assert item["type"] == "TODO"
    assert item["completed"] is False
    assert item["content"] == ""
    assert "id" in item
    assert item["created_at"] is not None
    assert item["updated_at"] is not None


def test_create_note_happy_path(client):
    item = create_note(client)

    assert item["type"] == "NOTE"
    assert item["completed"] is False


def test_create_item_missing_title_is_validation_error(client):
    response = client.post("/api/items", json={"content": "no title", "type": "TODO"})

    assert response.status_code == 422


def test_create_item_empty_title_is_validation_error(client):
    response = client.post("/api/items", json={"title": "", "type": "TODO"})

    assert response.status_code == 422


def test_create_item_invalid_type_is_validation_error(client):
    response = client.post("/api/items", json={"title": "Something", "type": "MAYBE"})

    assert response.status_code == 422


def test_create_item_missing_type_is_validation_error(client):
    response = client.post("/api/items", json={"title": "Something"})

    assert response.status_code == 422


# --- Retrieval ------------------------------------------------------------


def test_list_items_returns_created_items(client):
    create_todo(client, title="A")
    create_note(client, title="B")

    response = client.get("/api/items")

    assert response.status_code == 200
    titles = {item["title"] for item in response.json()}
    assert titles == {"A", "B"}


def test_list_items_filters_by_type(client):
    create_todo(client, title="A todo")
    create_note(client, title="A note")

    response = client.get("/api/items", params={"type": "NOTE"})

    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["title"] == "A note"


def test_list_items_filters_by_completed(client):
    todo = create_todo(client, title="Pending")
    done = create_todo(client, title="Done")
    client.post(f"/api/items/{done['id']}/complete")

    response = client.get("/api/items", params={"completed": True})

    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["title"] == "Done"
    assert todo["title"] != items[0]["title"]


def test_get_item_by_id(client):
    created = create_todo(client)

    response = client.get(f"/api/items/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_item_missing_id_returns_404(client):
    response = client.get("/api/items/999999")

    assert response.status_code == 404


# --- Editing ----------------------------------------------------------


def test_update_item_title_and_content(client):
    created = create_todo(client)

    response = client.patch(
        f"/api/items/{created['id']}",
        json={"title": "Updated title", "content": "Updated content"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Updated title"
    assert body["content"] == "Updated content"


def test_update_item_missing_id_returns_404(client):
    response = client.patch("/api/items/999999", json={"title": "Nope"})

    assert response.status_code == 404


def test_update_item_invalid_type_is_validation_error(client):
    created = create_todo(client)

    response = client.patch(f"/api/items/{created['id']}", json={"type": "MAYBE"})

    assert response.status_code == 422


def test_update_item_empty_title_is_validation_error(client):
    created = create_todo(client)

    response = client.patch(f"/api/items/{created['id']}", json={"title": ""})

    assert response.status_code == 422


# --- Deletion ---------------------------------------------------------


def test_delete_item_removes_it(client):
    created = create_todo(client)

    delete_response = client.delete(f"/api/items/{created['id']}")
    get_response = client.get(f"/api/items/{created['id']}")

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


def test_delete_item_missing_id_returns_404(client):
    response = client.delete("/api/items/999999")

    assert response.status_code == 404


# --- Completion state transitions --------------------------------------


def test_complete_then_reopen_todo(client):
    created = create_todo(client)

    completed = client.post(f"/api/items/{created['id']}/complete")
    assert completed.status_code == 200
    assert completed.json()["completed"] is True

    reopened = client.post(f"/api/items/{created['id']}/reopen")
    assert reopened.status_code == 200
    assert reopened.json()["completed"] is False


def test_complete_missing_id_returns_404(client):
    response = client.post("/api/items/999999/complete")

    assert response.status_code == 404


def test_reopen_missing_id_returns_404(client):
    response = client.post("/api/items/999999/reopen")

    assert response.status_code == 404


# --- Todo <-> Note conversion -------------------------------------------


def test_convert_todo_to_note_and_back(client):
    created = create_todo(client)

    converted = client.post(f"/api/items/{created['id']}/convert")
    assert converted.status_code == 200
    assert converted.json()["type"] == "NOTE"

    converted_back = client.post(f"/api/items/{created['id']}/convert")
    assert converted_back.status_code == 200
    assert converted_back.json()["type"] == "TODO"


def test_convert_missing_id_returns_404(client):
    response = client.post("/api/items/999999/convert")

    assert response.status_code == 404
