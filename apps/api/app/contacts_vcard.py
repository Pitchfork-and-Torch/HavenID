from __future__ import annotations

from typing import TYPE_CHECKING

import vobject

from app.phoneutil import to_e164

if TYPE_CHECKING:
    from app.models import Contact


def contacts_to_vcard(contacts: list[Contact]) -> str:
    chunks: list[str] = []
    for contact in contacts:
        card = vobject.vCard()
        card.add("fn").value = contact.display_name
        n = card.add("n")
        n.value = vobject.vcard.Name(family=contact.family_name or "", given=contact.given_name or "")
        if contact.org:
            card.add("org").value = [contact.org]
        if contact.notes:
            card.add("note").value = contact.notes
        for phone in contact.phones:
            tel = card.add("tel")
            tel.value = phone.e164
            tel.type_param = phone.label or "CELL"
        for email in contact.emails:
            em = card.add("email")
            em.value = email.address
            em.type_param = email.label or "HOME"
        chunks.append(card.serialize())
    return "".join(chunks)


def contacts_from_vcard(text: str) -> list[dict]:
    items: list[dict] = []
    raw = text.strip()
    if not raw:
        return items
    try:
        cards = list(vobject.readComponents(raw))
    except Exception:
        return items
    for card in cards:
        fn = str(getattr(getattr(card, "fn", None), "value", "") or "").strip()
        n = getattr(card, "n", None)
        given = ""
        family = ""
        if n and getattr(n, "value", None):
            given = str(getattr(n.value, "given", "") or "")
            family = str(getattr(n.value, "family", "") or "")
        if not fn:
            fn = " ".join(p for p in (given, family) if p).strip() or "Unnamed"
        org = ""
        if getattr(card, "org", None):
            val = card.org.value
            org = val[0] if isinstance(val, list) and val else str(val)
        notes = str(getattr(getattr(card, "note", None), "value", "") or "")
        phones: list[dict] = []
        emails: list[dict] = []
        contents = getattr(card, "contents", {})
        for tel in contents.get("tel", []):
            e164 = to_e164(str(tel.value))
            if e164:
                phones.append({"e164": e164, "label": str(getattr(tel, "type_param", "") or "mobile")})
        for em in contents.get("email", []):
            addr = str(em.value or "").strip()
            if addr:
                emails.append({"address": addr, "label": str(getattr(em, "type_param", "") or "home")})
        items.append(
            {
                "display_name": fn,
                "given_name": given,
                "family_name": family,
                "org": org,
                "notes": notes,
                "phones": phones,
                "emails": emails,
            }
        )
    return items
