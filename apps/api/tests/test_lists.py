from __future__ import annotations

from app.lists.match import first_hit, matches, normalize_pattern


def test_normalize():
    assert normalize_pattern("555-123-0000").endswith("5551230000") or normalize_pattern("+15551230000") == "+15551230000"
    assert normalize_pattern("+1 555 123 0000") == "+15551230000"


def test_exact_and_prefix():
    assert matches("+15551230000", "+15551230000", "exact")
    assert not matches("+15551230001", "+15551230000", "exact")
    assert matches("+15551239999", "+1555123", "prefix")


def test_first_hit():
    entries = [
        ("allow", "exact", "+15550001111", "mom"),
        ("deny", "prefix", "+1800", "toll"),
    ]
    assert first_hit("+15550001111", entries, "allow") is not None
    assert first_hit("+18005551212", entries, "deny") is not None
    assert first_hit("+15550001111", entries, "deny") is None
