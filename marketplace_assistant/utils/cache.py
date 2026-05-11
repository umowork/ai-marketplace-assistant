"""Caching utilities with fallback to in-memory store."""

import hashlib
import json
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Any


class CacheBackend(ABC):
    """Abstract cache backend."""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        ...

    @abstractmethod
    async def clear(self) -> None:
        ...

    def make_key(self, prefix: str, *parts: str) -> str:
        raw = ":".join(str(p) for p in parts)
        return f"{prefix}:{hashlib.md5(raw.encode()).hexdigest()[:12]}"


class MemoryCache(CacheBackend):
    """In-memory LRU cache with TTL."""

    def __init__(self, maxsize: int = 256):
        self._store: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._maxsize = maxsize

    async def get(self, key: str) -> Any | None:
        if key not in self._store:
            return None
        value, expires = self._store[key]
        if time.monotonic() > expires:
            del self._store[key]
            return None
        # Move to end (most recently used)
        self._store.move_to_end(key)
        return value

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        expires = time.monotonic() + ttl
        self._store[key] = (value, expires)
        self._store.move_to_end(key)
        if len(self._store) > self._maxsize:
            self._store.popitem(last=False)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def clear(self) -> None:
        self._store.clear()


class RedisCache(CacheBackend):
    """Redis-backed cache. Lazy import of redis."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self._redis_url = redis_url
        self._client: Any | None = None

    async def _get_client(self) -> Any:
        if self._client is None:
            import redis.asyncio as aioredis  # lazy import
            self._client = aioredis.from_url(
                self._redis_url, decode_responses=True
            )
        return self._client

    async def get(self, key: str) -> Any | None:
        client = await self._get_client()
        raw = await client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        client = await self._get_client()
        raw = json.dumps(value, default=str, ensure_ascii=False)
        await client.setex(key, ttl, raw)

    async def delete(self, key: str) -> None:
        client = await self._get_client()
        await client.delete(key)

    async def clear(self) -> None:
        client = await self._get_client()
        await client.flushdb()


def create_cache(redis_url: str | None = None) -> CacheBackend:
    """Factory: возвращает RedisCache если redis_url указан, иначе MemoryCache."""
    if redis_url:
        return RedisCache(redis_url)
    return MemoryCache()
