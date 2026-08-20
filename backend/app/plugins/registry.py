"""插件注册表：发现、加载、生命周期管理。

两路发现（方案 §7.2）：
1. importlib.metadata.entry_points(group="vulnscope.plugins") — 第三方包
2. 项目内 plugins/ 目录约定扫描 — 内置插件

启动时扫描加载，运行期仅可整槽禁用。
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from dataclasses import dataclass
from typing import Any

from app.plugins.base import PocParser, PocSource

logger = logging.getLogger(__name__)


@dataclass
class PluginEntry:
    """插件注册条目。"""

    slot: str  # parser / source / verifier / exporter / consumer
    name: str
    version: str
    instance: Any
    enabled: bool = True


class PluginRegistry:
    """内存注册表：{slot: {name: PluginEntry}}。"""

    def __init__(self) -> None:
        self._plugins: dict[str, dict[str, PluginEntry]] = {}

    def register(self, slot: str, name: str, version: str, instance: Any) -> None:
        """注册插件到指定槽位。"""
        self._plugins.setdefault(slot, {})[name] = PluginEntry(
            slot=slot, name=name, version=version, instance=instance
        )
        logger.info("plugin registered", extra={"slot": slot, "pname": name, "version": version})

    def get(self, slot: str, name: str) -> PluginEntry | None:
        """按槽位和名称获取插件。"""
        return self._plugins.get(slot, {}).get(name)

    def list(self, slot: str | None = None) -> list[PluginEntry]:
        """列出插件。slot=None 时返回所有插件。"""
        if slot is not None:
            return list(self._plugins.get(slot, {}).values())
        return [e for group in self._plugins.values() for e in group.values()]

    def set_enabled(self, slot: str, name: str, enabled: bool) -> bool:
        """启用/禁用指定插件。"""
        entry = self.get(slot, name)
        if entry is None:
            return False
        entry.enabled = enabled
        return True

    def discover_internal(self) -> None:
        """扫描 plugins/ 子目录发现内置插件。

        约定：每个插件模块暴露 `parser` / `source` 等命名实例。
        """
        import app.plugins.parser as parser_pkg
        import app.plugins.source as source_pkg

        # 扫描 parser 子目录
        self._scan_package(parser_pkg, "parser")

        # 扫描 source 子目录
        self._scan_package(source_pkg, "source")

    def _scan_package(self, package: Any, slot: str) -> None:
        """扫描包内所有模块，寻找命名实例。"""
        prefix = package.__name__ + "."
        for _, modname, ispkg in pkgutil.walk_packages(
            package.__path__, prefix=prefix, onerror=lambda x: None
        ):
            if ispkg:
                continue
            if modname.endswith("__init__"):
                continue
            try:
                mod = importlib.import_module(modname)
            except Exception as exc:
                logger.warning("plugin module load failed", extra={"modname": modname, "error": str(exc)})
                continue

            # 检查模块中是否有约定名称的实例
            instance = getattr(mod, "parser", None) or getattr(mod, "source", None)
            if instance is None:
                continue

            # 自动推断名称和版本
            name = getattr(instance, "name", modname.rsplit(".", 1)[-1])
            version = getattr(instance, "version", "0.1.0")

            # 校验接口契约
            if not self._validate_contract(instance, slot):
                logger.warning("plugin contract validation failed", extra={"slot": slot, "name": name})
                continue

            self.register(slot, name, version, instance)

    def _validate_contract(self, instance: Any, slot: str) -> bool:
        """校验插件实例是否实现对应接口契约。"""
        if slot == "parser":
            return isinstance(instance, PocParser)
        if slot == "source":
            return isinstance(instance, PocSource)
        # verifier/exporter/consumer 暂不校验
        return True


registry = PluginRegistry()
