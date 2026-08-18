from __future__ import annotations

import json
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai import classify_transcript
from app.audit import write_audit
from app.auth_util import current_user
from app.config import get_settings
from app.db import get_session
from app.kv import get_kv
from app.lists.match import first_hit
from app.models import CallLog, Contact, ListEntry, Policy, User
from app.phoneutil import is_anonymous, to_e164
from app.pipeline.engine import CallContext, PolicyView, decide, heuristic_score
from app.twiml import for_decision, record_screen

router = APIRouter(tags=["voice"])


def _xml(body: str) -> Response:
    return Response(content=body, media_type="application/xml")


def _validate_twilio(request: Request, form: dict) -> None:
    settings = get_settings()
    if settings.haven_env == "test":
        return
    token = settings.twilio_auth_token
    if not token:
        if request.headers.get("x-haven-simulate") == "1":
            return
        raise HTTPException(status_code=403, detail="twilio not configured")
    signature = request.headers.get("X-Twilio-Signature") or request.headers.get("x-twilio-signature")
    if not signature:
        raise HTTPException(status_code=403, detail="missing twilio signature")
    from twilio.request_validator import RequestValidator

    url = str(request.url)
    validator = RequestValidator(token)
    if not validator.validate(url, form, signature):
        raise HTTPException(status_code=403, detail="invalid twilio signature")


async def _owner(db: AsyncSession) -> User:
    user = (await db.execute(select(User).limit(1))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=503, detail="no owner")
    return user


async def _policy_view(db: AsyncSession, user: User) -> PolicyView:
    policy = (await db.execute(select(Policy).where(Policy.user_id == user.id))).scalar_one()
    return PolicyView(
        mode=policy.mode,  # type: ignore[arg-type]
        challenge_enabled=policy.challenge_enabled,
        ai_enabled=policy.ai_enabled,
        record_voicemail=policy.record_voicemail,
        recording_legal_ack=policy.recording_legal_ack,
        ring_strategy=policy.ring_strategy,
        reject_style=policy.reject_style,
        forward_e164=list(policy.forward_e164 or []),
    )


async def _hits(db: AsyncSession, user: User, number: str | None):
    rows = (await db.execute(select(ListEntry).where(ListEntry.user_id == user.id))).scalars().all()
    entries = [(r.list_kind, r.match_kind, r.pattern, r.note) for r in rows]
    return first_hit(number, entries, "allow"), first_hit(number, entries, "deny")


async def _is_contact(db: AsyncSession, user: User, number: str | None) -> bool:
    if not number:
        return False
    from app.models import ContactPhone

    row = (
        await db.execute(
            select(ContactPhone)
            .join(Contact, Contact.id == ContactPhone.contact_id)
            .where(Contact.user_id == user.id, ContactPhone.e164 == number)
        )
    ).scalar_one_or_none()
    return row is not None


async def _log(
    db: AsyncSession,
    user: User,
    sid: str,
    frm: str | None,
    to: str | None,
    decision,
) -> CallLog:
    existing = (await db.execute(select(CallLog).where(CallLog.provider_sid == sid))).scalar_one_or_none()
    if existing:
        existing.decision = decision.action
        existing.reason = decision.reason
        existing.spam_score = decision.spam_score
        existing.outcome = decision.action
        return existing
    row = CallLog(
        user_id=user.id,
        provider_sid=sid,
        direction="inbound",
        from_e164=frm,
        to_e164=to,
        decision=decision.action,
        reason=decision.reason,
        spam_score=decision.spam_score,
        outcome=decision.action,
    )
    db.add(row)
    return row


