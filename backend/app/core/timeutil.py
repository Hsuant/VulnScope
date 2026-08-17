"""时间序列化工具：统一把数据库时间序列化为带 UTC 偏移的 ISO 字符串。

SQLite 的 DateTime(timezone=True) 实际不存储时区，读回的是 naive UTC datetime；
直接 .isoformat() 输出的字符串不带时区偏移，前端 new Date() 会按浏览器本地时区
（如 UTC+8）解析，导致时间显示偏差（典型表现：刚创建/导入的 POC 显示成"8 小时前"）。
此工具统一补上 +00:00 偏移。
"""

from __future__ import annotations

import datetime as dt


def iso_utc(value: dt.datetime | None) -> str | None:
    """把 datetime 序列化为带 UTC 偏移的 ISO 字符串。

    naive（SQLite 存储的 UTC）补 +00:00；已带时区则原样保留。None 透传。
    """
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    return value.isoformat()
