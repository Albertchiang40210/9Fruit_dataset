from fastapi.testclient import TestClient

import live_predict_api as api

client = TestClient(api.app)


def test_health_is_public():
    assert client.get("/health").status_code == 200


def test_upload_requires_api_key():
    r = client.post("/api/upload_shot", json={"image": ""})
    assert r.status_code == 403


def test_upload_rejects_wrong_key():
    r = client.post("/api/upload_shot", json={"image": ""}, headers={"X-API-Key": "nope"})
    assert r.status_code == 403


def test_bad_image_returns_400():
    r = client.post("/api/upload_shot", json={"image": "bm90IGFuIGltYWdl"}, headers={"X-API-Key": "test-key"})
    assert r.status_code == 400
