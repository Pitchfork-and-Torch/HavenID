from __future__ import annotations

import json
import zipfile
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.audit import write_audit
from app.auth_util import current_user
from app.config import get_settings
from app.contacts_vcard import contacts_from_vcard, contacts_to_vcard
from app.crypto import hash_password, sha256_hex, verify_password
from app.db import get_session
from app.lists.match import normalize_pattern
from app.models import (
    AuditLog,
    CallLog,
    Contact,
    ContactEmail,
    ContactPhone,
    ListEntry,
    Policy,
    Session,
    SettingRow,
    TrustedDevice,
    User,
    WebAuthnCredential,
    new_id,
    utcnow,
)
from app.phoneutil import to_e164
from app.security import client_ip

router = APIRouter(prefix="/api/v1", tags=["core"])


async def owner(request: Request, db: AsyncSession = Depends(get_session)) -> User:
    return await current_user(request, db)


class ProfileIn(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    phone_e164: str | None = None
    password: str | None = Field(default=None, min_length=12, max_length=200)
    current_password: str | None = None


class ContactIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)
    given_name: str = ""
    family_name: str = ""
    org: str = ""
    notes: str = ""
    phones: list[dict] = Field(default_factory=list)
    emails: list[dict] = Field(default_factory=list)


class ListIn(BaseModel):
    list_kind: str
    match_kind: str = "exact"
    pattern: str
    note: str = ""


class PolicyIn(BaseModel):
    mode: str | None = None
    challenge_enabled: bool | None = None
    ai_enabled: bool | None = None
    record_voicemail: bool | None = None
    recording_legal_ack: bool | None = None
    ring_strategy: str | None = None
    reject_style: str | None = None
    forward_e164: list[str] | None = None
    public_spam_lists: bool | None = None


class SettingsIn(BaseModel):
    notify_email_voicemail: bool | None = None
    notify_email_blocked: bool | None = None
    theme: str | None = None


class DeviceNameIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class DeleteIn(BaseModel):
    confirm: str


def _contact_out(c: Contact) -> dict:
    return {
        "id": c.id,
        "display_name": c.display_name,
        "given_name": c.given_name,
        "family_name": c.family_name,
        "org": c.org,
        "notes": c.notes,
        "etag": c.etag,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        "phones": [{"id": p.id, "e164": p.e164, "label": p.label, "preferred": p.preferred} for p in c.phones],
        "emails": [{"id": e.id, "address": e.address, "label": e.label} for e in c.emails],
    }


def _apply_phones(contact: Contact, phones: list[dict]) -> None:
    contact.phones.clear()
    for item in phones:
        raw = item.get("e164") or item.get("number") or ""
        e164 = to_e164(raw)
        if not e164:
            continue
        contact.phones.append(
            ContactPhone(
                e164=e164,
                label=str(item.get("label") or "mobile")[:40],
                preferred=bool(item.get("preferred")),
            )
        )


@router.get("/me")
async def me(user: User = Depends(owner), db: AsyncSession = Depends(get_session)):
    settings = get_settings()
    policy = (await db.execute(select(Policy).where(Policy.user_id == user.id))).scalar_one_or_none()
    prefs = (await db.execute(select(SettingRow).where(SettingRow.user_id == user.id))).scalar_one_or_none()
    passkeys = (await db.execute(select(func.count()).select_from(WebAuthnCredential).where(WebAuthnCredential.user_id == user.id))).scalar_one()
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "phone_e164": user.phone_e164,
        "totp_enrolled": user.totp_confirmed_at is not None,
        "passkey_count": int(passkeys or 0),
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "twilio_configured": bool(settings.twilio_account_sid and settings.twilio_auth_token),
        "twilio_phone": settings.twilio_phone_number or "",
        "twilio_trial": settings.twilio_trial,
        "ai_available": bool(settings.xai_api_key),
        "smtp_configured": bool(settings.smtp_host),
        "policy": _policy_out(policy) if policy else None,
        "prefs": {
            "notify_email_voicemail": prefs.notify_email_voicemail if prefs else True,
            "notify_email_blocked": prefs.notify_email_blocked if prefs else False,
            "theme": prefs.theme if prefs else "dark",
        },
    }


