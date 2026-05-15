import json
import time
import traceback
from typing import Any, Optional
from config import settings

try:
    from redis import Redis
    from redis.exceptions import RedisError
except ImportError:
    Redis = None
    RedisError = Exception


DEFAULT_TTL_SECONDS = 15 * 60  # 15 minutes


class LocalCacheEntry:
    def __init__(self, value: Any, expires_at: float):
        self.value = value
        self.expires_at = expires_at


class CacheService:
    def __init__(self):
        self.redis_client = None
        self.local_cache = {}
        self.ready = False
        self._init_cache()

    def _init_cache(self):
        if not settings.REDIS_URL or Redis is None:
            print("Redis cache disabled: REDIS_URL missing or redis package unavailable.")
            return

        try:
            self.redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
            self.redis_client.ping()
            self.ready = True
            print("Redis cache initialized successfully.")
        except Exception as exc:
            print("Redis cache unavailable, falling back to local memory cache:", exc)
            traceback.print_exc()
            self.redis_client = None
            self.ready = False

    def _serialize(self, value: Any) -> str:
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return json.dumps(str(value), ensure_ascii=False)

    def _deserialize(self, value: Optional[str]) -> Any:
        if value is None:
            return None
        try:
            return json.loads(value)
        except Exception:
            return value

    def _cleanup_local(self):
        now = time.time()
        expired = [key for key, entry in self.local_cache.items() if entry.expires_at <= now]
        for key in expired:
            del self.local_cache[key]

    def get(self, key: str) -> Any:
        if self.redis_client:
            try:
                value = self.redis_client.get(key)
                return self._deserialize(value)
            except RedisError as exc:
                print("Redis cache read failed, using local fallback:", exc)
                self.redis_client = None

        self._cleanup_local()
        entry = self.local_cache.get(key)
        if entry and entry.expires_at > time.time():
            return entry.value
        if key in self.local_cache:
            del self.local_cache[key]
        return None

    def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL_SECONDS) -> bool:
        if self.redis_client:
            try:
                self.redis_client.set(key, self._serialize(value), ex=ttl)
                return True
            except RedisError as exc:
                print("Redis cache write failed, using local fallback:", exc)
                self.redis_client = None

        self.local_cache[key] = LocalCacheEntry(value, time.time() + ttl)
        return True

    def delete(self, key: str) -> bool:
        if self.redis_client:
            try:
                self.redis_client.delete(key)
            except RedisError as exc:
                print("Redis cache delete failed:", exc)
                self.redis_client = None
        self.local_cache.pop(key, None)
        return True

    def clear(self) -> bool:
        if self.redis_client:
            try:
                self.redis_client.flushdb()
            except RedisError as exc:
                print("Redis cache flush failed:", exc)
                self.redis_client = None
        self.local_cache.clear()
        return True

    def get_auto_scan(self, market: str, mode_name: str) -> Any:
        return self.get(f"autoscan:{mode_name}:{market}")

    def cache_auto_scan(self, market: str, mode_name: str, value: Any, ttl: int = DEFAULT_TTL_SECONDS) -> bool:
        return self.set(f"autoscan:{mode_name}:{market}", value, ttl)

    def get_analysis(self, market: str, payload_key: str) -> Any:
        return self.get(f"analysis:{market}:{payload_key}")

    def cache_analysis(self, market: str, payload_key: str, value: Any, ttl: int = DEFAULT_TTL_SECONDS) -> bool:
        return self.set(f"analysis:{market}:{payload_key}", value, ttl)

    def get_calendar_event(self, event_id: str) -> Any:
        return self.get(f"calendar:{event_id}")

    def cache_calendar_event(self, event_id: str, value: Any, ttl: int = DEFAULT_TTL_SECONDS) -> bool:
        return self.set(f"calendar:{event_id}", value, ttl)

    def get_dashboard_stats(self, user_id: str) -> Any:
        return self.get(f"dashboard:{user_id}")

    def cache_dashboard_stats(self, user_id: str, value: Any, ttl: int = DEFAULT_TTL_SECONDS) -> bool:
        return self.set(f"dashboard:{user_id}", value, ttl)


cache_service = CacheService()
