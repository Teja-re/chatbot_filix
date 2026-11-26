import pytest


@pytest.mark.anyio
async def test_register_login_and_me(client):
    res = await client.post(
        "/api/auth/register",
        json={"name": "Sathwik", "email": "sathwik@example.com", "password": "secret123"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["user"]["email"] == "sathwik@example.com"
    token = data["access_token"]

    me_res = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["name"] == "Sathwik"

    bad_login = await client.post(
        "/api/auth/login",
        json={"email": "sathwik@example.com", "password": "wrong"},
    )
    assert bad_login.status_code == 401


@pytest.mark.anyio
async def test_protected_routes_require_token(client):
    res = await client.get("/api/restaurants/nearby")
    assert res.status_code == 401
