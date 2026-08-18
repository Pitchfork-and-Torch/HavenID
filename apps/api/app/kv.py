from __future__ import annotations

import time
from typing import Protocol


class KV(Protocol):
    async def setex(self, key: str, ttl: int, value: str) -> None: ...
    async def get(self, key: str) -> str | None: ...
    async def delete(self, key: str) -> None: ...
    async def incr(self, key: str, ttl: int) -> int: ...


class MemoryKV:
    def __init__(self) -> None:
        self._data: dict[str, tuple[float, str]] = {}
        self._counts: dict[str, tuple[float, int]] = {}

    def _purge(self, key: str) -> None:
        item = self._data.get(key)
        if item and item[0] < time.time():
            self._data.pop(key, None)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self._data[key] = (time.time() + ttl, value)

    async def get(self, key: str) -> str | None:
        self._purge(key)
        item = self._data.get(key)
        return item[1] if item else None

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)
        self._counts.pop(key, None)

    async def incr(self, key: str, ttl: int) -> int:
        now = time.time()
        exp, count = self._counts.get(key, (now + ttl, 0))
        if exp < now:
            exp, count = now + ttl, 0
        count += 1
        self._counts[key] = (exp, count)
        return count


class RedisKV:
    def __init__(self, url: str) -> None:
        import redis.asyncio as redis

        self._r = redis.from_url(url, decode_responses=True)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        await self._r.set(key, value, ex=ttl)

    async def get(self, key: str) -> str | None:
        return await self._r.get(key)

    async def delete(self, key: str) -> None:
        await self._r.delete(key)

    async def incr(self, key: str, ttl: int) -> int:
        value = await self._r.incr(key)
        if value == 1:
            await self._r.expire(key, ttl)
        return int(value)


_kv: KV | None = None


def get_kv() -> KV:
    global _kv
    if _kv is None:
        from app.config import get_settings

        url = get_settings().redis_url
        _kv = RedisKV(url) if url else MemoryKV()
    return _kv


def set_kv(store: KV) -> None:
    global _kv
    _kv = store