@router.patch("/me")
async def patch_me(body: ProfileIn, request: Request, user: User = Depends(owner), db: AsyncSession = Depends(get_session)):
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.phone_e164 is not None:
        user.phone_e164 = to_e164(body.phone_e164)
    if body.password:
        if not body.current_password or not verify_password(user.password_hash, body.current_password):
            raise HTTPException(status_code=400, detail="current password required")
        user.password_hash = hash_password(body.password)
        await write_audit(db, action="password_change", user_id=user.id, ip=client_ip(request))
    await db.commit()
    return {"ok": True}


@router.get("/me/export")
async def export_me(user: User = Depends(owner), db: AsyncSession = Depends(get_session)):
    contacts = (
        await db.execute(select(Contact).where(Contact.user_id == user.id).options(selectinload(Contact.phones), selectinload(Contact.emails)))
    ).scalars().all()
    calls = (await db.execute(select(CallLog).where(CallLog.user_id == user.id).order_by(CallLog.started_at.desc()).limit(5000))).scalars().all()
    audits = (await db.execute(select(AuditLog).where(AuditLog.user_id == user.id).order_by(AuditLog.created_at.desc()).limit(5000))).scalars().all()
    lists = (await db.execute(select(ListEntry).where(ListEntry.user_id == user.id))).scalars().all()
    payload = {
        "profile": {"email": user.email, "display_name": user.display_name, "phone_e164": user.phone_e164},
        "contacts": [_contact_out(c) for c in contacts],
        "calls": [_call_out(c) for c in calls],
        "lists": [_list_out(x) for x in lists],
        "audit": [
            {"action": a.action, "actor": a.actor, "ip": a.ip, "meta": a.meta, "created_at": a.created_at.isoformat()}
            for a in audits
        ],
    }
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("havenid-export.json", json.dumps(payload, indent=2))
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=havenid-export.zip"},
    )


@router.delete("/me")
async def delete_me(body: DeleteIn, request: Request, user: User = Depends(owner), db: AsyncSession = Depends(get_session)):
    if body.confirm != user.email:
        raise HTTPException(status_code=400, detail="type your email to confirm")
    await write_audit(db, action="account_delete", user_id=user.id, ip=client_ip(request), meta={"email": user.email})
    await db.delete(user)
    await db.commit()
    return {"ok": True}


@router.get("/devices")
async def devices(user: User = Depends(owner), db: AsyncSession = Depends(get_session)):
    rows = (
        await db.execute(select(TrustedDevice).where(TrustedDevice.user_id == user.id).order_by(TrustedDevice.last_seen.desc()))
    ).scalars().all()
    sessions = (
        await db.execute(select(Session).where(Session.user_id == user.id, Session.revoked_at.is_(None)))
    ).scalars().all()
    return {
        "devices": [
            {
                "id": d.id,
                "name": d.name,
                "user_agent": d.user_agent,
                "last_ip": d.last_ip,
                "last_seen": d.last_seen.isoformat() if d.last_seen else None,
                "revoked": d.revoked_at is not None,
            }
            for d in rows
        ],
        "sessions": [
            {
                "id": s.id,
                "device_id": s.device_id,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "expires_at": s.expires_at.isoformat() if s.expires_at else None,
                "user_agent": s.user_agent,
            }
            for s in sessions
        ],
    }


@router.patch("/devices/{device_id}")
async def rename_device(device_id: str, body: DeviceNameIn, user: User = Depends(owner), db: AsyncSession = Depends(get_session)):
    device = await db.get(TrustedDevice, device_id)
    if not device or device.user_id != user.id:
        raise HTTPException(status_code=404, detail="not found")
    device.name = body.name
    await db.commit()
    return {"ok": True}


@router.delete("/devices/{device_id}")
async def revoke_device(device_id: str, request: Request, user: User = Depends(owner), db: AsyncSession = Depends(get_session)):
    device = await db.get(TrustedDevice, device_id)
    if not device or device.user_id != user.id:
        raise HTTPException(status_code=404, detail="not found")
    device.revoked_at = utcnow()
    sessions = (
        await db.execute(select(Session).where(Session.device_id == device.id, Session.revoked_at.is_(None)))
    ).scalars()
    for sess in sessions:
        sess.revoked_at = utcnow()
    await write_audit(db, action="device_revoke", user_id=user.id, ip=client_ip(request), meta={"device_id": device_id})
    await db.commit()
    return {"ok": True}


