"""领域事件总线（v1）：进程内 asyncio 异步派发，携带 MQ 兼容字段。

设计约束（见方案 §7.4）：
- v1 仅暴露 poc.* 与 batch_imported 事件；验证/AI/爬取事件随模块引入。
- 订阅者必须快速返回（纯内存操作），禁止阻塞；发布方不等待消费结果。
"""

from __future__ import annotations

import asyncio
import datetime as dt
import inspect
import uuid
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

EVENT_TYPES = {
    "poc.created",
    "poc.updated",
    "poc.deleted",
    "poc.status_changed",
    "poc.version_created",
    "poc.batch_imported",
    "poc.commented",
}


class EventTypes(str, Enum):
    POC_CREATED = "poc.created"
    POC_UPDATED = "poc.updated"
    POC_DELETED = "poc.deleted"
    POC_STATUS_CHANGED = "poc.status_changed"
    POC_VERSION_CREATED = "poc.version_created"
    BATCH_IMPORTED = "poc.batch_imported"
    VULN_BATCH_IMPORTED = "vuln.batch_imported"
    POC_COMMENTED = "poc.commented"

    @classmethod
    def has(cls, value: str) -> bool:
        return value in cls._value2member_map_


class DomainEvent:
    """事件载荷。event_id / aggregate_id / occurred_at 为将来切换 MQ 的兼容字段。"""

    __slots__ = ("event_id", "type", "aggregate_id", "payload", "occurred_at")

    def __init__(
        self, event_type: str, aggregate_id: str | None = None, payload: dict[str, Any] | None = None
    ) -> None:
        if not EventTypes.has(event_type):
            raise ValueError(f"未知事件类型: {event_type}")
        self.event_id = str(uuid.uuid4())
        self.type = event_type
        self.aggregate_id = aggregate_id
        self.payload = payload or {}
        self.occurred_at = dt.datetime.now(dt.timezone.utc)


Handler = Callable[[DomainEvent], Awaitable[None] | None]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[Handler]] = {}

    def subscribe(self, event_type: str, handler: Handler) -> None:
        self._subscribers.setdefault(event_type, set()).add(handler)

    def unsubscribe(self, event_type: str, handler: Handler) -> None:
        self._subscribers.get(event_type, set()).discard(handler)

    def publish(self, event: DomainEvent) -> None:
        """异步派发，不阻塞调用方。

        如果当前有运行中的 asyncio 事件循环，使用 create_task 异步派发；
        否则（同步上下文如 pytest 线程池），同步调用消费者。
        handler 异常仅记日志，不影响主流程。
        """
        for handler in self._subscribers.get(event.type, ()):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._safe(handler, event))
            except RuntimeError:
                # 没有运行中的事件循环（同步上下文如 pytest threadpool）
                self._safe_sync(handler, event)

    def _safe_sync(self, handler: Handler, event: DomainEvent) -> None:
        """同步调用消费者（无事件循环时的降级路径）。"""
        try:
            result = handler(event)
            if inspect.isawaitable(result):
                # 异步 handler 在同步上下文中被调用，忽略返回值
                pass
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "event subscriber failed",
                extra={"event": event.type, "error": str(exc)},
                exc_info=True,
            )

    async def _safe(self, handler: Handler, event: DomainEvent) -> None:
        try:
            result = handler(event)
            if inspect.isawaitable(result):
                await result
        except Exception as exc:  # noqa: BLE001 - 消费者异常必须隔离
            logger.warning(
                "event subscriber failed",
                extra={"event": event.type, "error": str(exc)},
                exc_info=True,
            )

    def subscriber_count(self, event_type: str) -> int:
        return len(self._subscribers.get(event_type, ()))


# 进程级单例
event_bus = EventBus()
