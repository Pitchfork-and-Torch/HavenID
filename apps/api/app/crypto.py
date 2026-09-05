from __future__ import annotations

import base64
import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken

from app.config import Settings

_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, ValueError):
        return False


def random_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _fernet(settings: Settings) -> Fernet:
    raw = (settings.haven_data_key or settings.haven_secret_key).encode("utf-8")
    digest = hashlib.sha256(raw).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_str(settings: Settings, plaintext: str) -> str:
    return _fernet(settings).encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_str(settings: Settings, token: str) -> str:
    try:
        return _fernet(settings).decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("could not decrypt secret") from exc
