import pytest

from backend.app.services.graph import extract_links


def make(client, title, content="", type="NOTE", **extra):
    response = client.post("/api/items", json={"title": title, "type": type, "content": content, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def graph(client):
    return client.get("/api/graph").json()


def by_title(data):
    return {n["title"]: n for n in data["nodes"]}


# --- link extraction ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("see [[A]] and [[B]]", ["A", "B"]),
        ("[[A|alias]] then [[a]] again", ["A"]),  # aliases resolve to the title; repeats collapse
        ("  [[  Spaced  ]]  ", ["Spaced"]),
        ("`[[in code]]` and [[real]]", ["real"]),
        ("```\n[[in fence]]\n```\n[[after]]", ["after"]),
        ("[[]] [[ ]] [[a[b]]", []),
        ("no links here", []),
    ],
)
def test_extract_links(content, expected):
    assert extract_links(content) == expected


# --- graph endpoint ----------------------------------------------------------------------------


def test_empty_graph(client):
    assert graph(client) == {"nodes": [], "edges": []}


def test_items_without_links_are_isolated_nodes(client):
    make(client, "Lonely")

    data = graph(client)

    assert [n["title"] for n in data["nodes"]] == ["Lonely"]
    assert data["edges"] == []
    assert data["nodes"][0]["degree"] == 0
    assert data["nodes"][0]["missing"] is False


def test_links_become_directed_edges_and_count_toward_degree(client):
    a = make(client, "A", "links to [[B]] and [[C]]")
    b = make(client, "B")
    c = make(client, "C", "back to [[A]]")

    data = graph(client)
    nodes = by_title(data)

    assert {(e["source"], e["target"]) for e in data["edges"]} == {
        (f"item:{a['id']}", f"item:{b['id']}"),
        (f"item:{a['id']}", f"item:{c['id']}"),
        (f"item:{c['id']}", f"item:{a['id']}"),
    }
    assert nodes["A"]["degree"] == 3
    assert nodes["B"]["degree"] == 1


def test_links_are_case_insensitive_and_support_aliases(client):
    make(client, "Target")
    make(client, "Source", "[[target|the thing]]")

    assert len(graph(client)["edges"]) == 1


def test_unresolved_links_become_missing_nodes_shared_by_title(client):
    make(client, "One", "needs [[Ghost]]")
    make(client, "Two", "also needs [[ghost]]")

    data = graph(client)
    ghosts = [n for n in data["nodes"] if n["missing"]]

    assert len(ghosts) == 1
    assert ghosts[0]["id"] is None
    assert ghosts[0]["type"] is None
    assert ghosts[0]["degree"] == 2
    assert len(data["edges"]) == 2


def test_self_links_and_duplicate_links_are_ignored(client):
    make(client, "Loop", "[[Loop]] [[Other]] [[Other]]")
    make(client, "Other")

    data = graph(client)

    assert len(data["edges"]) == 1
    assert by_title(data)["Loop"]["degree"] == 1


def test_duplicate_titles_resolve_to_the_oldest_item(client):
    first = make(client, "Same")
    make(client, "Same")
    make(client, "Linker", "[[Same]]")

    data = graph(client)

    assert [e["target"] for e in data["edges"]] == [f"item:{first['id']}"]


def test_links_work_between_todos_and_notes_and_carry_node_details(client):
    make(client, "Pay rent", type="TODO", tags=["home"])
    make(client, "Budget", "[[Pay rent]]")
    client.post("/api/items/1/complete")

    nodes = by_title(graph(client))

    assert nodes["Pay rent"]["type"] == "TODO"
    assert nodes["Pay rent"]["completed"] is True
    assert nodes["Pay rent"]["tags"] == ["home"]
    assert nodes["Budget"]["type"] == "NOTE"


def test_graph_requires_the_session_when_locked(client):
    client.post("/api/auth/setup", json={"password": "secret1"})

    assert client.get("/api/graph").status_code == 401
