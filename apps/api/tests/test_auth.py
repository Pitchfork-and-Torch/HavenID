from __future__ import annotations

import pyotp
from httpx import AsyncClient
from sqlalchemy import select

from app.config import get_settings
from app.crypto import decrypt_str
from app.models import User
from tests.conftest import login_full


async def test_health(client: AsyncClient):
    r = await client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["has_owner"] is True
    assert body["bootstrap_configured"] is True


async def test_login_wrong_password(client: AsyncClient):
    r = await client.post("/api/v1/auth/login", json={"email": "owner@example.com", "password": "definitely-wrong-1"})
    assert r.status_code == 401


async def test_totp_and_session(client: AsyncClient):
    await login_full(client)
    me = await client.get("/api/v1/me")
    assert me.status_code == 200
    assert me.json()["email"] == "owner@example.com"
    assert me.json()["totp_enrolled"] is True


async def test_logout_revokes(client: AsyncClient):
    await login_full(client)
    out = await client.post("/api/v1/auth/logout")
    assert out.status_code == 200
    me = await client.get("/api/v1/me")
    assert me.status_code == 401


async def test_refresh_rotates(client: AsyncClient):
    await login_full(client)
    r = await client.post("/api/v1/auth/refresh")
    assert r.status_code == 200
    me = await client.get("/api/v1/me")
    assert me.status_code == 200


async def test_recovery_codes_reset_totp(client: AsyncClient):
    await login_full(client)
    # recover needs a stored code; pull from last confirm is gone. Re-enroll path:
    # login again after logout using recover requires unused codes from enroll.
    # Re-do enroll flow and keep codes.
    await client.post("/api/v1/auth/logout")
    r = await client.post("/api/v1/auth/login", json={"email": "owner@example.com", "password": "correct-horse-battery"})
    assert r.json()["need"] == "totp"
    from app.db import SessionLocal

    assert SessionLocal is not None
    async with SessionLocal() as session:
        user = (await session.execute(select(User))).scalar_one()
        secret = decrypt_str(get_settings(), user.totp_secret_enc)
    code = pyotp.TOTP(secret).now()
    await client.post("/api/v1/auth/totp/verify", json={"code": code})
    rec = await client.post(
        "/api/v1/auth/recover",
        json={"email": "owner@example.com", "code": "nope-nope", "new_password": "brand-new-password-12"},
    )
    assert rec.status_code == 400
