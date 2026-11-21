from .conftest import API


async def test_liveness(client):
    r = await client.get(f"{API}/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    assert (await client.get("/health")).status_code == 200


async def test_readiness_checks_db(client):
    r = await client.get(f"{API}/health/ready")
    assert r.status_code == 200 and r.json()["database"] == "ok"


async def test_request_id_header_and_error_envelope_for_404(client):
    r = await client.get(f"{API}/nope", headers={"X-Request-ID": "abc123"})
    assert r.headers["X-Request-ID"] == "abc123"
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
