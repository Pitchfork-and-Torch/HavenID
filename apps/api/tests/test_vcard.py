from __future__ import annotations

from types import SimpleNamespace

from app.contacts_vcard import contacts_from_vcard, contacts_to_vcard


def test_vcard_roundtrip():
    contact = SimpleNamespace(
        display_name="Ada Lovelace",
        given_name="Ada",
        family_name="Lovelace",
        org="Analytical",
        notes="first programmer",
        phones=[SimpleNamespace(e164="+15551230000", label="CELL")],
        emails=[SimpleNamespace(address="ada@example.com", label="HOME")],
    )
    text = contacts_to_vcard([contact])
    assert "BEGIN:VCARD" in text
    parsed = contacts_from_vcard(text)
    assert parsed
    assert parsed[0]["display_name"]
    assert any(p["e164"] == "+15551230000" for p in parsed[0]["phones"])
