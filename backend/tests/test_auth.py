import pytest
from httpx import AsyncClient
from sqlalchemy import text

VALID = {"email": "asha@example.org", "password": "a-long-password-1", "full_name": "Asha Verma"}


async def register(client: AsyncClient, **overrides: object) -> object:
    return await client.post("/v1/auth/register", json={**VALID, **overrides})


async def test_register_sets_httponly_cookie_and_returns_donor(client: AsyncClient) -> None:
    r = await register(client)
    assert r.status_code == 201  # type: ignore[attr-defined]
    body = r.json()  # type: ignore[attr-defined]
    assert body["role"] == "donor"
    assert "password" not in str(body)
    cookie = r.headers["set-cookie"]  # type: ignore[attr-defined]
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie


async def test_role_cannot_be_chosen_by_the_client(client: AsyncClient) -> None:
    r = await register(client, role="admin")
    assert r.status_code == 422  # type: ignore[attr-defined]  # unknown fields are rejected


async def test_duplicate_email_is_rejected_case_insensitively(client: AsyncClient) -> None:
    assert (await register(client)).status_code == 201  # type: ignore[attr-defined]
    r = await register(client, email="ASHA@example.org")
    assert r.status_code == 409  # type: ignore[attr-defined]


async def test_short_password_is_rejected_without_echoing_it(client: AsyncClient) -> None:
    r = await register(client, password="short")
    assert r.status_code == 422  # type: ignore[attr-defined]
    assert "short" not in r.text  # type: ignore[attr-defined]
    assert r.headers["content-type"].startswith("application/problem+json")  # type: ignore[attr-defined]


async def test_me_requires_a_session(client: AsyncClient) -> None:
    r = await client.get("/v1/auth/me")
    assert r.status_code == 401


async def test_login_then_me_then_logout(client: AsyncClient) -> None:
    await register(client)
    client.cookies.clear()
    login = await client.post(
        "/v1/auth/login", json={"email": VALID["email"], "password": VALID["password"]}
    )
    assert login.status_code == 200
    me = await client.get("/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == VALID["email"]
    out = await client.post("/v1/auth/logout")
    assert out.status_code == 204
    client.cookies.clear()
    assert (await client.get("/v1/auth/me")).status_code == 401


async def test_wrong_password_and_unknown_email_give_the_same_generic_error(
    client: AsyncClient,
) -> None:
    await register(client)
    client.cookies.clear()
    wrong = await client.post(
        "/v1/auth/login", json={"email": VALID["email"], "password": "not-the-password"}
    )
    unknown = await client.post(
        "/v1/auth/login", json={"email": "nobody@example.org", "password": "not-the-password"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"]


async def test_login_is_rate_limited_with_retry_after(client: AsyncClient) -> None:
    for _ in range(10):
        await client.post("/v1/auth/login", json={"email": "x@example.org", "password": "pw"})
    r = await client.post("/v1/auth/login", json={"email": "x@example.org", "password": "pw"})
    assert r.status_code == 429
    assert int(r.headers["retry-after"]) >= 1


async def test_tampered_cookie_is_rejected(client: AsyncClient) -> None:
    await register(client)
    token = client.cookies.get("session")
    assert token
    client.cookies.set("session", token[:-3] + "abc")
    assert (await client.get("/v1/auth/me")).status_code == 401


async def test_stored_password_is_hashed_not_plaintext(client: AsyncClient, app: object) -> None:
    await register(client)
    async with app.state.engine.connect() as conn:  # type: ignore[attr-defined]
        stored = (await conn.execute(text("SELECT password_hash FROM users"))).scalar_one()
    assert stored.startswith("$argon2")
    assert VALID["password"] not in stored


@pytest.mark.parametrize("path", ["/health"])
async def test_health_is_public_and_does_not_need_the_database(
    client: AsyncClient, path: str
) -> None:
    assert (await client.get(path)).json() == {"status": "ok"}


async def test_ready_round_trips_the_database(client: AsyncClient) -> None:
    r = await client.get("/ready")
    assert r.status_code == 200
    assert r.json() == {"status": "ready"}
