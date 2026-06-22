def test_in_memory_rate_limiter_blocks_after_limit():
    from app.services.rate_limiter import InMemoryRateLimitBackend

    backend = InMemoryRateLimitBackend()

    assert backend.hit("login:single:127.0.0.1", limit=1, window_seconds=60) == (True, 0)
    allowed, retry_after = backend.hit("login:single:127.0.0.1", limit=1, window_seconds=60)

    assert allowed is False
    assert retry_after > 0


def test_register_endpoint_returns_retry_after_when_limited(client):
    admin_headers = _login_as_admin(client)
    update = client.put(
        "/api/v1/admin/rate-limits/register",
        headers=admin_headers,
        json={
            "singleMax": 1,
            "singleWindowSeconds": 60,
            "minuteMax": 1,
            "minuteWindowSeconds": 60,
            "dayMax": 10,
            "dayWindowSeconds": 86400,
        },
    ).json()
    assert update["code"] == 200

    first = client.post("/api/v1/users/register", headers={"X-Test-Client": "limited"}, json={"username": "limited-1", "password": "secret"}).json()
    second = client.post("/api/v1/users/register", headers={"X-Test-Client": "limited"}, json={"username": "limited-2", "password": "secret"}).json()

    assert first["code"] == 200
    assert second["code"] == 429
    assert second["data"]["retryAfterSeconds"] > 0


def _login_as_admin(client):
    from sqlalchemy import select

    from app.core.database import SessionLocal
    from app.models.user import User

    client.post("/api/v1/users/register", json={"username": "rate-admin", "password": "secret"})
    data = client.post("/api/v1/users/login", json={"username": "rate-admin", "password": "secret"}).json()["data"]
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.username == "rate-admin"))
        user.role = "ADMIN"
        db.commit()
    finally:
        db.close()
    return {"Authorization": f"Bearer {data['token']}"}
