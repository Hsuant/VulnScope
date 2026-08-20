"""Prometheus 指标注册表与探活挂钩（v1：进程内，零外部依赖）。

提供 Counter / Gauge / Histogram 三类指标与 Prometheus TEXT 文本渲染，
供 ``GET /metrics`` 端点暴露。数据面保持最小化：

- 组件探活（db / cache / plugins）由健康检查与启动流程写入 Gauge；
- 请求统计由 RequestMetricsMiddleware 采集；
- 进程级基础指标（uptime / GC）在渲染时现算，保证时效。

线程安全：dict 操作在 CPython 下原子，指标粒度无需锁。
"""

from __future__ import annotations

import gc
import time
from collections.abc import Iterable
from typing import Any, TypeVar

from starlette.middleware.base import BaseHTTPMiddleware

_MetricT = TypeVar("_MetricT", bound="Metric")

# ── 指标对象 ──────────────────────────────────────────────────────────────

_T = tuple[tuple[str, str], ...]  # ((label_name, label_value), ...) 固定排序


def _normalize_labels(labelnames: tuple[str, ...], labels: dict[str, Any] | None) -> _T:
    """标签规范化：固定顺序 + 缺省补空串，保证同维度组可稳定聚合。"""
    labels = labels or {}
    return tuple((name, str(labels.get(name, ""))) for name in labelnames)


def _labels_fmt(key: _T) -> str:
    if not key:
        return ""
    inner = ",".join(f'{k}="{v}"' for k, v in key)
    return f"{{{inner}}}"


class Metric:
    """指标基类：注册时登记 help/type，子类维护数值存储。"""

    def __init__(self, name: str, help: str, labelnames: tuple[str, ...] = ()) -> None:
        self.name = name
        self.help = help
        self.labelnames = labelnames

    @property
    def type(self) -> str:  # pragma: no cover - 抽象
        raise NotImplementedError

    def render(self) -> str:
        return b"" if False else ""


class Counter(Metric):
    """单调递增计数器（请求数、事件数）。"""

    def __init__(self, name: str, help: str, labelnames: tuple[str, ...] = ()) -> None:
        super().__init__(name, help, labelnames)
        self._values: dict[_T, float] = {}

    @property
    def type(self) -> str:
        return "counter"

    def inc(self, amount: float = 1, **labels: Any) -> None:
        key = _normalize_labels(self.labelnames, labels)
        self._values[key] = self._values.get(key, 0.0) + amount

    def render(self) -> str:
        lines = [f"# HELP {self.name} {self.help}", f"# TYPE {self.name} counter"]
        lines += [f"{self.name}{_labels_fmt(k)} {v}" for k, v in sorted(self._values.items())]
        return "\n".join(lines)


class Gauge(Metric):
    """可增可减的当前值（在途请求、探活状态、uptime）。"""

    def __init__(self, name: str, help: str, labelnames: tuple[str, ...] = ()) -> None:
        super().__init__(name, help, labelnames)
        self._values: dict[_T, float] = {}

    @property
    def type(self) -> str:
        return "gauge"

    def set(self, value: float, **labels: Any) -> None:
        self._values[_normalize_labels(self.labelnames, labels)] = float(value)

    def inc(self, amount: float = 1, **labels: Any) -> None:
        key = _normalize_labels(self.labelnames, labels)
        self._values[key] = self._values.get(key, 0.0) + amount

    def dec(self, amount: float = 1, **labels: Any) -> None:
        key = _normalize_labels(self.labelnames, labels)
        self._values[key] = self._values.get(key, 0.0) - amount

    def render(self) -> str:
        lines = [f"# HELP {self.name} {self.help}", f"# TYPE {self.name} gauge"]
        lines += [f"{self.name}{_labels_fmt(k)} {v}" for k, v in sorted(self._values.items())]
        return "\n".join(lines)


