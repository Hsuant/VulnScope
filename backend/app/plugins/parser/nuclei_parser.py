"""Nuclei YAML 模板解析器（方案 §6.2 ~ §6.4）。

将标准 Nuclei 模板文本解析为 NormalizedPoc IR，供导入管道使用。
支持模板元数据提取、CVE 关联、标签解析、请求块验证。
"""

from __future__ import annotations

import re
from typing import Any

import yaml

from app.plugins.base import NormalizedPoc, PocParser

# 合法 severity 值
VALID_SEVERITIES = {"info", "low", "medium", "high", "critical"}

# 合法请求块类型
VALID_PROTOCOL_BLOCKS = {"http", "dns", "network", "ssl", "headless", "websocket", "file", "code"}

# 禁止的请求块类型（v1 拒绝入库）
FORBIDDEN_BLOCKS_V1 = {"headless", "code"}

# CVE 编号正则
CVE_PATTERN = re.compile(r"^CVE-\d{4}-\d{4,}$", re.IGNORECASE)

# 模板名称正则（与 poc.name 约束一致）
NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9.-]*$")


class NucleiParser(PocParser):
    """Nuclei YAML 模板解析器。

    支持标准 ProjectDiscovery 模板语法，提取元数据映射到 NormalizedPoc。
    """

    name: str = "nuclei-yaml"
    supported_formats: set[str] = {"nuclei-yaml", "yaml"}

    def parse(self, raw: str | bytes, format: str | None = None) -> list[NormalizedPoc]:
        """解析 Nuclei YAML 文本为 NormalizedPoc 列表。

        Args:
            raw: YAML 模板文本（str 或 bytes）。
            format: 格式标识，默认 "nuclei-yaml"。

        Returns:
            NormalizedPoc 列表（通常单模板单条，但兼容多文档 YAML）。

        Raises:
            ValueError: YAML 解析失败或结构严重异常。
        """
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")

        documents = list(yaml.safe_load_all(raw))
        results: list[NormalizedPoc] = []

        for doc in documents:
            if not isinstance(doc, dict):
                continue  # 跳过非映射文档（如纯标量）
            try:
                poc = self._parse_single(doc, raw)
                results.append(poc)
            except (ValueError, KeyError) as exc:
                # 单条解析失败不阻塞整批
                import logging

                logging.getLogger(__name__).warning("Nuclei 模板解析跳过: %s", exc)
                continue

        return results

    def _parse_single(self, doc: dict, raw_text: str) -> NormalizedPoc:
        """解析单个 Nuclei 模板文档。"""
        template_id = doc.get("id", "")
        if not template_id or not NAME_PATTERN.match(template_id):
            # 尝试转为小写再匹配（很多模板用大写 CVE-ID 作为 id）
            if not NAME_PATTERN.match(template_id.lower()):
                raise ValueError(f"模板 id 非法: {template_id}")
            template_id = template_id.lower()

        info = doc.get("info", {})
        if not isinstance(info, dict) or not info:
            raise ValueError("模板缺少 info 元数据块或 info 为空")

        # 提取元数据
        name = template_id
        title = info.get("name", "") or template_id
        author = info.get("author", "")
        severity = str(info.get("severity", "info")).lower()
        if severity not in VALID_SEVERITIES:
            severity = "info"

        description = info.get("description", "")
        remediation = info.get("remediation", "")

        # 提取分类信息
        classification = info.get("classification", {}) or {}
        cve_ids_raw = classification.get("cve-id", []) or []
        if isinstance(cve_ids_raw, str):
            cve_ids_raw = [cve_ids_raw]
        cve_ids = [c.upper() for c in cve_ids_raw if CVE_PATTERN.match(c)]

        # 提取标签
        tags_raw = info.get("tags", "")
        tags: list[str] = []
        if isinstance(tags_raw, str):
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
        elif isinstance(tags_raw, list):
            tags = [str(t).strip() for t in tags_raw if t]

        # 提取参考链接
        references_raw = info.get("reference", []) or []
        if isinstance(references_raw, str):
            references_raw = [references_raw]
        references = [str(r) for r in references_raw if r]

        # 提取 metadata（厂商/产品等信息）
        metadata = info.get("metadata", {}) or {}

        # 构建 extra_meta
        extra_meta: dict[str, Any] = {}
        if remediation:
            extra_meta["remediation"] = remediation
        if metadata:
            extra_meta["metadata"] = metadata
        if classification:
            extra_meta["classification"] = classification

        # 检测请求块
        present_blocks = [k for k in VALID_PROTOCOL_BLOCKS if k in doc]
        extra_meta["protocol_blocks"] = present_blocks

        # v1 安全拦截：禁止 headless / code 块
        forbidden = [b for b in FORBIDDEN_BLOCKS_V1 if b in present_blocks]
        if forbidden:
            extra_meta["v1_blocked_blocks"] = forbidden
            extra_meta["v1_blocked"] = True

        # 检测 unsafe raw 请求
        http_block = doc.get("http")
        if isinstance(http_block, list):
            for req in http_block:
                if isinstance(req, dict) and req.get("unsafe") and req.get("raw"):
                    extra_meta["unsafe_ack"] = False
                    break

        # 构建 POC 内容（使用原始文本，但做规范化）
        content = self._normalize_template(raw_text, doc)

        return NormalizedPoc(
            name=name,
            title=title or None,
            description=description or None,
            author=author or None,
            source="imported",
            severity=severity,
            content=content,
            format="nuclei-yaml",
            cve_ids=cve_ids,
            tags=tags,
            references=references,
            extra_meta=extra_meta,
        )

    def _normalize_template(self, raw_text: str, doc: dict) -> str:
        """规范化模板文本：统一换行、去尾随空白，保留 YAML 结构。"""
        text = raw_text.strip()
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = "\n".join(line.rstrip() for line in text.split("\n"))
        text = text.rstrip("\n") + "\n"
        return text

    def validate(self, poc: NormalizedPoc) -> list[str]:
        """Nuclei 模板专项校验（§6.4）。

        在 NormalizedPoc.validate_structure() 基础之上增加：
        1. 结构合法性：YAML 可解析
        2. 字段约束：severity 枚举、CVE 格式
        3. 请求块完整性：至少一个请求块
        4. matchers 语义
        5. 禁止执行型风险字段
        """
        errors = poc.validate_structure()

        # 尝试解析 content 为 YAML
        try:
            doc = yaml.safe_load(poc.content)
            if not isinstance(doc, dict):
                errors.append("模板内容不是合法的 YAML 映射")
                return errors
        except yaml.YAMLError as e:
            errors.append(f"YAML 解析失败: {e}")
            return errors

        # 检查 info 块
        info = doc.get("info")
        if not isinstance(info, dict):
            errors.append("缺少 info 元数据块")
            return errors

        # 检查请求块
        present_blocks = [k for k in VALID_PROTOCOL_BLOCKS if k in doc]
        if not present_blocks:
            errors.append("模板至少需要一种请求块（http/dns/network/ssl/websocket/file/code）")

        # 检查禁止块
        for banned in FORBIDDEN_BLOCKS_V1:
            if banned in doc:
                errors.append(f"v1 禁止 {banned} 请求块（无沙箱执行环境）")

        # 检查 http 块完整性
        http_block = doc.get("http")
        if isinstance(http_block, list):
            for i, req in enumerate(http_block):
                if isinstance(req, dict):
                    # method + path/raw 必须成对出现
                    has_path = bool(req.get("path")) or bool(req.get("raw"))
                    if req.get("method") and not has_path:
                        errors.append(f"http 请求 #{i} 有 method 但缺少 path/raw")
                    if has_path and not req.get("method"):
                        errors.append(f"http 请求 #{i} 有 path/raw 但缺少 method")

        # 检查 matchers 类型
        for block_name in present_blocks:
            block = doc.get(block_name)
            if isinstance(block, list):
                for item in block:
                    if isinstance(item, dict):
                        matchers = item.get("matchers", []) or []
                        if isinstance(matchers, dict):
                            matchers = [matchers]
                        for m in matchers:
                            if isinstance(m, dict):
                                mtype = m.get("type", "")
                                if mtype and mtype not in {
                                    "word",
                                    "regex",
                                    "status",
                                    "code",
                                    "size",
                                    "binary",
                                    "dsl",
                                    "condition",
                                }:
                                    errors.append(f"非法 matcher 类型: {mtype}")

        return errors


# 注册实例
parser = NucleiParser()
