from __future__ import annotations

import io
import pyotp
import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import write_audit
from app.auth_util import (
    ACCESS_COOKIE,
    DEVICE_COOKIE,
    REFRESH_COOKIE,
    clear_cookie,
    current_user,
    issue_session,
    pending_user_id,
    set_cookie,
    set_pending,
    touch_or_create_device,
)
from app.config import get_settings
from app.crypto import decrypt_str, encrypt_str, hash_password, random_token, sha256_hex, verify_password
from app.db import get_session
from app.kv import get_kv
from app.models import RecoveryCode, Session, TrustedDevice, User, WebAuthnCredential, as_utc, utcnow
from app.security import client_ip, rate_limit

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class TotpIn(BaseModel):
    code: str = Field(min_length=6, max_length=12)


class RecoverIn(BaseModel):
    email: EmailStr
    code: str
    new_password: str = Field(min_length=12, max_length=200)


def _codes() -> list[str]:
    return [random_token(5).replace("_", "x").replace("-", "y")[:10] for _ in range(10)]


@router.post("/login")
async def login(body: LoginIn, request: Request, response: Response, db: AsyncSession = Depends(get_session)):
    await rate_limit(f"login:{client_ip(request)}", 12, 60)
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()
    if not user or not verify_password(user.password_hash, body.password):
        await write_audit(db, action="login_fail", ip=client_ip(request), meta={"email": body.email.lower()})
        await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    await set_pending(user.id, response)
    await write_audit(db, action="login_password_ok", user_id=user.id, ip=client_ip(request))
    await db.commit()
    if user.totp_confirmed_at is None:
        return {"need": "enroll_totp", "email": user.email}
    return {"need": "totp", "email": user.email}


@router.post("/totp/enroll")
async def totp_enroll(request: Request, db: AsyncSession = Depends(get_session)):
    user_id = await pending_user_id(request)
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user missing")
    if user.totp_confirmed_at is not None:
        raise HTTPException(status_code=400, detail="totp already enrolled")
    settings = get_settings()
    secret = pyotp.random_base32()
    user.totp_secret_enc = encrypt_str(settings, secret)
    uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="HavenID")
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    import base64

    png = base64.b64encode(buf.getvalue()).decode("ascii")
    await write_audit(db, action="totp_enroll_start", user_id=user.id, ip=client_ip(request))
    await db.commit()
    return {"otpauth_url": uri, "secret": secret, "qr_png_base64": png}


@router.post("/totp/confirm")
async def totp_confirm(body: TotpIn, request: Request, response: Response, db: AsyncSession = Depends(get_session)):
    user_id = await pending_user_id(request)
    user = await db.get(User, user_id)
    if not user or not user.totp_secret_enc:
        raise HTTPException(status_code=400, detail="enroll totp first")
    secret = decrypt_str(get_settings(), user.totp_secret_enc)
    if not pyotp.TOTP(secret).verify(body.code.replace(" ", ""), valid_window=1):
        raise HTTPException(status_code=401, detail="invalid totp")
    user.totp_confirmed_at = utcnow()
    plain_codes = _codes()
    for code in plain_codes:
        db.add(RecoveryCode(user_id=user.id, code_hash=sha256_hex(code.lower())))
    device, token = await touch_or_create_device(db, user, request, request.cookies.get(DEVICE_COOKIE))
    await issue_session(db, response, user, request, device)
    set_cookie(response, DEVICE_COOKIE, token, 365 * 24 * 3600)
    await write_audit(db, action="totp_enrolled", user_id=user.id, ip=client_ip(request))
    await db.commit()
    return {"ok": True, "recovery_codes": plain_codes}


