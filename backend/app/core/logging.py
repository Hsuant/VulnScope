"""日志框架：控制台文本 + 文件 JSON 双通道。

设计概述
--------
本模块为 VulnScope 提供统一日志基础设施，遵循「单一入口、双通道输出、
结构化字段」原则：

1. **单一入口**：全项目通过 :func:`get_logger` 获取日志器，便于集中治理
   （未来如需挂载 filter / 自定义子类，只需改这一处）。
2. **双通道输出**：
   - 控制台：人类可读文本，ERROR 及以上级别额外追加结构化 JSON 行，
     便于终端快速定位异常上下文。
   - 文件：JSON Lines（每行一个对象），按日存储为 ``logs/<YYYY-MM-DD>.log``，
     含 ``request_id`` 便于链路追踪，保留 ``LOG_RETENTION_DAYS`` 天后自动清理。
3. **结构化字段**：通过 ``extra={...}`` 传入的键值对并入 JSON 对象，
   避免字符串拼接带来的解析成本。

时区约定
--------
所有时间戳均为 UTC（带 ``Z`` 后缀），日志文件按 UTC 日期切分。
采用 UTC 而非本地时区，保证多机房 / 容器环境下日志时间线一致，
便于跨节点对账。
"""

from __future__ import annotations

import glob
import json
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings

# ── 日志目录解析 ──────────────────────────────────────────────────────────
# 优先级：环境变量 LOG_DIR > .git 哨兵（本地开发）> pyproject.toml 哨兵
# （Docker）> 兜底 3 层上溯。解耦「代码位置」与「日志落盘位置」，
# 生产环境可通过 VULNSCOPE_LOG_DIR 指向独立日志卷。


def _find_marker_root(marker: str, *, expect_dir: bool) -> str:
    """从本文件所在目录逐级上溯，查找包含指定哨兵文件/目录的祖先目录。

    哨兵机制避免硬编码上溯层数：本地开发（``backend/app/core/``）
    与 Docker（``app/app/core/``）目录结构不同，层数不一致。

    Args:
        marker: 哨兵文件/目录名，如 ``.git`` 或 ``pyproject.toml``。
        expect_dir: ``True`` 时把 marker 当目录检测，``False`` 当文件检测。

    Returns:
        命中哨兵的目录绝对路径；未命中返回空串。
    """
    current = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):  # 上限 10 层，防止异常目录结构下死循环
        target = os.path.join(current, marker)
        if (os.path.isdir(target) if expect_dir else os.path.isfile(target)):
            return current
        parent = os.path.dirname(current)
        if parent == current:  # 已到文件系统根，无法继续上溯
            break
        current = parent
    return ""


def _resolve_log_dir() -> str:
    """解析日志落盘目录。

    解析顺序（前者优先）：
        1. ``settings.LOG_DIR``（环境变量 ``VULNSCOPE_LOG_DIR`` 覆盖）；
        2. ``.git`` 哨兵目录（本地开发 → git 项目根，日志落在项目根/logs）；
        3. ``pyproject.toml`` 哨兵文件（Docker → /app/，日志落在 /app/logs）；
        4. 兜底：从本文件上溯 3 层（兼容旧路径假设）。

    Returns:
        日志目录绝对路径。
    """
    # 显式环境变量优先，生产环境可指向独立日志卷（如 /var/log/vulnscope）。
    explicit = getattr(settings, "LOG_DIR", "") or ""
    if explicit:
        return os.path.abspath(explicit)
    for marker, expect_dir in ((".git", True), ("pyproject.toml", False)):
        root = _find_marker_root(marker, expect_dir=expect_dir)
        if root:
            return os.path.join(root, "logs")
    # 兜底：维持旧行为，从本文件上溯 3 层到达项目根。
    fallback = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    return os.path.join(fallback, "logs")


_LOG_DIR = _resolve_log_dir()

# ── request_id 上下文注入 ────────────────────────────────────────────────
# 与 ``app/core/request_id`` 共享同一 contextvar，但采用延迟导入以打破
# ``logging <-> request_id`` 的环依赖（request_id 模块不直接依赖 logging，
# 但 logging 在运行期需要读取 contextvar）。首次调用时完成绑定并缓存，
# 后续调用零额外导入开销。


