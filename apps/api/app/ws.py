from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.kv import get_kv

router = APIRouter()


@router.websocket("/ws/live")
async def live(ws: WebSocket) -> None:
    await ws.accept()
    try:
        while True:
            payload = {"type": "heartbeat"}
            raw = await get_kv().get("call:last")
            if raw:
                try:
                    payload["last_call"] = json.loads(raw)
                except json.JSONDecodeError:
                    pass
            await ws.send_json(payload)
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        return
