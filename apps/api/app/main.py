from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sqlalchemy import select

from app import db as haven_db
from app.bootstrap import ensure_owner
from app.config import get_settings
from app.models import User
from app.routers import auth, core, voice
from app.security import check_csrf
from app.ws import router as ws_router

log = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    haven_db.configure_engine(settings)
    await haven_db.init_db()
    owner = None
    if haven_db.SessionLocal is not None:
        async with haven_db.SessionLocal() as session:
            owner = await ensure_owner(session, settings)
    log.info(
        "havenid ready bootstrap_configured=%s has_owner=%s",
        settings.bootstrap_configured,
        owner is not None,
    )
    yield


app = FastAPI(
    title="HavenID",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.haven_public_url.rstrip("/"),
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def csrf_and_headers(request: Request, call_next):
    try:
        check_csrf(request)
    except Exception as exc:
        from fastapi import HTTPException

        if isinstance(exc, HTTPException):
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        raise
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/health")
async def health():
    has_owner = False
    if haven_db.SessionLocal is not None:
        try:
            async with haven_db.SessionLocal() as session:
                has_owner = (await session.execute(select(User).limit(1))).scalar_one_or_none() is not None
        except Exception:
            has_owner = False
    settings = get_settings()
    return {
        "ok": True,
        "name": "HavenID",
        "has_owner": has_owner,
        "bootstrap_configured": settings.bootstrap_configured,
    }


app.include_router(auth.router)
app.include_router(core.router)
app.include_router(voice.router)
app.include_router(ws_router)
