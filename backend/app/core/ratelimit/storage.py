"""限流计数存储后端抽象。

窗口计数器需要"按 key 存取整数值 + 设置/读取过期时间"两类操作。
进程内实现采用 (count, expires_at) 元组 + 惰性过期，语义为严格的固定窗口：
计数从首次请求起固定 ttl 后失效，后续自增不续期，保证窗口边界确定可预期。
分布式部署时替换为 Redis 实现（INCR + EXPIRE 原子操作），无需改动上层。
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from cachetools import LRUCache


class RateLimitStorage(ABC):
    """计数存储接口：get / increment / delete。"""

    @abstractmethod
    def get(self, key: str) -> Any:
        """读取当前计数，未命中或已过期返回 None。"""

    @abstractmethod
    def increment(self, key: str, ttl: int) -> int:
        """计数自增 1；首次写入按 ttl 设置过期，后续自增不续期。返回自增后的值。"""

    @abstractmethod
    def ttl(self, key: str) -> int:
        """返回窗口剩余秒数；未命中或已过期返回 0。"""

    @abstractmethod
    def delete(self, key: str) -> None:
        """清除指定 key 的计数（登录成功后重置窗口）。"""


class InprocRateLimitStorage(RateLimitStorage):
    """进程内固定窗口存储后端。

    值为 (count, expires_at) 元组；get 时惰性判定过期并清除，避免读取脏计数。
    用 LRUCache 限定容量，防止异常来源 IP 爆增导致内存无限增长。
    """

    def __init__(self, maxsize: int = 4096) -> None:
        self._store: LRUCache[str, tuple[int, float]] = LRUCache(maxsize=maxsize)
        self._now = time.monotonic  # 单调时钟，不受系统时间回拨影响

    def get(self, key: str) -> Any:
        entry = self._store.get(key)
        if entry is None:
            return None
        count, expires_at = entry
        if self._now() >= expires_at:  # 惰性过期回收
            self._store.pop(key, None)
            return None
        return count

    def increment(self, key: str, ttl: int) -> int:
        now = self._now()
        entry = self._store.get(key)
        if entry is not None and now < entry[1]:
            # 窗口未过期：仅自增，不续期，保持固定窗口边界。
            count = entry[0] + 1
            self._store[key] = (count, entry[1])
            return count
        # 窗口过期或首次写入：开启新窗口，过期时间为 now + ttl。
        self._store[key] = (1, now + ttl)
        return 1

    def ttl(self, key: str) -> int:
        entry = self._store.get(key)
        if entry is None:
            return 0
        remaining = entry[1] - self._now()
        return max(0, int(remaining) + 1)  # 向上取整，避免 Retry-After 报 0

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


def get_storage() -> RateLimitStorage:
    """按配置返回存储后端。redis 分支 v2 实现，当前统一 inproc。"""
    from app.core.config import settings
    from app.core.logging import get_logger

    if settings.CACHE_BACKEND == "redis":
        get_logger(__name__).warning("redis 存储需 v2 引入，降级为 inproc")
    return InprocRateLimitStorage()
