import io
import pytest


@pytest.mark.asyncio
async def test_create_game(client, admin_headers):
    response = await client.post("/games/", headers=admin_headers, json={
        "name": "Default", "folder_name": "default", "description": "demo game"
    })
    assert response.status_code == 201
    assert response.json()["folder_name"] == "default"


@pytest.mark.asyncio
async def test_assign_game_to_game_dev(client, admin_headers):
    user_response = await client.post("/users/", headers=admin_headers, json={
        "username": "gamedev1", "email": "gamedev1@example.com", "password": "secret", "role": "game_dev"
    })
    user_id = user_response.json()["id"]

    game_response = await client.post("/games/", headers=admin_headers, json={"name": "G1", "folder_name": "g1"})
    game_id = game_response.json()["id"]

    assign_response = await client.post("/assignments/", headers=admin_headers,
                                        json={"user_id": user_id, "game_id": game_id})
    assert assign_response.status_code == 201

    duplicate_response = await client.post("/assignments/", headers=admin_headers,
                                           json={"user_id": user_id, "game_id": game_id})
    assert duplicate_response.status_code == 400


@pytest.mark.asyncio
async def test_admin_can_upload_binary(client, admin_headers, binaries_dir):
    files = {"file": ("Outland-debug.zip", io.BytesIO(b"PKDATA"), "application/zip")}
    form = {"kind": "debug", "platform": "linux", "version": "0.1.0"}
    response = await client.post("/binaries/", headers=admin_headers, files=files, data=form)
    assert response.status_code == 201
    assert response.json()["kind"] == "debug"

    list_response = await client.get("/binaries/", headers=admin_headers)
    assert len(list_response.json()) == 1


@pytest.mark.asyncio
async def test_non_admin_cannot_upload_binary(client, admin_headers, binaries_dir):
    await client.post("/users/", headers=admin_headers, json={
        "username": "developer", "email": "dev@example.com", "password": "secret", "role": "game_dev"
    })
    dev_login = await client.post("/auth/login", json={"email": "dev@example.com", "password": "secret"})
    dev_headers = {"Authorization": f"Bearer {dev_login.json()['access_token']}"}

    files = {"file": ("build.zip", io.BytesIO(b"data"), "application/zip")}
    response = await client.post("/binaries/", headers=dev_headers,
                                 files=files, data={"kind": "debug", "platform": "linux", "version": "0"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_engine_dev_only_sees_debug_builds(client, admin_headers, binaries_dir):
    for build_kind in ("debug", "release"):
        files = {"file": (f"Outland-{build_kind}.zip", io.BytesIO(b"X"), "application/zip")}
        await client.post("/binaries/", headers=admin_headers,
                          files=files, data={"kind": build_kind, "platform": "linux", "version": "0.1"})

    await client.post("/users/", headers=admin_headers, json={
        "username": "engdev", "email": "engdev@example.com", "password": "secret", "role": "engine_dev"
    })
    login = await client.post("/auth/login", json={"email": "engdev@example.com", "password": "secret"})
    eng_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = await client.get("/binaries/", headers=eng_headers)
    build_kinds = {b["kind"] for b in response.json()}
    assert build_kinds == {"debug"}