@router.post("/totp/verify")
async def totp_verify(body: TotpIn, request: Request, response: Response, db: AsyncSession = Depends(get_session)):
    await rate_limit(f"totp:{client_ip(request)}", 20, 60)
    user_id = await pending_user_id(request)
    user = await db.get(User, user_id)
    if not user or not user.totp_secret_enc or user.totp_confirmed_at is None:
        raise HTTPException(status_code=400, detail="totp not enrolled")
    secret = decrypt_str(get_settings(), user.totp_secret_enc)
    if not pyotp.TOTP(secret).verify(body.code.replace(" ", ""), valid_window=1):
        await write_audit(db, action="totp_fail", user_id=user.id, ip=client_ip(request))
        await db.commit()
        raise HTTPException(status_code=401, detail="invalid totp")
    device, token = await touch_or_create_device(db, user, request, request.cookies.get(DEVICE_COOKIE))
    await issue_session(db, response, user, request, device)
    set_cookie(response, DEVICE_COOKIE, token, 365 * 24 * 3600)
    await write_audit(db, action="login_ok", user_id=user.id, ip=client_ip(request))
    await db.commit()
    return {"ok": True}


@router.post("/refresh")
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_session)):
    raw = request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise HTTPException(status_code=401, detail="no refresh")
    result = await db.execute(select(Session).where(Session.refresh_hash == sha256_hex(raw)))
    row = result.scalar_one_or_none()
    if not row or row.revoked_at is not None or as_utc(row.expires_at) < utcnow():
        raise HTTPException(status_code=401, detail="refresh expired")
    user = await db.get(User, row.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="user missing")
    row.revoked_at = utcnow()
    device = await db.get(TrustedDevice, row.device_id) if row.device_id else None
    await issue_session(db, response, user, request, device)
    await db.commit()
    return {"ok": True}


@router.post("/logout")
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_session)):
    raw = request.cookies.get(REFRESH_COOKIE)
    if raw:
        result = await db.execute(select(Session).where(Session.refresh_hash == sha256_hex(raw)))
        row = result.scalar_one_or_none()
        if row:
            row.revoked_at = utcnow()
            await write_audit(db, action="logout", user_id=row.user_id, ip=client_ip(request))
    clear_cookie(response, ACCESS_COOKIE)
    clear_cookie(response, REFRESH_COOKIE)
    await db.commit()
    return {"ok": True}


