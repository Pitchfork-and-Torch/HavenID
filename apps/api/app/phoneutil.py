from __future__ import annotations

import phonenumbers
from phonenumbers import NumberParseException


def to_e164(raw: str | None, region: str = "US") -> str | None:
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    if text.lower() in {"anonymous", "restricted", "unknown", "private"}:
        return None
    try:
        parsed = phonenumbers.parse(text, region)
    except NumberParseException:
        return None
    if not phonenumbers.is_possible_number(parsed):
        return None
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def is_anonymous(raw: str | None) -> bool:
    if raw is None or not raw.strip():
        return True
    return raw.strip().lower() in {"anonymous", "restricted", "unknown", "private"}
