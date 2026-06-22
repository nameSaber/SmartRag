from dataclasses import dataclass
import time

from redis import Redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BizError
from app.models.admin import RateLimitConfig


@dataclass
class RateLimitRule:
    config_key: str
    single_max: int
    single_window_seconds: int
    day_max: int
    day_window_seconds: int


class InMemoryRateLimitBackend:
    def __init__(self):
        self.events: dict[str, list[float]] = {}

    def hit(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time.time()
        window_start = now - window_seconds
        items = [item for item in self.events.get(key, []) if item > window_start]
        if len(items) >= limit:
            retry_after = max(1, int(items[0] + window_seconds - now))
            self.events[key] = items
            return False, retry_after
        items.append(now)
        self.events[key] = items
        return True, 0

    def reset(self) -> None:
        self.events.clear()


class RedisRateLimitBackend:
    def __init__(self, redis_client: Redis | None = None):
        self.redis = redis_client or Redis.from_url(settings.redis_url)

    def hit(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now_ms = int(time.time() * 1000)
        window_ms = window_seconds * 1000
        redis_key = f"rate:{key}"
        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(redis_key, 0, now_ms - window_ms)
        pipe.zcard(redis_key)
        _, current_count = pipe.execute()
        if current_count >= limit:
            oldest = self.redis.zrange(redis_key, 0, 0, withscores=True)
            retry_after = 1
            if oldest:
                retry_after = max(1, int((oldest[0][1] + window_ms - now_ms) / 1000))
            return False, retry_after
        # 时间戳加纳秒片段，避免同一毫秒内成员名冲突。
        self.redis.zadd(redis_key, {f"{now_ms}:{time.perf_counter_ns()}": now_ms})
        self.redis.expire(redis_key, window_seconds)
        return True, 0


_memory_backend = InMemoryRateLimitBackend()


def reset_in_memory_rate_limiter() -> None:
    _memory_backend.reset()


def get_rate_limit_backend():
    if settings.rate_limit_backend == "redis":
        return RedisRateLimitBackend()
    return _memory_backend


def load_rate_limit_rule(db: Session, config_key: str) -> RateLimitRule:
    row = db.get(RateLimitConfig, config_key)
    if not row:
        row = RateLimitConfig(config_key=config_key)
        db.add(row)
        db.commit()
        db.refresh(row)
    return RateLimitRule(
        config_key=row.config_key,
        single_max=row.single_max,
        single_window_seconds=row.single_window_seconds,
        day_max=row.day_max,
        day_window_seconds=row.day_window_seconds,
    )


def enforce_rate_limit(db: Session, config_key: str, identity: str) -> None:
    rule = load_rate_limit_rule(db, config_key)
    backend = get_rate_limit_backend()
    for window_name, limit, seconds in [
        ("single", rule.single_max, rule.single_window_seconds),
        ("day", rule.day_max, rule.day_window_seconds),
    ]:
        allowed, retry_after = backend.hit(f"{rule.config_key}:{window_name}:{identity}", limit, seconds)
        if not allowed:
            raise BizError("请求过于频繁，请稍后再试", 429, {"retryAfterSeconds": retry_after})
