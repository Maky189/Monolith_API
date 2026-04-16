import queue
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from acl import Access, access_for, rules_for
from database import Role


def make_user(role):
    return SimpleNamespace(role=role)


@pytest_asyncio.fixture
async def source_tree(tmp_path, monkeypatch):
    root = tmp_path / "Outland"
    (root / "src" / "Core").mkdir(parents=True)
    (root / "src" / "RHI").mkdir(parents=True)
    (root / "games" / "default").mkdir(parents=True)
    (root / "games" / "adventure").mkdir(parents=True)
    (root / "src" / "Core" / "Engine.cpp").write_text("// engine\n")
    (root / "src" / "RHI" / "README.md").write_text("# RHI\n")
    (root / "src" / "RHI" / "RHIDevice.h").write_text("// rhi\n")
    (root / "games" / "default" / "main.cpp").write_text("// default\n")
    (root / "games" / "adventure" / "main.cpp").write_text("// adventure\n")
    monkeypatch.setenv("OUTLAND_ROOT", str(root))
    return root


async def create_user_and_login(client, admin_headers, role, username):
    await client.post("/users/", headers=admin_headers, json={
        "username": username, "email": f"{username}@example.com",
        "password": "secret", "role": role,
    })
    login = await client.post("/auth/login", json={"email": f"{username}@example.com", "password": "secret"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def create_user_sync(test_client, admin_token, role, username):
    test_client.post("/users/", headers={"Authorization": f"Bearer {admin_token}"}, json={
        "username": username, "email": f"{username}@example.com", "password": "secret", "role": role,
    })
    login = test_client.post("/auth/login", json={"email": f"{username}@example.com", "password": "secret"})
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_engine_dev_blocked_from_rhi(source_tree, client, admin_headers):
    eng_headers = await create_user_and_login(client, admin_headers, "engine_dev", "engdev")
    response = await client.get("/fs/file?path=src/RHI/RHIDevice.h", headers=eng_headers)
    assert response.status_code == 403

    readme_response = await client.get("/fs/file?path=src/RHI/README.md", headers=eng_headers)
    assert readme_response.status_code == 200


@pytest.mark.asyncio
async def test_game_dev_only_sees_assigned_game(source_tree, client, admin_headers):
    game_response = await client.post("/games/", headers=admin_headers, json={
        "name": "Default Game", "folder_name": "default"
    })
    game_id = game_response.json()["id"]

    user_response = await client.post("/users/", headers=admin_headers, json={
        "username": "gduser", "email": "gduser@example.com", "password": "secret", "role": "game_dev"
    })
    user_id = user_response.json()["id"]
    await client.post("/assignments/", headers=admin_headers, json={"user_id": user_id, "game_id": game_id})

    login = await client.post("/auth/login", json={"email": "gduser@example.com", "password": "secret"})
    gd_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    tree_response = await client.get("/fs/tree?path=games", headers=gd_headers)
    folder_names = {entry["name"] for entry in tree_response.json()}
    assert "default" in folder_names
    assert "adventure" not in folder_names


@pytest.mark.asyncio
async def test_path_traversal_blocked(source_tree, client, admin_headers):
    response = await client.get("/fs/file?path=../etc/passwd", headers=admin_headers)
    assert response.status_code in (400, 403, 404)


@pytest.mark.asyncio
async def test_acl_rules_engine_dev(source_tree):
    rules = rules_for(make_user(Role.engine_dev), [])
    assert access_for(rules, "src/Core/Engine.cpp") == Access.write
    assert access_for(rules, "src/RHI/RHIDevice.h") == Access.none
    assert access_for(rules, "src/RHI/README.md") == Access.read



@pytest.mark.asyncio
async def test_websocket_file_change_notification(tmp_path, monkeypatch):
    root = tmp_path / "Outland"
    (root / "src" / "Core").mkdir(parents=True)
    (root / "src" / "Core" / "Engine.cpp").write_text("// base\n")
    monkeypatch.setenv("OUTLAND_ROOT", str(root))

    from database import Base, engine
    from main import app, bootstrap_admin

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await bootstrap_admin()

    with TestClient(app) as test_client:
        admin_login = test_client.post("/auth/login", json={"email": "admin@example.com", "password": "adminpass"})
        admin_token = admin_login.json()["access_token"]

        alice_token = create_user_sync(test_client, admin_token, "engine_dev", "alice")
        bob_token = create_user_sync(test_client, admin_token, "engine_dev", "bob")

        with test_client.websocket_connect(f"/fs/ws?token={bob_token}") as ws:
            test_client.put(
                "/fs/file",
                headers={"Authorization": f"Bearer {alice_token}"},
                json={"path": "src/Core/Engine.cpp", "content": "// edited by alice\n"},
            )
            event = ws.receive_json()
            assert event["type"] == "file.changed"
            assert event["path"] == "src/Core/Engine.cpp"
