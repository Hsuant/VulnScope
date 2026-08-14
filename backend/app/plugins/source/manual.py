"""Manual Source 插件：手动录入 POC 的包装器。

手动录入的 POC 不需要额外 fetch，直接通过 API 创建。
此插件主要提供注册占位，供插件面板展示。
"""

from __future__ import annotations

from typing import Any

from app.plugins.base import NormalizedPoc, PocSource


class ManualSource(PocSource):
    """手动录入来源插件。

    手动录入不经过 fetch() 管道，直接由 API 创建。
    此插件仅作为注册占位，供 UI 插件面板展示"来源类型"。
    """

    name: str = "manual"
    version: str = "1.0.0"

    def fetch(self, params: dict[str, Any]) -> list[NormalizedPoc]:
        """手动来源不提供 fetch 能力。

        Returns:
            空列表。手动录入的 POC 直接通过 API 创建。
        """
        return []


# 注册实例
source = ManualSource()
