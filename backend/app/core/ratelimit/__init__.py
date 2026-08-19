"""限流框架（rate limiting）。

模块分层：
    storage  —— 计数存储后端抽象（进程内 / 可扩展 Redis）
    window   —— 滑动窗口计数器，封装"窗口内请求计数 + 过期回收"
    limiter  —— 限流器门面，组合存储与窗口，提供 acquire() 判定

设计要点：
    - 面向对象：存储后端、窗口计数器、限流器均为可独立替换/单测的类。
    - 模块化：每一层职责单一，上层依赖抽象而非具体实现。
    - 进程内单实例足够覆盖 v1 单机部署；预留 Redis 存储槽位，v2 任务队列引入时平滑替换。
"""

from app.core.ratelimit.limiter import RateLimiter, RateLimitResult, rate_limiter

__all__ = ["RateLimiter", "RateLimitResult", "rate_limiter"]