@router.post("/recover")
async def recover(body: RecoverIn, request: Request, db: AsyncSession = Depends(get_session)):
    await rate_limit(f"recover:{client_ip(request)}", 8, 300)
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="recovery failed")
    hashed = sha256_hex(body.code.strip().lower())
    code_row = (
        await db.execute(
            select(RecoveryCode).where(
                RecoveryCode.user_id == user.id,
                RecoveryCode.code_hash == hashed,
                RecoveryCode.used_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not code_row:
        await write_audit(db, action="recover_fail", user_id=user.id, ip=client_ip(request))
        await db.commit()
        raise HTTPException(status_code=400, detail="recovery failed")
    code_row.used_at = utcnow()
    user.password_hash = hash_password(body.new_password)
    user.totp_secret_enc = None
    user.totp_confirmed_at = None
    sessions = (await db.execute(select(Session).where(Session.user_id == user.id, Session.revoked_at.is_(None)))).scalars()
    for sess in sessions:
        sess.revoked_at = utcnow()
    await write_audit(db, action="recover_ok", user_id=user.id, ip=client_ip(request))
    await db.commit()
    return {"ok": True, "need": "enroll_totp"}


@router.get("/webauthn/register/options")
async def webauthn_register_options(request: Request, db: AsyncSession = Depends(get_session)):
    from webauthn import generate_registration_options
    from webauthn.helpers import bytes_to_base64url
    from webauthn.helpers.structs import (
        AuthenticatorSelectionCriteria,
        ResidentKeyRequirement,
        UserVerificationRequirement,
    )

    user = await current_user(request, db)
    settings = get_settings()
    options = generate_registration_options(
        rp_id=settings.haven_domain,
        rp_name="HavenID",
        user_name=user.email,
        user_id=user.id.encode("utf-8"),
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
    )
    await get_kv().setex(f"wa:reg:{user.id}", 300, bytes_to_base64url(options.challenge))
    return {
        "publicKey": {
            "rp": {"id": options.rp.id, "name": options.rp.name},
            "user": {
                "id": bytes_to_base64url(options.user.id),
                "name": options.user.name,
                "displayName": options.user.display_name or options.user.name,
            },
            "challenge": bytes_to_base64url(options.challenge),
            "pubKeyCredParams": [{"type": "public-key", "alg": p.alg} for p in options.pub_key_cred_params],
            "timeout": options.timeout,
            "attestation": options.attestation,
        }
    }


@router.post("/webauthn/register")
async def webauthn_register(payload: dict, request: Request, db: AsyncSession = Depends(get_session)):
    from webauthn import verify_registration_response
    from webauthn.helpers import base64url_to_bytes, bytes_to_base64url

    user = await current_user(request, db)
    settings = get_settings()
    challenge = await get_kv().get(f"wa:reg:{user.id}")
    if not challenge:
        raise HTTPException(status_code=400, detail="registration expired")
    verification = verify_registration_response(
        credential=payload,
        expected_challenge=base64url_to_bytes(challenge),
        expected_rp_id=settings.haven_domain,
        expected_origin=settings.haven_public_url.rstrip("/"),
    )
    cred_id = bytes_to_base64url(verification.credential_id)
    db.add(
        WebAuthnCredential(
            user_id=user.id,
            cred_id=cred_id,
            public_key=bytes_to_base64url(verification.credential_public_key),
            sign_count=verification.sign_count,
            nickname=str(payload.get("nickname") or "Passkey"),
        )
    )
    await write_audit(db, action="webauthn_enroll", user_id=user.id, ip=client_ip(request))
    await db.commit()
    return {"ok": True}


@router.get("/webauthn/login/options")
async def webauthn_login_options(email: str, db: AsyncSession = Depends(get_session)):
    from webauthn import generate_authentication_options
    from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
    from webauthn.helpers.structs import PublicKeyCredentialDescriptor, UserVerificationRequirement

    result = await db.execute(select(User).where(User.email == email.lower()))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="not found")
    creds = (
        await db.execute(select(WebAuthnCredential).where(WebAuthnCredential.user_id == user.id))
    ).scalars().all()
    if not creds:
        raise HTTPException(status_code=400, detail="no passkeys")
    settings = get_settings()
    options = generate_authentication_options(
        rp_id=settings.haven_domain,
        user_verification=UserVerificationRequirement.PREFERRED,
        allow_credentials=[
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.cred_id)) for c in creds
        ],
    )
    await get_kv().setex(f"wa:auth:{user.id}", 300, bytes_to_base64url(options.challenge))
    return {
        "user_id": user.id,
        "publicKey": {
            "challenge": bytes_to_base64url(options.challenge),
            "rpId": options.rp_id,
            "timeout": options.timeout,
            "userVerification": options.user_verification,
            "allowCredentials": [{"type": "public-key", "id": c.cred_id} for c in creds],
        },
    }


@router.post("/webauthn/login")
async def webauthn_login(payload: dict, request: Request, response: Response, db: AsyncSession = Depends(get_session)):
    from webauthn import verify_authentication_response
    from webauthn.helpers import base64url_to_bytes

    user_id = payload.get("user_id")
    user = await db.get(User, user_id) if user_id else None
    if not user:
        raise HTTPException(status_code=400, detail="user missing")
    challenge = await get_kv().get(f"wa:auth:{user.id}")
    if not challenge:
        raise HTTPException(status_code=400, detail="login expired")
    cred_id = payload.get("id") or payload.get("rawId")
    cred = (
        await db.execute(select(WebAuthnCredential).where(WebAuthnCredential.cred_id == cred_id))
    ).scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=400, detail="unknown passkey")
    settings = get_settings()
    verification = verify_authentication_response(
        credential=payload,
        expected_challenge=base64url_to_bytes(challenge),
        expected_rp_id=settings.haven_domain,
        expected_origin=settings.haven_public_url.rstrip("/"),
        credential_public_key=base64url_to_bytes(cred.public_key),
        credential_current_sign_count=cred.sign_count,
    )
    cred.sign_count = verification.new_sign_count
    cred.last_used_at = utcnow()
    device, token = await touch_or_create_device(db, user, request, request.cookies.get(DEVICE_COOKIE))
    await issue_session(db, response, user, request, device)
    set_cookie(response, DEVICE_COOKIE, token, 365 * 24 * 3600)
    await write_audit(db, action="webauthn_login", user_id=user.id, ip=client_ip(request))
    await db.commit()
    return {"ok": True}
