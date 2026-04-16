import pytest


@pytest.mark.asyncio
async def test_login_success(client):
    response = await client.post("/auth/login", json={"email": "admin@example.com", "password": "adminpass"})
    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    response = await client.post("/auth/login", json={"email": "admin@example.com", "password": "wrong"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_only_admin_can_create_users(client, admin_headers):
    response = await client.post("/users/", headers=admin_headers, json={
        "username": "alice", "email": "alice@example.com", "password": "alicepw", "role": "engine_dev"
    })
    assert response.status_code == 201

    alice_login = await client.post("/auth/login", json={"email": "alice@example.com", "password": "alicepw"})
    alice_headers = {"Authorization": f"Bearer {alice_login.json()['access_token']}"}

    response2 = await client.post("/users/", headers=alice_headers, json={
        "username": "bob", "email": "bob@example.com", "password": "bobpw", "role": "game_dev"
    })
    assert response2.status_code == 403


@pytest.mark.asyncio
async def test_duplicate_user_rejected(client, admin_headers):
    user_data = {"username": "dup", "email": "dup@example.com", "password": "dup123", "role": "game_dev"}
    await client.post("/users/", headers=admin_headers, json=user_data)
    response = await client.post("/users/", headers=admin_headers, json=user_data)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_disabled_user_cannot_login(client, admin_headers):
    response = await client.post("/users/", headers=admin_headers, json={
        "username": "inactive", "email": "inactive@example.com", "password": "secret", "role": "game_dev"
    })
    user_id = response.json()["id"]
    await client.patch(f"/users/{user_id}", headers=admin_headers, json={"is_active": False})

    login_response = await client.post("/auth/login", json={"email": "inactive@example.com", "password": "secret"})
    assert login_response.status_code == 403
