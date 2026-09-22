def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_comparison_defaults_to_all_four_countries(client):
    response = client.post("/v1/comparisons", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["thread_id"]
    assert [r["country"] for r in body["comparison"]["reports"]] == ["FR", "DE", "UK", "IN"]


def test_each_request_gets_its_own_thread(client):
    first = client.post("/v1/comparisons", json={}).json()
    second = client.post("/v1/comparisons", json={}).json()

    assert first["thread_id"] != second["thread_id"]
    assert len(second["comparison"]["reports"]) == 4


def test_unknown_country_is_rejected(client):
    response = client.post("/v1/comparisons", json={"countries": ["US"]})

    assert response.status_code == 422


def test_empty_country_list_is_rejected(client):
    response = client.post("/v1/comparisons", json={"countries": []})

    assert response.status_code == 422
