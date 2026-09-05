"""Smoke login + dashboard APIs through the Next.js proxy. No secrets printed."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT / "apps" / "api")
sys.path.insert(0, str(ROOT / "apps" / "api"))

from dotenv import dotenv_values
from httpx import Client
import pyotp
from sqlalchemy import create_engine, text

env = {}
for p in (ROOT / ".env", ROOT / "apps" / "api" / ".env"):
    if p.exists():
        env.update({k: v for k, v in dotenv_values(p).items() if v is not None})

email = (env.get("BOOTSTRAP_EMAIL") or "").strip()
password = env.get("BOOTSTRAP_PASSWORD") or ""
db_url = env.get("DATABASE_URL") or "sqlite+aiosqlite:///./havenid.db"
public = env.get("HAVEN_PUBLIC_URL") or ""

print("email_ok", "@" in email and "." in email.split("@")[-1])
print("password_set", bool(password) and len(password) >= 8)
print("public_url_host", public.split("://")[-1].split("/")[0] if public else "(empty)")

sync_url = db_url.replace("sqlite+aiosqlite", "sqlite").replace("postgresql+asyncpg", "postgresql")
if sync_url.startswith("sqlite:///./"):
    sync_url = "sqlite:///" + str(ROOT / "apps" / "api" / "havenid.db")

eng = create_engine(sync_url)
with eng.connect() as cx:
    row = cx.execute(text("SELECT email, totp_confirmed_at IS NOT NULL, length(totp_secret_enc) FROM users LIMIT 1")).fetchone()
if not row:
    print("FAIL no owner row")
    sys.exit(1)
db_email, totp_on, secret_len = row
print("owner_email_match", db_email.lower() == email.lower())
print("totp_enrolled", bool(totp_on))
print("totp_secret_present", bool(secret_len))

from app.config import get_settings
from app.crypto import decrypt_str
from app.models import User
from sqlalchemy.orm import Session as SASession

# decrypt via ORM using same settings as API
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# Use aiosqlite file through sync sqlite3 + app crypto
import sqlite3
from app.crypto import decrypt_str as dec
from app.models import User as UserModel

# Pull encrypted secret without printing it
enc = None
with eng.connect() as cx:
    enc = cx.execute(text("SELECT totp_secret_enc FROM users LIMIT 1")).scalar()

code = None
if enc:
    try:
        secret = dec(get_settings(), enc)
        code = pyotp.TOTP(secret).now()
        print("totp_code_ready", True)
    except Exception as exc:
        print("totp_decrypt_fail", type(exc).__name__)
else:
    print("totp_code_ready", False)

base = "http://127.0.0.1:3000"
with Client(base_url=base, timeout=10.0, follow_redirects=True) as c:
    login = c.post("/api/v1/auth/login", json={"email": email, "password": password})
    print("login_status", login.status_code)
    if login.status_code != 200:
        detail = ""
        try:
            detail = str(login.json().get("detail", ""))[:80]
        except Exception:
            detail = login.text[:80]
        print("login_detail", detail)
        sys.exit(1)
    need = login.json().get("need")
    print("login_need", need)
    cookies = list(c.cookies.keys())
    print("cookies_after_login", ",".join(sorted(cookies)) or "(none)")

    if need == "enroll_totp":
        en = c.post("/api/v1/auth/totp/enroll")
        print("enroll_status", en.status_code)
        if en.status_code != 200:
            print("enroll_detail", str(en.text)[:80])
            sys.exit(1)
        secret = en.json()["secret"]
        code = pyotp.TOTP(secret).now()
        conf = c.post("/api/v1/auth/totp/confirm", json={"code": code})
        print("confirm_status", conf.status_code)
        print("recovery_codes", len(conf.json().get("recovery_codes") or []))
    elif need == "totp":
        if not code:
            print("FAIL need totp but could not mint code")
            sys.exit(1)
        ver = c.post("/api/v1/auth/totp/verify", json={"code": code})
        print("verify_status", ver.status_code)
        if ver.status_code != 200:
            print("verify_detail", str(ver.text)[:80])
            sys.exit(1)

    print("cookies_after_totp", ",".join(sorted(c.cookies.keys())) or "(none)")
    me = c.get("/api/v1/me")
    print("me_status", me.status_code)
    if me.status_code == 200:
        body = me.json()
        print("me_totp", body.get("totp_enrolled"))
        print("me_email_host", (body.get("email") or "").split("@")[-1])
    else:
        print("me_detail", str(me.text)[:120])
        sys.exit(1)

    ov = c.get("/api/v1/overview")
    print("overview_status", ov.status_code)
    if ov.status_code == 200:
        o = ov.json()
        print("overview_calls", o.get("calls_total"), "contacts", o.get("contacts"), "mode", o.get("policy_mode"))

    sim = c.post("/api/v1/voice/simulate", json={"frm": "+15551239999", "stage": "inbound"})
    print("simulate_status", sim.status_code)
    if sim.status_code == 200:
        print("simulate_has_twiml", bool(sim.json().get("twiml")))

    calls = c.get("/api/v1/calls")
    print("calls_status", calls.status_code, "n", len((calls.json() or {}).get("items") or []) if calls.status_code == 200 else 0)

    login_page = c.get("/login")
    print("login_page", login_page.status_code)
    dash = c.get("/")
    print("dash_page", dash.status_code)

print("SMOKE_OK")
