"""限流器门面：组合存储后端，提供 acquire() 判定。

固定窗口算法：每个 (标识, 动作) 组合在 ttl 窗口内最多允许 limit 次请求；
超出即拒绝，直至窗口过期。登录成功后调用 reset() 清零计数，避免正常用户
被偶然的失败尝试拖入冷却。

面向对象设计：
    - RateLimitResult —— 不可变判定结果，承载 allowed / remaining / retry_after。
    - RateLimiter     —— 限流器，封装存储交互与窗口规则，供中间件/服务调用。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.ratelimit.storage import RateLimitStorage, get_storage


@dataclass(frozen=True)
class RateLimitResult:
    """限流判定结果。"""

    allowed: bool
    remaining: int
    retry_after: int  # 窗口剩余秒数，拒绝时供 Retry-After 头使用


class RateLimiter:
    """固定窗口限流器。"""

    def __init__(self, storage: RateLimitStorage | None = None) -> None:
        self._storage = storage or get_storage()

    def acquire(self, key: str, limit: int, ttl: int) -> RateLimitResult:
        """尝试获取一次请求配额。

        Args:
            key: 限流标识（如 "login:ip:1.2.3.4"）。
            limit: 窗口内允许的最大次数。
            ttl: 窗口时长（秒）。

        Returns:
            RateLimitResult：allowed 表示是否放行，remaining 为窗口内剩余配额，
            retry_after 为拒绝时至窗口重置的秒数。
        """
        count = self._storage.increment(key, ttl)
        remaining = max(0, limit - count)
        allowed = count <= limit
        # 拒绝时取窗口精确剩余时长作为 Retry-After；放行时为 0。
        retry_after = 0 if allowed else self._storage.ttl(key)
        return RateLimitResult(allowed=allowed, remaining=remaining, retry_after=retry_after)

    def reset(self, key: str) -> None:
        """重置标识的计数窗口（登录成功后调用，清零失败计数）。"""
        self._storage.delete(key)


# 进程内单例：v1 单机部署共享同一存储；多实例部署需替换为 Redis 后端。
rate_limiter = RateLimiter()