@router.get("/audit")
async def audit(user: User = Depends(owner), db: AsyncSession = Depends(get_session), limit: int = 100):
    rows = (
        await db.execute(
            select(AuditLog).where(AuditLog.user_id == user.id).order_by(AuditLog.created_at.desc()).limit(min(limit, 500))
        )
    ).scalars().all()
    return {
        "items": [
            {
                "id": a.id,
                "action": a.action,
                "actor": a.actor,
                "ip": a.ip,
                "meta": a.meta,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in rows
        ]
    }


@router.get("/contacts")
async def list_contacts(q: str | None = None, user: User = Depends(owner), db: AsyncSession = Depends(get_session)):
    stmt = select(Contact).where(Contact.user_id == user.id).options(selectinload(Contact.phones), selectinload(Contact.emails))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Contact.display_name.ilike(like),
                Contact.org.ilike(like),
                Contact.notes.ilike(like),
            )
        )
    rows = (await db.execute(stmt.order_by(Contact.display_name))).scalars().all()
    return {"items": [_contact_out(c) for c in rows]}


@router.post("/contacts")
async def create_contact(body: ContactIn, request: Request, user: User = Depends(owner), db: AsyncSession = Depends(get_session)):
    contact = Contact(
        user_id=user.id,
        display_name=body.display_name,
        given_name=body.given_name,
        family_name=body.family_name,
        org=body.org,
        notes=body.notes,
        etag=new_id(),
    )
    _apply_phones(contact, body.phones)
    for item in body.emails:
        addr = str(item.get("address") or "").strip()
        if addr:
            contact.emails.append(ContactEmail(address=addr, label=str(item.get("label") or "home")[:40]))
    db.add(contact)
    await write_audit(db, action="contact_create", user_id=user.id, ip=client_ip(request), meta={"name": body.display_name})
    await db.commit()
    await db.refresh(contact)
    loaded = (
        await db.execute(select(Contact).where(Contact.id == contact.id).options(selectinload(Contact.phones), selectinload(Contact.emails)))
    ).scalar_one()
    return _contact_out(loaded)


@router.patch("/contacts/{contact_id}")
async def patch_contact(contact_id: str, body: ContactIn, user: User = Depends(owner), db: AsyncSession = Depends(get_session)):
    contact = (
        await db.execute(
            select(Contact).where(Contact.id == contact_id, Contact.user_id == user.id).options(
                selectinload(Contact.phones), selectinload(Contact.emails)
            )
        )
    ).scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="not found")
    contact.display_name = body.display_name
    contact.given_name = body.given_name
    contact.family_name = body.family_name
    contact.org = body.org
    contact.notes = body.notes
    contact.etag = new_id()
    _apply_phones(contact, body.phones)
    contact.emails.clear()
    for item in body.emails:
        addr = str(item.get("address") or "").strip()
        if addr:
            contact.emails.append(ContactEmail(address=addr, label=str(item.get("label") or "home")[:40]))
    await db.commit()
    loaded = (
        await db.execute(select(Contact).where(Contact.id == contact.id).options(selectinload(Contact.phones), selectinload(Contact.emails)))
    ).scalar_one()
    return _contact_out(loaded)


@router.delete("/contacts/{contact_id}")
async def delete_contact(contact_id: str, user: User = Depends(owner), db: AsyncSession = Depends(get_session)):
    contact = await db.get(Contact, contact_id)
    if not contact or contact.user_id != user.id:
        raise HTTPException(status_code=404, detail="not found")
    await db.delete(contact)
    await db.commit()
    return {"ok": True}


@router.get("/contacts/export")
async def export_contacts(user: User = Depends(owner), db: AsyncSession = Depends(get_session)):
    rows = (
        await db.execute(
            select(Contact).where(Contact.user_id == user.id).options(selectinload(Contact.phones), selectinload(Contact.emails))
        )
    ).scalars().all()
    text = contacts_to_vcard(rows)
    return Response(content=text, media_type="text/vcard", headers={"Content-Disposition": "attachment; filename=contacts.vcf"})


class VcardIn(BaseModel):
    vcard: str


@router.post("/contacts/import")
async def import_contacts(body: VcardIn, request: Request, user: User = Depends(owner), db: AsyncSession = Depends(get_session)):
    parsed = contacts_from_vcard(body.vcard)
    created = 0
    for item in parsed:
        contact = Contact(user_id=user.id, **{k: item[k] for k in ("display_name", "given_name", "family_name", "org", "notes")})
        _apply_phones(contact, item.get("phones") or [])
        for em in item.get("emails") or []:
            contact.emails.append(ContactEmail(address=em["address"], label=em.get("label") or "home"))
        db.add(contact)
        created += 1
    await write_audit(db, action="contacts_import", user_id=user.id, ip=client_ip(request), meta={"count": created})
    await db.commit()
    return {"ok": True, "imported": created}


