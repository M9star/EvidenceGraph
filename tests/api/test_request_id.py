from tests.support import auth_header


def test_health_echoes_a_request_id(client):
    response = client.get("/health", headers={"x-request-id": "req-123"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req-123"


def test_comparison_gets_a_generated_request_id(client, settings):
    response = client.post("/v1/comparisons", json={}, headers=auth_header(settings))

    assert response.status_code == 200
    assert response.headers["x-request-id"]
