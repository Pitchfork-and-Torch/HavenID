from __future__ import annotations

import httpx

from app.config import Settings


async def classify_transcript(settings: Settings, text: str) -> str | None:
    if not settings.xai_api_key or not text.strip():
        return None
    prompt = (
        "Classify this inbound phone call transcript as exactly one word: "
        "spam or human. Transcript:\n"
        f"{text[:1500]}"
    )
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post(
                f"{settings.xai_api_base.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.xai_api_key}"},
                json={
                    "model": settings.xai_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                    "max_tokens": 8,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip().lower()
    except Exception:
        return None
    if "spam" in content:
        return "spam"
    if "human" in content:
        return "human"
    return None
