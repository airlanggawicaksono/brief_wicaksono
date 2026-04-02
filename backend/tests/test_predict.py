def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_predict(client):
    r = client.post("/predict", json={"text": "show me skincare for gen z under 100k"})
    assert r.status_code == 200
    data = r.json()
    assert "intent" in data
    assert "entities" in data


def test_predict_and_search(client):
    r = client.post("/predict/search", json={"text": "skincare products"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)
