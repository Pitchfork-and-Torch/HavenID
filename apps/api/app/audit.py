from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def write_audit(
    session: AsyncSession,
    *,
    action: str,
    user_id: str | None = None,
    actor: str = "user",
    ip: str = "",
    meta: dict | None = None,
) -> None:
    session.add(
        AuditLog(
            user_id=user_id,
            actor=actor,
            action=action,
            ip=ip or "",
            meta=meta or {},
        )
    )
    await session.flush()