async def _run(db: AsyncSession, form: dict, stage: str, extra: dict | None = None) -> Response:
    settings = get_settings()
    user = await _owner(db)
    policy = await _policy_view(db, user)
    sid = form.get("CallSid") or form.get("call_sid") or "CA_unknown"
    raw_from = form.get("From") or form.get("from")
    raw_to = form.get("To") or form.get("to") or settings.twilio_phone_number
    frm = to_e164(raw_from)
    to = to_e164(raw_to)
    allow, deny = await _hits(db, user, frm)
    known = await _is_contact(db, user, frm)
    score = heuristic_score(is_anonymous=is_anonymous(raw_from), is_contact=known)
    extra = extra or {}
    ctx = CallContext(
        from_e164=frm,
        to_e164=to,
        call_sid=sid,
        is_anonymous=is_anonymous(raw_from),
        is_contact=known,
        allow_hit=allow,
        deny_hit=deny,
        policy=policy,
        trial=settings.twilio_trial,
        ai_available=bool(settings.xai_api_key),
        heuristic_score=score,
        gather_digits=form.get("Digits") or extra.get("digits"),
        challenge_passed=bool(extra.get("challenge_passed")),
        ai_label=extra.get("ai_label"),
        stage=stage,
    )
    decision = decide(ctx)
    await _log(db, user, sid, frm, to, decision)
    await get_kv().setex(
        f"call:{sid}",
        3600,
        json.dumps({"action": decision.action, "reason": decision.reason, "from": frm}),
    )
    await write_audit(
        db,
        action="call_decision",
        user_id=user.id,
        actor="pipeline",
        meta={"sid": sid, "from": frm, "decision": decision.action, "reason": decision.reason, "stage": stage},
    )
    await db.commit()

    if decision.needs_record and not settings.twilio_trial:
        return _xml(record_screen(settings.haven_public_url))
    xml = for_decision(
        decision.action,
        public_url=settings.haven_public_url,
        forwards=policy.forward_e164,
        simultaneous=policy.ring_strategy == "simultaneous",
    )
    return _xml(xml)


@router.post("/voice/inbound")
async def inbound(request: Request, db: AsyncSession = Depends(get_session)):
    form = dict(await request.form())
    _validate_twilio(request, form)
    return await _run(db, form, "inbound")


@router.post("/voice/gather")
async def gather(request: Request, db: AsyncSession = Depends(get_session)):
    form = dict(await request.form())
    _validate_twilio(request, form)
    return await _run(db, form, "gather")


@router.post("/voice/screen")
async def screen(request: Request, db: AsyncSession = Depends(get_session)):
    form = dict(await request.form())
    _validate_twilio(request, form)
    settings = get_settings()
    transcript = form.get("TranscriptionText") or ""
    label = await classify_transcript(settings, transcript) if transcript else None
    return await _run(db, form, "ai", {"ai_label": label, "challenge_passed": True})


@router.post("/voice/recording")
async def recording(request: Request, db: AsyncSession = Depends(get_session)):
    form = dict(await request.form())
    _validate_twilio(request, form)
    sid = form.get("CallSid") or "CA_unknown"
    url = form.get("RecordingUrl") or ""
    row = (await db.execute(select(CallLog).where(CallLog.provider_sid == sid))).scalar_one_or_none()
    if row:
        row.recording_path = url
        row.transcript = form.get("TranscriptionText") or row.transcript
        row.outcome = "voicemail"
        await db.commit()
        settings = get_settings()
        user = await db.get(User, row.user_id)
        if user and settings.smtp_host:
            from app.notify import send_mail

            send_mail(
                settings,
                user.email,
                "[HavenID] Voicemail",
                f"Voicemail from {row.from_e164 or 'unknown'}.\n{row.transcript}",
            )
    return _xml('<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>')


@router.post("/voice/status")
async def status_cb(request: Request, db: AsyncSession = Depends(get_session)):
    form = dict(await request.form())
    _validate_twilio(request, form)
    sid = form.get("CallSid")
    if not sid:
        return {"ok": True}
    row = (await db.execute(select(CallLog).where(CallLog.provider_sid == sid))).scalar_one_or_none()
    if row:
        try:
            row.duration_sec = int(form.get("CallDuration") or 0)
        except ValueError:
            pass
        if form.get("CallStatus"):
            row.outcome = str(form.get("CallStatus"))
        await db.commit()
    return {"ok": True}


class SimulateIn(BaseModel):
    frm: str | None = None
    to: str | None = None
    digits: str | None = None
    stage: str = "inbound"
    call_sid: str | None = None


@router.post("/api/v1/voice/simulate")
async def simulate(body: SimulateIn, request: Request, db: AsyncSession = Depends(get_session)):
    await current_user(request, db)
    form = {
        "CallSid": body.call_sid or "CA_sim",
        "From": body.frm or "",
        "To": body.to or get_settings().twilio_phone_number or "+15555550100",
        "Digits": body.digits or "",
    }
    resp = await _run(db, form, body.stage)
    return JSONResponse({"twiml": resp.body.decode("utf-8") if isinstance(resp.body, (bytes, bytearray)) else str(resp.body)})
