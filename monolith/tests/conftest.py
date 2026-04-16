import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["BOOTSTRAP_ADMIN_EMAIL"] = "admin@example.com"
os.environ["BOOTSTRAP_ADMIN_USERNAME"] = "admin"
os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "adminpass"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from database import Base, engine
from main import app, bootstrap_admin


@pytest_asyncio.fixture
async def client():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await bootstrap_admin()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def admin_token(client):
    response = await client.post("/auth/login",
                                 json={"email": "admin@example.com", "password": "adminpass"})
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest_asyncio.fixture
async def binaries_dir(tmp_path, monkeypatch):
    folder = tmp_path / "binaries"
    folder.mkdir()
    monkeypatch.setenv("BINARIES_DIR", str(folder))
    return folder