def _call_out(c: CallLog) -> dict:
    return {
        "id": c.id,
        "provider_sid": c.provider_sid,
        "direction": c.direction,
        "from_e164": c.from_e164,
        "to_e164": c.to_e164,
        "started_at": c.started_at.isoformat() if c.started_at else None,
        "duration_sec": c.duration_sec,
        "outcome": c.outcome,
        "decision": c.decision,
        "reason": c.reason,
        "spam_score": c.spam_score,
        "transcript": c.transcript,
        "has_recording": bool(c.recording_path),
    }


@router.get("/calls")
async def list_calls(
    q: str | None = None,
    outcome: str | None = None,
    decision: str | None = None,
    user: User = Depends(owner),
    db: AsyncSession = Depends(get_session),
    limit: int = 100,
):
    stmt = select(CallLog).where(CallLog.user_id == user.id)
    if outcome:
        stmt = stmt.where(CallLog.outcome == outcome)
    if decision:
        stmt = stmt.where(CallLog.decision == decision)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(CallLog.from_e164.ilike(like), CallLog.transcript.ilike(like), CallLog.reason.ilike(like)))
    rows = (await db.execute(stmt.order_by(CallLog.started_at.desc()).limit(min(limit, 500)))).scalars().all()
    return {"items": [_call_out(c) for c in rows]}


@router.post("/calls/{call_id}/mark-spam")
async def mark_spam(call_id: str, request: Request, user: User = Depends(owner), db: AsyncSession = Depends(get_session)):
    call = await db.get(CallLog, call_id)
    if not call or call.user_id != user.id:
        raise HTTPException(status_code=404, detail="not found")
    if call.from_e164:
        exists = (
            await db.execute(
                select(ListEntry).where(
                    ListEntry.user_id == user.id,
                    ListEntry.list_kind == "deny",
                    ListEntry.pattern == call.from_e164,
                )
            )
        ).scalar_one_or_none()
        if not exists:
            db.add(ListEntry(user_id=user.id, list_kind="deny", match_kind="exact", pattern=call.from_e164, note="marked from call log"))
    call.decision = "marked_spam"
    await write_audit(db, action="mark_spam", user_id=user.id, ip=client_ip(request), meta={"from": call.from_e164})
    await db.commit()
    return {"ok": True}


@router.post("/calls/{call_id}/mark-ok")
async def mark_ok(call_id: str, request: Request, user: User = Depends(owner), db: AsyncSession = Depends(get_session)):
    call = await db.get(CallLog, call_id)
    if not call or call.user_id != user.id:
        raise HTTPException(status_code=404, detail="not found")
    if call.from_e164:
        exists = (
            await db.execute(
                select(ListEntry).where(
                    ListEntry.user_id == user.id,
                    ListEntry.list_kind == "allow",
                    ListEntry.pattern == call.from_e164,
                )
            )
        ).scalar_one_or_none()
        if not exists:
            db.add(ListEntry(user_id=user.id, list_kind="allow", match_kind="exact", pattern=call.from_e164, note="marked ok"))
    call.decision = "marked_ok"
    await write_audit(db, action="mark_ok", user_id=user.id, ip=client_ip(request), meta={"from": call.from_e164})
    await db.commit()
    return {"ok": True}


