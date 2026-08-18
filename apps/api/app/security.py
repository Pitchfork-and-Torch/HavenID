from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.config import Settings, get_settings
from app.kv import get_kv


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


def check_csrf(request: Request, settings: Settings | None = None) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    path = request.url.path
    if path.startswith("/voice/") or path.startswith("/api/health"):
        return
    settings = settings or get_settings()
    origin = request.headers.get("origin") or ""
    site = request.headers.get("sec-fetch-site", "")
    if site in {"same-origin", "same-site", "none", ""}:
        if not origin:
            return
    allowed = {
        settings.haven_public_url.rstrip("/"),
        f"https://{settings.haven_domain}",
        f"http://{settings.haven_domain}",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    }
    if origin.rstrip("/") in allowed:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="csrf origin rejected")


async def rate_limit(key: str, limit: int, window: int = 60) -> None:
    count = await get_kv().incr(f"rl:{key}", window)
    if count > limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="rate limited")
