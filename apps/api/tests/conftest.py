from __future__ import annotations

import os

os.environ["HAVEN_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["BOOTSTRAP_EMAIL"] = "owner@example.com"
os.environ["BOOTSTRAP_PASSWORD"] = "correct-horse-battery"
os.environ["HAVEN_SECRET_KEY"] = "test-secret-key-havenid-32bytes!!"
os.environ["HAVEN_DATA_KEY"] = "test-data-key-havenid-32bytes!!!"
os.environ["REDIS_URL"] = ""
os.environ["COOKIE_SECURE"] = "false"
os.environ["HAVEN_PUBLIC_URL"] = "http://localhost:3000"
os.environ["HAVEN_DOMAIN"] = "localhost"
os.environ["TWILIO_TRIAL"] = "true"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.db import configure_engine, init_db
from app.kv import MemoryKV, set_kv


@pytest_asyncio.fixture
async def client():
    get_settings.cache_clear()
    configure_engine(get_settings())
    await init_db(reset=True)
    set_kv(MemoryKV())
    from app.bootstrap import ensure_owner
    from app.db import SessionLocal
    from app.main import app

    assert SessionLocal is not None
    async with SessionLocal() as session:
        await ensure_owner(session, get_settings())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost:3000") as ac:
        yield ac
    from app.db import engine

    if engine is not None:
        await engine.dispose()


async def login_full(client: AsyncClient) -> None:
    import pyotp
    from app.config import get_settings
    from app.crypto import decrypt_str
    from app.db import SessionLocal
    from app.models import User
    from sqlalchemy import select

    r = await client.post("/api/v1/auth/login", json={"email": "owner@example.com", "password": "correct-horse-battery"})
    assert r.status_code == 200, r.text
    assert r.json()["need"] == "enroll_totp"
    en = await client.post("/api/v1/auth/totp/enroll")
    assert en.status_code == 200, en.text
    assert SessionLocal is not None
    async with SessionLocal() as session:
        user = (await session.execute(select(User))).scalar_one()
        secret = decrypt_str(get_settings(), user.totp_secret_enc)
    code = pyotp.TOTP(secret).now()
    conf = await client.post("/api/v1/auth/totp/confirm", json={"code": code})
    assert conf.status_code == 200, conf.text
    assert "recovery_codes" in conf.json()
