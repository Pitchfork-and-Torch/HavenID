from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import login_full


async def test_contact_crud_and_overview(client: AsyncClient):
    await login_full(client)
    created = await client.post(
        "/api/v1/contacts",
        json={
            "display_name": "Ada Lovelace",
            "given_name": "Ada",
            "family_name": "Lovelace",
            "phones": [{"e164": "+1 555 123 0000", "label": "mobile"}],
            "emails": [{"address": "ada@example.com"}],
        },
    )
    assert created.status_code == 200, created.text
    cid = created.json()["id"]
    assert created.json()["phones"][0]["e164"] == "+15551230000"

    listed = await client.get("/api/v1/contacts", params={"q": "Ada"})
    assert listed.status_code == 200
    assert listed.json()["items"]

    deny = await client.post(
        "/api/v1/lists",
        json={"list_kind": "deny", "match_kind": "exact", "pattern": "+15559990000", "note": "spam"},
    )
    assert deny.status_code == 200, deny.text

    ov = await client.get("/api/v1/overview")
    assert ov.status_code == 200
    assert ov.json()["contacts"] >= 1

    deleted = await client.delete(f"/api/v1/contacts/{cid}")
    assert deleted.status_code == 200
