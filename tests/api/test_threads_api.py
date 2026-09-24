from evidence_graph.auth import Role
from tests.support import auth_header


def test_user_cannot_read_or_resume_or_delete_another_users_thread(client, settings):
    alice = auth_header(settings, "alice")
    bob = auth_header(settings, "bob")
    created = client.post("/v1/comparisons", json={}, headers=alice)
    thread_id = created.json()["thread_id"]

    assert client.get(f"/v1/threads/{thread_id}", headers=bob).status_code == 404
    assert client.get("/v1/threads", headers=bob).json() == []
    assert (
        client.post("/v1/comparisons", json={"thread_id": thread_id}, headers=bob).status_code
        == 404
    )
    assert client.delete(f"/v1/threads/{thread_id}", headers=bob).status_code == 404
    assert client.get(f"/v1/threads/{thread_id}", headers=alice).status_code == 200


def test_viewer_can_read_own_thread(client, settings):
    researcher = auth_header(settings, "alice", Role.RESEARCHER)
    viewer = auth_header(settings, "alice", Role.VIEWER)
    thread_id = client.post("/v1/comparisons", json={}, headers=researcher).json()["thread_id"]

    response = client.get(f"/v1/threads/{thread_id}", headers=viewer)

    assert response.status_code == 200
    assert response.json()["thread_id"] == thread_id
    assert response.json()["comparison"]["reports"]


def test_list_returns_only_the_caller_threads(client, settings):
    alice = auth_header(settings, "alice")
    bob = auth_header(settings, "bob")
    alice_id = client.post("/v1/comparisons", json={}, headers=alice).json()["thread_id"]
    bob_id = client.post("/v1/comparisons", json={}, headers=bob).json()["thread_id"]

    alice_list = client.get("/v1/threads", headers=alice).json()
    bob_list = client.get("/v1/threads", headers=bob).json()

    assert [t["thread_id"] for t in alice_list] == [alice_id]
    assert [t["thread_id"] for t in bob_list] == [bob_id]


def test_owner_can_delete_their_thread(client, settings):
    headers = auth_header(settings)
    thread_id = client.post("/v1/comparisons", json={}, headers=headers).json()["thread_id"]

    deleted = client.delete(f"/v1/threads/{thread_id}", headers=headers)

    assert deleted.status_code == 204
    assert client.get(f"/v1/threads/{thread_id}", headers=headers).status_code == 404


def test_threads_require_a_token(client):
    assert client.get("/v1/threads").status_code == 401
    assert client.get("/v1/threads/missing").status_code == 401
    assert client.delete("/v1/threads/missing").status_code == 401
