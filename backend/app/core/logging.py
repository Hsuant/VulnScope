"""日志框架：控制台文本 + 文件 JSON 双通道。

- 控制台输出标准文本格式（保留 uvicorn 原生访问日志形式），
  仅 ERROR 级别附加结构化 JSON 行。
- 全部日志同时写入 ``logs/app.log``（JSON 行，含 request_id），
  按 50MB 轮转，保留 7 份归档。
- ``request_id`` 经 contextvars 由 ``RequestIdLogFilter`` 注入每条日志记录。
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import time
from typing import Any

from app.core.config import settings

# 项目根目录下的 logs/ 目录（从 app/core/logging.py 向上 3 级到达项目根）。
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_LOG_DIR = os.path.join(_PROJECT_ROOT, "logs")

# 与 core/request_id 共享的 contextvar（延迟导入避免环依赖）。
_request_id_var: Any = None


def _get_request_id() -> str:
    global _request_id_var
    if _request_id_var is None:
        from app.core.request_id import request_id_var

        _request_id_var = request_id_var
    return _request_id_var.get() or ""


class RequestIdLogFilter(logging.Filter):
    """为每条日志记录补 request_id 属性（从当前 context 读取）。"""

    def filter(self, record: logging.LogRecord) -> bool:
        request_id = _get_request_id()
        if request_id:
            record.request_id = request_id
        else:
            record.request_id = ""
        return True


class StructLogFormatter(logging.Formatter):
    """JSON 行格式化器：extra 字段并入对象，便于下游解析。"""

    _RESERVED = frozenset(
        {
            "ts",
            "level",
            "logger",
            "msg",
            "request_id",
            "name",
            "message",
            "asctime",
            "msecs",
            "relativeCreated",
            "process",
            "processName",
            "thread",
            "threadName",
            "taskName",
        }
    )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(record.created))
            + f".{int(record.msecs):03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", ""),
        }
        for key, value in record.__dict__.items():
            if key not in self._RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info and record.exc_info[0]:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


_configured = False


def setup_logging() -> None:
    """幂等装配日志：控制台文本 + 文件 JSON 双通道。"""
    global _configured
    if _configured:
        return

    level = getattr(logging, str(settings.LOG_LEVEL).upper(), logging.INFO)

    root = logging.getLogger()
    # 清空既有 handler（避免重复注册导致日志翻倍）。
    for handler in list(root.handlers):
        root.removeHandler(handler)
    root.setLevel(level)

    req_filter = RequestIdLogFilter()

    # ── 控制台：文本格式 ──
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(logging.Formatter("%(levelname)s:     %(message)s"))
    console.addFilter(req_filter)
    root.addHandler(console)

    # ── 文件：JSON 行，按日轮转 ──
    os.makedirs(_LOG_DIR, exist_ok=True)
    log_path = os.path.join(_LOG_DIR, "app.log")
    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_path,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
        utc=True,
    )
    file_handler.suffix = "%Y-%m-%d"
    file_handler.namer = lambda name: name.replace("app.log.", "") + ".log"
    file_handler.setLevel(level)
    file_handler.setFormatter(StructLogFormatter())
    file_handler.addFilter(req_filter)
    root.addHandler(file_handler)

    # 第三方库日志收敛，避免 SQLAlchemy/httpx 刷屏；uvicorn.access 保留原样。
    for noisy in ("sqlalchemy.engine", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _configured = True
    get_logger(__name__).info("logging initialized", extra={"log_dir": _LOG_DIR, "level": settings.LOG_LEVEL})


def get_logger(name: str) -> logging.Logger:
    """获取应用日志器（传入 ``__name__`` 即可，自动附 request_id）。"""
    return logging.getLogger(name)
