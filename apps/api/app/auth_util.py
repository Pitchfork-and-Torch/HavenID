from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.crypto import random_token, sha256_hex
from app.kv import get_kv
from app.models import Session, TrustedDevice, User, utcnow

ACCESS_COOKIE = "havenid_access"
REFRESH_COOKIE = "havenid_refresh"
PENDING_COOKIE = "havenid_pending"
DEVICE_COOKIE = "havenid_device"


def _cookie_kwargs(settings: Settings) -> dict:
    return {
        "httponly": True,
        "secure": settings.cookie_secure_effective,
        "samesite": "lax",
        "path": "/",
    }


def set_cookie(response: Response, name: str, value: str, max_age: int, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    response.set_cookie(name, value, max_age=max_age, **_cookie_kwargs(settings))


def clear_cookie(response: Response, name: str, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    response.delete_cookie(name, path="/")


def access_token(user_id: str, session_id: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "sid": session_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.access_ttl_seconds)).timestamp()),
    }
    return jwt.encode(payload, settings.haven_secret_key, algorithm="HS256")


def decode_access(token: str, settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    try:
        return jwt.decode(token, settings.haven_secret_key, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid session") from exc


async def issue_session(
    session: AsyncSession,
    response: Response,
    user: User,
    request: Request,
    device: TrustedDevice | None,
    settings: Settings | None = None,
) -> Session:
    settings = settings or get_settings()
    refresh = random_token(32)
    row = Session(
        user_id=user.id,
        device_id=device.id if device else None,
        refresh_hash=sha256_hex(refresh),
        expires_at=utcnow() + timedelta(seconds=settings.refresh_ttl_seconds),
        user_agent=(request.headers.get("user-agent") or "")[:400],
    )
    session.add(row)
    await session.flush()
    set_cookie(response, ACCESS_COOKIE, access_token(user.id, row.id, settings), settings.access_ttl_seconds, settings)
    set_cookie(response, REFRESH_COOKIE, refresh, settings.refresh_ttl_seconds, settings)
    clear_cookie(response, PENDING_COOKIE, settings)
    return row


async def current_user(request: Request, db: AsyncSession) -> User:
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not signed in")
    payload = decode_access(token)
    user = await db.get(User, payload["sub"])
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user missing")
    sess = await db.get(Session, payload.get("sid"))
    if not sess or sess.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="session revoked")
    return user


async def optional_user(request: Request, db: AsyncSession) -> User | None:
    if not request.cookies.get(ACCESS_COOKIE):
        return None
    try:
        return await current_user(request, db)
    except HTTPException:
        return None


async def set_pending(user_id: str, response: Response, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    token = random_token(24)
    await get_kv().setex(f"pending:{token}", settings.pending_ttl_seconds, user_id)
    set_cookie(response, PENDING_COOKIE, token, settings.pending_ttl_seconds, settings)
    return token


async def pending_user_id(request: Request) -> str:
    token = request.cookies.get(PENDING_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="login expired")
    user_id = await get_kv().get(f"pending:{token}")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="login expired")
    return user_id


async def touch_or_create_device(
    db: AsyncSession,
    user: User,
    request: Request,
    device_token: str | None,
) -> tuple[TrustedDevice, str]:
    token = device_token or random_token(24)
    hashed = sha256_hex(token)
    result = await db.execute(select(TrustedDevice).where(TrustedDevice.token_hash == hashed))
    device = result.scalar_one_or_none()
    ua = (request.headers.get("user-agent") or "")[:400]
    ip = request.client.host if request.client else ""
    if device and device.user_id == user.id and device.revoked_at is None:
        device.last_seen = utcnow()
        device.last_ip = ip
        device.user_agent = ua
        return device, token
    device = TrustedDevice(
        user_id=user.id,
        token_hash=hashed,
        name=_device_name(ua),
        user_agent=ua,
        last_ip=ip,
        last_seen=utcnow(),
    )
    db.add(device)
    await db.flush()
    return device, token


def _device_name(ua: str) -> str:
    ua_l = ua.lower()
    if "iphone" in ua_l:
        return "iPhone"
    if "ipad" in ua_l:
        return "iPad"
    if "android" in ua_l:
        return "Android"
    if "mac" in ua_l:
        return "Mac"
    if "windows" in ua_l:
        return "Windows"
    return "Browser"
