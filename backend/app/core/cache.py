"""缓存后端抽象（v1：进程内 TTL 缓存；预留 redis 开关位）。

方案 §3：v1 默认 inproc（cachetools.TTLCache），CACHE_BACKEND=redis 时切换，
Redis 由 v2 任务队列引入。接口最小化，任何实现替换无侵入。
"""

from __future__ import annotations

from typing import Any

from cachetools import TTLCache

from app.core.config import settings


class CacheBackend:
    """统一缓存接口。get 未命中返回 None；set 可覆盖。"""

    def get(self, key: str) -> Any:  # pragma: no cover - 抽象
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:  # pragma: no cover - 抽象
        raise NotImplementedError

    def delete(self, key: str) -> None:  # pragma: no cover - 抽象
        raise NotImplementedError


class InprocCache(CacheBackend):
    """进程内 TTL 缓存。maxsize 足够覆盖常见 POC 元数据缓存量。"""

    def __init__(self, ttl: int | None = None) -> None:
        self._ttl = ttl or settings.CACHE_TTL_SECONDS
        self._store: TTLCache[str, Any] = TTLCache(maxsize=1024, ttl=self._ttl)

    def get(self, key: str) -> Any:
        return self._store.get(key)

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        # ttl 参数预留：inproc 后端按实例级 TTL 统一过期，不按 key 单独覆盖
        self._store[key] = value

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


def get_cache() -> CacheBackend:
    """按配置返回缓存后端。redis 分支 v2 实现，当前降级 inproc 并告警。"""
    if settings.CACHE_BACKEND == "redis":
        print("[cache] CACHE_BACKEND=redis 需 v2 引入，降级为 inproc")
    return InprocCache()


cache = get_cache()
