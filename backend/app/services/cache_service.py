"""Redis caching service helpers."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from typing import Any

import redis
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class CacheService:
    """Service layer for Redis-backed JSON caching."""

    STORE_LIST_KEY = "cache:stores:list"
    STORE_PRODUCTS_KEY_PATTERN = "cache:stores:{store_id}:products:list"

    def __init__(self, *, default_ttl_seconds: int = 300) -> None:
        settings = get_settings()
        self._default_ttl_seconds = default_ttl_seconds
        self._client: Redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

    def get_json(self, key: str) -> Any | None:
        """Return parsed JSON value for a key when present."""
        try:
            cached = self._client.get(key)
            if cached is None:
                return None
            return json.loads(cached)
        except (RedisError, json.JSONDecodeError):
            logger.warning("Cache read failed for key '%s'.", key, exc_info=True)
            return None

    def set_json(self, key: str, value: Any, *, ttl_seconds: int | None = None) -> None:
        """Store a JSON-serializable value with TTL."""
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl_seconds
        try:
            self._client.setex(key, ttl, json.dumps(value))
        except (RedisError, TypeError, ValueError):
            logger.warning("Cache write failed for key '%s'.", key, exc_info=True)

    def delete(self, key: str) -> None:
        """Delete a single cache key."""
        try:
            self._client.delete(key)
        except RedisError:
            logger.warning("Cache delete failed for key '%s'.", key, exc_info=True)

    def delete_by_pattern(self, pattern: str) -> None:
        """Delete all keys matching the pattern."""
        try:
            keys = list(self._iter_keys(pattern))
            if keys:
                self._client.delete(*keys)
        except RedisError:
            logger.warning("Cache delete by pattern failed for '%s'.", pattern, exc_info=True)

    def _iter_keys(self, pattern: str) -> Iterator[str]:
        """Iterate matching keys using scan for production-safe traversal."""
        return self._client.scan_iter(match=pattern)

    @classmethod
    def store_list_key(cls) -> str:
        """Cache key for the store list endpoint."""
        return cls.STORE_LIST_KEY

    @classmethod
    def store_products_key(cls, store_id: int) -> str:
        """Cache key for the store products list endpoint."""
        return cls.STORE_PRODUCTS_KEY_PATTERN.format(store_id=store_id)

    def invalidate_store_list(self) -> None:
        """Invalidate store list cache."""
        self.delete(self.store_list_key())

    def invalidate_store_products(self, store_id: int) -> None:
        """Invalidate products list cache for a store."""
        self.delete(self.store_products_key(store_id))


cache_service = CacheService()