def _list_out(e: ListEntry) -> dict:
    return {
        "id": e.id,
        "list_kind": e.list_kind,
        "match_kind": e.match_kind,
        "pattern": e.pattern,
        "note": e.note,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


@router.get("/lists")
async def list_entries(user: User = Depends(owner), db: AsyncSession = Depends(get_session)):
    rows = (await db.execute(select(ListEntry).where(ListEntry.user_id == user.id).order_by(ListEntry.created_at.desc()))).scalars().all()
    return {"items": [_list_out(x) for x in rows]}


@router.post("/lists")
async def add_list(body: ListIn, request: Request, user: User = Depends(owner), db: AsyncSession = Depends(get_session)):
    if body.list_kind not in {"allow", "deny"}:
        raise HTTPException(status_code=400, detail="list_kind must be allow or deny")
    if body.match_kind not in {"exact", "prefix"}:
        raise HTTPException(status_code=400, detail="match_kind must be exact or prefix")
    pattern = normalize_pattern(body.pattern)
    if len(pattern) < 4:
        raise HTTPException(status_code=400, detail="pattern too short")
    row = ListEntry(user_id=user.id, list_kind=body.list_kind, match_kind=body.match_kind, pattern=pattern, note=body.note[:200])
    db.add(row)
    await write_audit(db, action="list_add", user_id=user.id, ip=client_ip(request), meta={"kind": body.list_kind, "pattern": pattern})
    await db.commit()
    await db.refresh(row)
    return _list_out(row)


@router.delete("/lists/{entry_id}")
async def delete_list(entry_id: str, user: User = Depends(owner), db: AsyncSession = Depends(get_session)):
    row = await db.get(ListEntry, entry_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="not found")
    await db.delete(row)
    await db.commit()
    return {"ok": True}


def _policy_out(p: Policy) -> dict:
    return {
        "mode": p.mode,
        "challenge_enabled": p.challenge_enabled,
        "ai_enabled": p.ai_enabled,
        "record_voicemail": p.record_voicemail,
        "recording_legal_ack": p.recording_legal_ack,
        "ring_strategy": p.ring_strategy,
        "reject_style": p.reject_style,
        "forward_e164": p.forward_e164 or [],
        "public_spam_lists": p.public_spam_lists,
    }


@router.get("/policy")
async def get_policy(user: User = Depends(owner), db: AsyncSession = Depends(get_session)):
    policy = (await db.execute(select(Policy).where(Policy.user_id == user.id))).scalar_one()
    return _policy_out(policy)


@router.patch("/policy")
async def patch_policy(body: PolicyIn, request: Request, user: User = Depends(owner), db: AsyncSession = Depends(get_session)):
    policy = (await db.execute(select(Policy).where(Policy.user_id == user.id))).scalar_one()
    data = body.model_dump(exclude_none=True)
    if "mode" in data and data["mode"] not in {"strict", "balanced", "permissive"}:
        raise HTTPException(status_code=400, detail="invalid mode")
    if "forward_e164" in data:
        cleaned = []
        for n in data["forward_e164"]:
            e164 = to_e164(n)
            if e164:
                cleaned.append(e164)
        data["forward_e164"] = cleaned
    for key, value in data.items():
        setattr(policy, key, value)
    await write_audit(db, action="policy_update", user_id=user.id, ip=client_ip(request), meta=data)
    await db.commit()
    return _policy_out(policy)


@router.patch("/settings")
async def patch_settings(body: SettingsIn, user: User = Depends(owner), db: AsyncSession = Depends(get_session)):
    prefs = (await db.execute(select(SettingRow).where(SettingRow.user_id == user.id))).scalar_one()
    data = body.model_dump(exclude_none=True)
    for key, value in data.items():
        setattr(prefs, key, value)
    await db.commit()
    return {"ok": True}


@router.get("/overview")
async def overview(user: User = Depends(owner), db: AsyncSession = Depends(get_session)):
    settings = get_settings()
    total = (await db.execute(select(func.count()).select_from(CallLog).where(CallLog.user_id == user.id))).scalar_one()
    blocked = (
        await db.execute(
            select(func.count()).select_from(CallLog).where(
                CallLog.user_id == user.id,
                CallLog.decision.in_(["reject_silent", "reject_polite", "marked_spam"]),
            )
        )
    ).scalar_one()
    contacts = (await db.execute(select(func.count()).select_from(Contact).where(Contact.user_id == user.id))).scalar_one()
    devices = (
        await db.execute(
            select(func.count()).select_from(TrustedDevice).where(
                TrustedDevice.user_id == user.id, TrustedDevice.revoked_at.is_(None)
            )
        )
    ).scalar_one()
    recent = (
        await db.execute(select(CallLog).where(CallLog.user_id == user.id).order_by(CallLog.started_at.desc()).limit(10))
    ).scalars().all()
    policy = (await db.execute(select(Policy).where(Policy.user_id == user.id))).scalar_one_or_none()
    return {
        "calls_total": int(total or 0),
        "calls_blocked": int(blocked or 0),
        "contacts": int(contacts or 0),
        "devices": int(devices or 0),
        "policy_mode": policy.mode if policy else "balanced",
        "twilio_ok": bool(settings.twilio_account_sid),
        "twilio_phone": settings.twilio_phone_number or "",
        "twilio_trial": settings.twilio_trial,
        "ai_available": bool(settings.xai_api_key),
        "recent": [_call_out(c) for c in recent],
    }
