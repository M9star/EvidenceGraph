from fastapi.testclient import TestClient

from evidence_graph.api.main import create_app
from evidence_graph.auth import Role
from evidence_graph.tools.fixture import FixtureToolkit
from tests.support import auth_header


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unauthenticated_run_is_rejected(client):
    response = client.post("/v1/comparisons", json={})

    assert response.status_code == 401


def test_forged_token_is_rejected(client):
    response = client.post(
        "/v1/comparisons",
        json={},
        headers={"Authorization": "Bearer not-a-real-token"},
    )

    assert response.status_code == 401


def test_viewer_cannot_start_a_run(client, settings):
    response = client.post(
        "/v1/comparisons",
        json={},
        headers=auth_header(settings, role=Role.VIEWER),
    )

    assert response.status_code == 403


def test_create_comparison_defaults_to_all_four_countries(client, settings):
    response = client.post("/v1/comparisons", json={}, headers=auth_header(settings))

    assert response.status_code == 200
    body = response.json()
    assert body["thread_id"]
    assert [r["country"] for r in body["comparison"]["reports"]] == ["FR", "DE", "UK", "IN"]


def test_each_request_gets_its_own_thread(client, settings):
    headers = auth_header(settings)
    first = client.post("/v1/comparisons", json={}, headers=headers).json()
    second = client.post("/v1/comparisons", json={}, headers=headers).json()

    assert first["thread_id"] != second["thread_id"]
    assert len(second["comparison"]["reports"]) == 4


def test_resume_replaces_reports_instead_of_appending(client, settings):
    headers = auth_header(settings)
    first = client.post("/v1/comparisons", json={}, headers=headers).json()
    second = client.post(
        "/v1/comparisons",
        json={"thread_id": first["thread_id"]},
        headers=headers,
    )

    assert second.status_code == 200
    body = second.json()
    assert body["thread_id"] == first["thread_id"]
    assert len(body["comparison"]["reports"]) == 4
    detail = client.get(f"/v1/threads/{first['thread_id']}", headers=headers).json()
    assert len(detail["history"]) == 1


def test_unknown_country_is_rejected(client, settings):
    response = client.post(
        "/v1/comparisons", json={"countries": ["US"]}, headers=auth_header(settings)
    )

    assert response.status_code == 422


def test_empty_country_list_is_rejected(client, settings):
    response = client.post("/v1/comparisons", json={"countries": []}, headers=auth_header(settings))

    assert response.status_code == 422


def test_daily_quota_rejects_the_next_run(settings):
    tight = settings.model_copy(update={"daily_run_quota": 1})
    client = TestClient(create_app(settings=tight, toolkit=FixtureToolkit()))
    headers = auth_header(tight)

    assert client.post("/v1/comparisons", json={}, headers=headers).status_code == 200
    second = client.post("/v1/comparisons", json={}, headers=headers)

    assert second.status_code == 429
    assert second.json()["detail"] == "daily run quota exceeded"