def _get_request_id() -> str:
    """读取当前请求的 request_id（无请求上下文时返回空串）。

    contextvar 的绑定结果做模块级缓存：第一次调用触发导入，之后直接读取，
    避免每条日志都付出 import 查找成本。
    """
    global _request_id_var
    if _request_id_var is None:
        from app.core.request_id import request_id_var

        _request_id_var = request_id_var
    return _request_id_var.get() or ""


_request_id_var: Any = None


class RequestIdLogFilter(logging.Filter):
    """为每条日志记录补 ``request_id`` 属性（从当前 context 读取）。

    挂载在 root logger 的各 handler 上，通过 propagation 覆盖全部子日志器，
    无需每个模块自行处理。无请求上下文时 ``request_id`` 为空串（如启动期日志）。
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _get_request_id()
        return True


# ── JSON 行格式化器 ──────────────────────────────────────────────────────


class StructLogFormatter(logging.Formatter):
    """JSON 行格式化器：``extra`` 字段并入对象，便于下游（ELK/Loki）解析。

    输出字段顺序固定为 ``ts / level / logger / msg / request_id``，随后是
    调用方通过 ``extra=`` 传入的任意键值。标准 :class:`LogRecord` 属性
    （如 ``levelno``、``pathname``）通过 ``_RESERVED`` 集合过滤，避免污染输出。
    """

    # 标准 LogRecord 属性 + 本格式化器自产字段，一律不透传到 JSON payload。
    # 补全 Python 3.10+ 的全部标准属性，防止意外泄漏到下游解析。
    _RESERVED = frozenset(
        {
            # 自产字段（本格式化器显式写入）
            "ts",
            "level",
            "logger",
            "msg",
            "request_id",
            # 标准 LogRecord 属性（logging.LogRecord.__init__ 设置的全部）
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "message",
            "asctime",
            "taskName",
        }
    )

    def format(self, record: logging.LogRecord) -> str:
        """渲染单条日志为 JSON 字符串。

        Args:
            record: 待渲染的日志记录。

        Returns:
            一行 JSON 文本（``ensure_ascii=False``，保留中文可读性）。
        """
        # 时间戳：ISO-8601 + 毫秒 + UTC（Z 后缀）。created 为 epoch 秒，
        # msecs 为毫秒部分，拼接后精度到毫秒。
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S."
        ) + f"{record.msecs:03.0f}Z"
        payload: dict[str, Any] = {
            "ts": ts,
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", ""),
        }
        # 透传调用方 extra 键值（跳过保留字段与私有属性）。
        for key, value in record.__dict__.items():
            if key not in self._RESERVED and not key.startswith("_"):
                payload[key] = value
        # 异常信息：渲染为多行文本字符串，便于在 JSON 行中检索。
        if record.exc_info and record.exc_info[0]:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """控制台格式化器：常规文本，ERROR 及以上追加 JSON 行。

    设计取舍：控制台主要面向人眼，故默认输出简洁文本；但 ERROR/CRITICAL
    往往需要结构化字段（request_id、exception）才能定位，故在文本行之后
    追加一条 JSON 行，兼顾可读性与可检索性。
    """

    _TEXT_FMT = logging.Formatter("%(levelname)s:     %(message)s")
    _JSON_FMT = StructLogFormatter()

    def format(self, record: logging.LogRecord) -> str:
        """渲染控制台输出：低级别文本，ERROR+ 追加 JSON 行。

        Args:
            record: 待渲染的日志记录。

        Returns:
            文本行；ERROR 及以上时其后另起一行附 JSON。
        """
        text = self._TEXT_FMT.format(record)
        if record.levelno >= logging.ERROR:
            # 追加结构化行，便于终端复制后直接喂给 jq 等工具。
            text = f"{text}\n{self._JSON_FMT.format(record)}"
        return text


# ── 按日轮转文件处理器 ──────────────────────────────────────────────────


class DailyLogHandler(logging.Handler):
    """按日轮转的日志处理器，文件名格式：``YYYY-MM-DD.log``。

    每天 UTC 午夜自动切换文件，保留 ``retention_days`` 天，超期自动清理。
    线程安全：通过 :class:`threading.Lock` 保护文件写入、切换与清理。

    与标准库 :class:`logging.handlers.TimedRotatingFileHandler` 的区别：
    本处理器直接以日期命名「当前文件」（而非固定名 + 日期后缀），省去
    namer/rotator 的间接映射，文件名即语义，便于外部日志采集器直接按日期轮询。
    """

    def __init__(
        self,
        log_dir: str,
        retention_days: int = 30,
        level: int = logging.NOTSET,
    ) -> None:
        """初始化按日日志处理器。

        Args:
            log_dir: 日志落盘目录，不存在时自动创建。
            retention_days: 旧日志保留天数，``<= 0`` 表示永不清理。
            level: 处理器最低日志级别。
        """
        super().__init__(level)
        self.log_dir = log_dir
        self.retention_days = retention_days
        self._lock = threading.Lock()
        self._date: str | None = None  # 当前文件对应的 UTC 日期
        self._file: logging.StreamHandler | None = None  # 委托的内部 handler
        self._formatter: logging.Formatter | None = None

    def _get_date(self) -> str:
        """返回当前 UTC 日期字符串 ``YYYY-MM-DD``。"""
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _open_file(self, date_str: str) -> logging.StreamHandler:
        """打开或创建当日日志文件，返回包装好的 StreamHandler。

        委托 StreamHandler 是为了复用其格式化与 emit 逻辑，避免重复实现。

        Args:
            date_str: 日期字符串 ``YYYY-MM-DD``。

        Returns:
            绑定到当日文件流的 StreamHandler。
        """
        os.makedirs(self.log_dir, exist_ok=True)
        path = os.path.join(self.log_dir, f"{date_str}.log")
        # 追加模式：进程重启后续写当日文件，不截断历史。
        # 生命周期由本 Handler 管理（close 时显式关闭），故忽略 SIM115。
        stream = open(path, "a", encoding="utf-8")  # noqa: SIM115
        handler = logging.StreamHandler(stream)
        handler.setLevel(self.level)
        if self._formatter:
            handler.setFormatter(self._formatter)
        return handler

    def _rotate(self) -> None:
        """关闭旧文件，打开新日期的文件。

        必须在持有 ``self._lock`` 时调用。旧文件关闭失败被吞掉（已尽力），
        避免因单个关闭异常阻塞整个日志通道。
        """
        if self._file:
            old = self._file
            self._file = None  # 先解引用，保证异常路径下也不会误用旧 handler
            try:
                old.stream.close()
            except Exception:
                pass
        new_date = self._get_date()
        self._date = new_date
        self._file = self._open_file(new_date)

    def _cleanup(self) -> None:
        """清理超过 ``retention_days`` 的旧日志文件。

        通过文件名解析日期（而非 mtime），保证清理依据与文件名一致，
        不受文件被 touch / 复制等操作影响。仅在跨日切换时调用一次，
        频率低、开销可忽略。
        """
        if self.retention_days <= 0:
            return
        cutoff = datetime.now(timezone.utc).timestamp() - self.retention_days * 86400
        # 仅匹配严格 YYYY-MM-DD.log 命名，避免误删其他文件。
        pattern = os.path.join(self.log_dir, "????-??-??.log")
        for path in glob.glob(pattern):
            try:
                fname = os.path.basename(path)
                # 从文件名解析日期：YYYY-MM-DD.log → 取前 10 字符。
                file_date = datetime.strptime(fname[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if file_date.timestamp() < cutoff:
                    os.remove(path)
            except (ValueError, OSError):
                # 文件名不合规或被占用，跳过不中断清理。
                pass

    def setFormatter(self, fmt: logging.Formatter) -> None:  # noqa: N802
        """覆写格式化器，并同步给已打开的内部 handler。

        Args:
            fmt: 格式化器实例。
        """
        self._formatter = fmt
        if self._file:
            self._file.setFormatter(fmt)

    def emit(self, record: logging.LogRecord) -> None:
        """写入日志记录，必要时切换日期文件。

        每次 emit 都比对当前日期：跨日时先切换文件再清理旧文件，
        随后委托内部 StreamHandler 完成实际写入。全部路径异常兜底
        ``handleError``，符合 :class:`logging.Handler` 契约。

        Args:
            record: 待写入的日志记录。
        """
        today = self._get_date()
        with self._lock:
            try:
                if self._date != today:
                    self._rotate()
                    self._cleanup()
                if self._file:
                    self._file.emit(record)
            except Exception:
                self.handleError(record)

    def flush(self) -> None:
        """刷新内部文件流缓冲。

        标准库在进程退出（``logging.shutdown``）时会调用各 handler 的 flush。
        本处理器把文件流托管给内部 StreamHandler，故需委托刷新，否则基类
        ``flush`` 会因找不到 ``self.stream`` 抛 ``AttributeError``。
        """
        with self._lock:
            if self._file:
                try:
                    self._file.flush()
                except Exception:
                    pass

    def close(self) -> None:
        """关闭文件句柄并调用基类清理。

        必须先关闭内部 handler 持有的文件流，再调用基类 ``close``
        完成注册表摘除等收尾。
        """
        with self._lock:
            if self._file:
                try:
                    self._file.stream.close()
                except Exception:
                    pass
                self._file = None
        super().close()


# ── 装配入口 ─────────────────────────────────────────────────────────────

_configured = False


def setup_logging() -> None:
    """幂等装配日志：控制台文本 + 文件 JSON 双通道。

    幂等性：通过模块级 ``_configured`` 标志保证重复调用（如测试 reload）
    不会重复挂载 handler 导致日志翻倍。每次调用先清空 root 既有 handler，
    再按当前配置重建。

    配置项：
        - ``LOG_LEVEL``：全局最低日志级别（控制台 + 文件共用）。
        - ``LOG_RETENTION_DAYS``：文件日志保留天数。
        - ``LOG_DIR``：日志目录覆盖（可选）。
    """
    global _configured
    if _configured:
        return

    level = getattr(logging, str(settings.LOG_LEVEL).upper(), logging.INFO)

    root = logging.getLogger()
    # 清空既有 handler：避免 reload 场景下重复注册导致日志翻倍。
    for handler in list(root.handlers):
        root.removeHandler(handler)
    root.setLevel(level)

    # request_id 过滤器单例，挂载到所有 handler，子日志器经 propagation 自动继承。
    req_filter = RequestIdLogFilter()

    # ── 控制台：人类可读文本，ERROR+ 追加 JSON 行 ──
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(ConsoleFormatter())
    console.addFilter(req_filter)
    root.addHandler(console)

    # ── 文件：JSON Lines，按日轮转 ──
    daily_handler = DailyLogHandler(
        log_dir=_LOG_DIR,
        retention_days=settings.LOG_RETENTION_DAYS,
        level=level,
    )
    daily_handler.setFormatter(StructLogFormatter())
    daily_handler.addFilter(req_filter)
    root.addHandler(daily_handler)

    # 第三方库日志收敛：SQLAlchemy / httpx 默认 INFO 会刷屏，压到 WARNING。
    # uvicorn.access 保留原样（访问日志由本应用 RequestMetricsMiddleware 接管，
    # 不依赖 uvicorn 自带访问日志）。
    for noisy in ("sqlalchemy.engine", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _configured = True
    get_logger(__name__).info(
        "logging initialized",
        extra={
            "log_dir": _LOG_DIR,
            "level": settings.LOG_LEVEL,
            "retention_days": settings.LOG_RETENTION_DAYS,
        },
    )


def get_logger(name: str) -> logging.Logger:
    """获取应用日志器（全项目统一入口）。

    传入 ``__name__`` 即可。request_id 由挂在 root handler 的
    :class:`RequestIdLogFilter` 自动注入，无需调用方关心。

    Args:
        name: 日志器名称，通常传 ``__name__``。

    Returns:
        标准 :class:`logging.Logger` 实例。
    """
    return logging.getLogger(name)
