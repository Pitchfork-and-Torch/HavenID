"""Create the owner row if the users table is empty. Prints no secrets."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps" / "api"
os.chdir(API)
sys.path.insert(0, str(API))


async def main() -> int:
    from app.bootstrap import ensure_owner
    from app.config import get_settings
    from app.db import SessionLocal, configure_engine, init_db

    get_settings.cache_clear()
    settings = get_settings()
    print("bootstrap_configured", settings.bootstrap_configured)
    if not settings.bootstrap_configured:
        print("FAIL bootstrap env not loaded")
        return 1
    configure_engine(settings)
    await init_db()
    if SessionLocal is None:
        print("FAIL no session factory")
        return 1
    async with SessionLocal() as session:
        user = await ensure_owner(session, settings)
    print("owner", "yes" if user else "no")
    return 0 if user else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
