from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db import Base


def new_id() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    phone_e164: Mapped[str | None] = mapped_column(String(20), nullable=True)
    display_name: Mapped[str] = mapped_column(String(120), default="Owner")
    password_hash: Mapped[str] = mapped_column(String(255))
    totp_secret_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    totp_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    recovery_codes: Mapped[list[RecoveryCode]] = relationship(back_populates="user", cascade="all, delete-orphan")
    devices: Mapped[list[TrustedDevice]] = relationship(back_populates="user", cascade="all, delete-orphan")


class RecoveryCode(Base):
    __tablename__ = "recovery_codes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="recovery_codes")


class WebAuthnCredential(Base):
    __tablename__ = "webauthn_credentials"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    cred_id: Mapped[str] = mapped_column(String(512), unique=True)
    public_key: Mapped[str] = mapped_column(Text)
    sign_count: Mapped[int] = mapped_column(Integer, default=0)
    nickname: Mapped[str] = mapped_column(String(80), default="Passkey")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TrustedDevice(Base):
    __tablename__ = "trusted_devices"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(80), default="Browser")
    user_agent: Mapped[str] = mapped_column(String(400), default="")
    last_ip: Mapped[str] = mapped_column(String(80), default="")
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="devices")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    device_id: Mapped[str | None] = mapped_column(ForeignKey("trusted_devices.id", ondelete="SET NULL"), nullable=True)
    refresh_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    user_agent: Mapped[str] = mapped_column(String(400), default="")


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    display_name: Mapped[str] = mapped_column(String(200), index=True)
    given_name: Mapped[str] = mapped_column(String(120), default="")
    family_name: Mapped[str] = mapped_column(String(120), default="")
    org: Mapped[str] = mapped_column(String(200), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    etag: Mapped[str] = mapped_column(String(40), default=new_id)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    phones: Mapped[list[ContactPhone]] = relationship(back_populates="contact", cascade="all, delete-orphan")
    emails: Mapped[list[ContactEmail]] = relationship(back_populates="contact", cascade="all, delete-orphan")


class ContactPhone(Base):
    __tablename__ = "contact_phones"
    __table_args__ = (UniqueConstraint("contact_id", "e164", name="uq_contact_phone"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    contact_id: Mapped[str] = mapped_column(ForeignKey("contacts.id", ondelete="CASCADE"), index=True)
    e164: Mapped[str] = mapped_column(String(20), index=True)
    label: Mapped[str] = mapped_column(String(40), default="mobile")
    preferred: Mapped[bool] = mapped_column(Boolean, default=False)

    contact: Mapped[Contact] = relationship(back_populates="phones")


class ContactEmail(Base):
    __tablename__ = "contact_emails"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    contact_id: Mapped[str] = mapped_column(ForeignKey("contacts.id", ondelete="CASCADE"), index=True)
    address: Mapped[str] = mapped_column(String(320))
    label: Mapped[str] = mapped_column(String(40), default="home")

    contact: Mapped[Contact] = relationship(back_populates="emails")


class CallLog(Base):
    __tablename__ = "call_logs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider_sid: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    direction: Mapped[str] = mapped_column(String(16), default="inbound")
    from_e164: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    to_e164: Mapped[str | None] = mapped_column(String(20), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    duration_sec: Mapped[int] = mapped_column(Integer, default=0)
    outcome: Mapped[str] = mapped_column(String(40), default="pending")
    decision: Mapped[str] = mapped_column(String(40), default="")
    reason: Mapped[str] = mapped_column(String(200), default="")
    spam_score: Mapped[float] = mapped_column(Float, default=0.0)
    transcript: Mapped[str] = mapped_column(Text, default="")
    recording_path: Mapped[str] = mapped_column(String(400), default="")
    raw_meta: Mapped[dict] = mapped_column(JSON, default=dict)


class ListEntry(Base):
    __tablename__ = "list_entries"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    list_kind: Mapped[str] = mapped_column(String(16), index=True)  # allow | deny
    match_kind: Mapped[str] = mapped_column(String(16), default="exact")  # exact | prefix
    pattern: Mapped[str] = mapped_column(String(32), index=True)
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    mode: Mapped[str] = mapped_column(String(16), default="balanced")
    challenge_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    record_voicemail: Mapped[bool] = mapped_column(Boolean, default=False)
    recording_legal_ack: Mapped[bool] = mapped_column(Boolean, default=False)
    ring_strategy: Mapped[str] = mapped_column(String(16), default="simultaneous")
    reject_style: Mapped[str] = mapped_column(String(16), default="polite")
    forward_e164: Mapped[list] = mapped_column(JSON, default=list)
    public_spam_lists: Mapped[bool] = mapped_column(Boolean, default=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    actor: Mapped[str] = mapped_column(String(40), default="user")
    action: Mapped[str] = mapped_column(String(80), index=True)
    ip: Mapped[str] = mapped_column(String(80), default="")
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class SettingRow(Base):
    __tablename__ = "settings"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    notify_email_voicemail: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_email_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    theme: Mapped[str] = mapped_column(String(16), default="dark")