class Histogram(Metric):
    """观测值直方图：固定桶 + 累计计数，支持分位数聚合。"""

    def __init__(
        self, name: str, help: str, labelnames: tuple[str, ...] = (), buckets: Iterable[float] = ()
    ) -> None:
        super().__init__(name, help, labelnames)
        self._buckets = (
            tuple(sorted(buckets))
            if buckets
            else (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
        )
        self._counts: dict[_T, list[int]] = {}
        self._sums: dict[_T, float] = {}

    @property
    def type(self) -> str:
        return "histogram"

    def observe(self, value: float, **labels: Any) -> None:
        key = _normalize_labels(self.labelnames, labels)
        counts = self._counts.setdefault(key, [0] * (len(self._buckets) + 1))
        for i, bound in enumerate(self._buckets):
            if value <= bound:
                counts[i] += 1
        counts[-1] += 1  # +Inf
        self._sums[key] = self._sums.get(key, 0.0) + value

    def render(self) -> str:
        lines = [f"# HELP {self.name} {self.help}", f"# TYPE {self.name} histogram"]
        for key, counts in sorted(self._counts.items()):
            sfx = _labels_fmt(key)
            for i, bound in enumerate(self._buckets):
                lines.append(f"{self.name}_bucket{_merge_labels(key, ('le', str(bound)))} {counts[i]}")
            lines.append(f"{self.name}_bucket{_merge_labels(key, ('le', '+Inf'))} {counts[-1]}")
            lines.append(f"{self.name}_sum{sfx} {self._sums.get(key, 0.0)}")
            lines.append(f"{self.name}_count{sfx} {counts[-1]}")
        return "\n".join(lines)


def _merge_labels(key: _T, extra: tuple[str, str]) -> str:
    """现有标签 + 追加标签（le）渲染为 Prometheus 标签串。"""
    pairs = list(key) + [extra]
    inner = ",".join(f'{k}="{v}"' for k, v in pairs)
    return f"{{{inner}}}"


# ── 注册表 ────────────────────────────────────────────────────────────────


class MetricsRegistry:
    """收集全部指标并渲染 Prometheus TEXT 格式。进程内单例。"""

    def __init__(self) -> None:
        self._metrics: dict[str, Metric] = {}

    def counter(self, name: str, help: str, labelnames: tuple[str, ...] = ()) -> Counter:
        return self._register(Counter(name, help, labelnames))

    def gauge(self, name: str, help: str, labelnames: tuple[str, ...] = ()) -> Gauge:
        return self._register(Gauge(name, help, labelnames))

    def histogram(
        self, name: str, help: str, labelnames: tuple[str, ...] = (), buckets: Iterable[float] = ()
    ) -> Histogram:
        return self._register(Histogram(name, help, labelnames, buckets))

    def _register(self, metric: _MetricT) -> _MetricT:
        if metric.name in self._metrics:
            raise ValueError(f"指标重复注册: {metric.name}")
        self._metrics[metric.name] = metric
        return metric

    def render(self) -> str:
        """渲染全部指标；进程基础指标在此现算（若已注册相关 gauge）。"""
        uptime = self._metrics.get("vulnscope_process_uptime_seconds")
        gc_count = self._metrics.get("vulnscope_python_gc_count")
        if isinstance(uptime, Gauge):
            uptime.set(max(0.0, time.monotonic() - _START_MONOTONIC))
        if isinstance(gc_count, Gauge):
            gc_count.set(sum(gc.get_count()))
        blocks = [
            m.render() for _, m in sorted(self._metrics.items()) if isinstance(m, Counter | Gauge | Histogram)
        ]
        blocks.append("# EOF")
        return "\n".join(blocks) + "\n"


_START_MONOTONIC = time.monotonic()

# 进程级单例：指标名必须全局唯一，注册须在导入期完成（见 metrics.init_metrics()）。
registry = MetricsRegistry()


def init_metrics() -> dict[str, Any]:
    """装配应用级指标（幂等调用），供中间件与 /metrics 端点引用。

    Returns:
        指标句柄字典：http_total / http_duration / http_inflight /
        db_health / cache_health / plugins_loaded / uptime / gc。
    """
    global _INITIALIZED, _HANDLES
    if _INITIALIZED:
        return _HANDLES

    http_total = registry.counter("vulnscope_http_requests_total", "HTTP 请求总数", ("method", "status"))
    http_duration = registry.histogram(
        "vulnscope_http_request_duration_seconds", "HTTP 请求耗时（秒）", ("method",)
    )
    http_inflight = registry.gauge("vulnscope_http_requests_inflight", "处理中请求数")
    db_health = registry.gauge("vulnscope_db_healthy", "数据库连通（1=up 0=down）")
    cache_health = registry.gauge("vulnscope_cache_healthy", "缓存后端自检（1=up 0=down）")
    plugins_loaded = registry.gauge("vulnscope_plugins_loaded", "已加载插件总数")
    uptime = registry.gauge("vulnscope_process_uptime_seconds", "进程运行时长（秒）")
    gc_metric = registry.gauge("vulnscope_python_gc_count", "Python GC 各代回收累计次数")

    handles = {
        "http_total": http_total,
        "http_duration": http_duration,
        "http_inflight": http_inflight,
        "db_health": db_health,
        "cache_health": cache_health,
        "plugins_loaded": plugins_loaded,
        "uptime": uptime,
        "gc": gc_metric,
    }
    _HANDLES.update(handles)
    _INITIALIZED = True
    return _HANDLES


_INITIALIZED = False
_HANDLES: dict[str, Any] = {}


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    """请求度量中间件：请求计数 / 耗时直方图 / 在途数 + 结构化访问日志。

    依赖外层 RequestIdContextMiddleware 已就绪 request_id context。
    """

    _handles: dict[str, Any] | None = None

    def _get_handles(self) -> dict[str, Any]:
        if self._handles is None:
            self._handles = init_metrics()
        return self._handles

    async def dispatch(self, request, call_next) -> Any:  # noqa: ANN001
        handles = self._get_handles()
        start = time.perf_counter()
        handles["http_inflight"].inc()
        try:
            response = await call_next(request)
        finally:
            handles["http_inflight"].dec()
        duration = time.perf_counter() - start
        method = request.method
        status = response.status_code
        handles["http_total"].inc(method=method, status=str(status))
        handles["http_duration"].observe(duration, method=method)
        # 访问日志（DEBUG 级别，仅写入文件供回溯分析；控制台见 uvicorn 原生日志）。
        from app.core.logging import get_logger
        from app.core.request_id import get_request_id

        get_logger("access").debug(
            "request",
            extra={
                "method": method,
                "path": str(request.url.path),
                "status": status,
                "duration_ms": round(duration * 1000, 1),
                "request_id": get_request_id(),
                "client": request.client.host if request.client else "",
            },
        )
        response.headers["X-Process-Time"] = f"{duration * 1000:.1f}ms"
        return response
