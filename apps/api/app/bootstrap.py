from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.crypto import hash_password
from app.models import Policy, SettingRow, User

log = logging.getLogger("havenid")


async def ensure_owner(session: AsyncSession, settings: Settings) -> User | None:
    existing = (await session.execute(select(User).limit(1))).scalar_one_or_none()
    if existing:
        await _ensure_policy(session, existing)
        return existing
    if not settings.bootstrap_configured:
        log.warning("owner bootstrap skipped (BOOTSTRAP_EMAIL or BOOTSTRAP_PASSWORD missing)")
        return None
    user = User(
        email=settings.bootstrap_email.lower().strip(),
        password_hash=hash_password(settings.bootstrap_password),
        display_name="Owner",
    )
    session.add(user)
    await session.flush()
    await _ensure_policy(session, user)
    await session.commit()
    log.info("owner bootstrap created")
    return user


async def _ensure_policy(session: AsyncSession, user: User) -> None:
    policy = (await session.execute(select(Policy).where(Policy.user_id == user.id))).scalar_one_or_none()
    if not policy:
        session.add(Policy(user_id=user.id))
    prefs = (await session.execute(select(SettingRow).where(SettingRow.user_id == user.id))).scalar_one_or_none()
    if not prefs:
        session.add(SettingRow(user_id=user.id))
    await session.flush()
