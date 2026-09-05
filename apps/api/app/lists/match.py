from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListHit:
    list_kind: str
    match_kind: str
    pattern: str
    note: str = ""


def normalize_pattern(raw: str) -> str:
    digits = "".join(ch for ch in raw if ch.isdigit() or ch == "+")
    if digits.startswith("00"):
        digits = "+" + digits[2:]
    if digits and not digits.startswith("+"):
        digits = "+" + digits
    return digits


def matches(number: str | None, pattern: str, match_kind: str) -> bool:
    if not number:
        return False
    pat = normalize_pattern(pattern)
    num = normalize_pattern(number)
    if not pat or not num:
        return False
    kind = (match_kind or "exact").lower()
    if kind == "prefix":
        return num.startswith(pat)
    return num == pat


def first_hit(
    number: str | None,
    entries: list[tuple[str, str, str, str]],
    want: str,
) -> ListHit | None:
    """entries: (list_kind, match_kind, pattern, note)"""
    for list_kind, match_kind, pattern, note in entries:
        if list_kind != want:
            continue
        if matches(number, pattern, match_kind):
            return ListHit(list_kind, match_kind, pattern, note)
    return None
