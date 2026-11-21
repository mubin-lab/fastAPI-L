import os

# Must be set before the app (and its settings) is imported: fast bcrypt for tests.
os.environ["BCRYPT_ROUNDS"] = "4"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import security
from app.db.base import Base
from app.db.session import get_db, make_engine
from app.main import create_app
from app.models import Role, User

PASSWORD = "Str0ngPassw0rd!"
API = "/api/v1"


@pytest.fixture
async def session_factory():
    engine = make_engine("sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def client(session_factory):
    app = create_app()

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def register(client, email="user@example.com", password=PASSWORD, full_name="Test User"):
    return await client.post(f"{API}/auth/register",
                             json={"email": email, "password": password, "full_name": full_name})


async def login(client, email="user@example.com", password=PASSWORD):
    return await client.post(f"{API}/auth/login", data={"username": email, "password": password})


async def make_user(client, email="user@example.com") -> dict:
    """Register + login. Returns {"tokens": {...}, "headers": {...}, "user": {...}}."""
    r = await register(client, email)
    assert r.status_code == 201, r.text
    tokens = (await login(client, email)).json()
    return {"user": r.json(), "tokens": tokens, "headers": {"Authorization": f"Bearer {tokens['access_token']}"}}


@pytest.fixture
async def user_a(client):
    return await make_user(client, "a@example.com")


@pytest.fixture
async def user_b(client):
    return await make_user(client, "b@example.com")


@pytest.fixture
async def admin(client, session_factory):
    """Admins cannot self-register; insert one directly, then log in through the API."""
    async with session_factory() as s:
        s.add(User(email="admin@example.com", full_name="Admin",
                   hashed_password=security.hash_password(PASSWORD), role=Role.ADMIN.value))
        await s.commit()
    tokens = (await login(client, "admin@example.com")).json()
    return {"tokens": tokens, "headers": {"Authorization": f"Bearer {tokens['access_token']}"}}


async def create_project(client, headers, name="Proj", **extra) -> dict:
    r = await client.post(f"{API}/projects", json={"name": name, **extra}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


async def create_task(client, headers, project_id, title="Task", **extra) -> dict:
    r = await client.post(f"{API}/tasks", json={"project_id": project_id, "title": title, **extra}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()
