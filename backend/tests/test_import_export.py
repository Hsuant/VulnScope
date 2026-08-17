"""导入导出 API 集成测试。

测试覆盖：
- 格式嗅探器
- YAML/JSON 导入
- 导入去重
- 导出 JSON/ Nuclei
- 权限控制
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

# ── 测试数据 ────────────────────────────────────────────────────────────

SAMPLE_NUCLEI_YAML = """id: test-import-yaml

info:
  name: Test Import YAML
  severity: medium
  author: tester
  description: A test POC for import
  tags: rce,oob

http:
  - method: GET
    path:
      - "{{BaseURL}}/test"
"""

SAMPLE_NUCLEI_YAML_2 = """id: test-import-yaml-2

info:
  name: Test Import YAML 2
  severity: high
  author: tester
  description: Another test POC for import

http:
  - method: POST
    path:
      - "{{BaseURL}}/test2"
"""

SAMPLE_JSON = json.dumps(
    [
        {
            "name": "test-import-json",
            "title": "Test Import JSON",
            "severity": "critical",
            "author": "tester",
            "description": "A test POC from JSON import",
            "content": "id: test-import-json\n\ninfo:\n  name: Test Import JSON\n  severity: critical\n",
            "cve_ids": ["CVE-2024-0002"],
            "tags": ["rce"],
        },
        {
            "name": "test-import-json-2",
            "title": "Test Import JSON 2",
            "severity": "high",
            "content": "id: test-import-json-2\n\ninfo:\n  name: Test Import JSON 2\n  severity: high\n",
        },
    ]
)

SAMPLE_MD = """---
name: test-markdown-doc
title: Test Markdown Doc
severity: high
author: tester
cve:
  - CVE-2024-9999
tags: [rce, md-test]
references:
  - https://example.com/advisory
---

# 概述

漏洞正文，含 `inline code` 与代码块：

```python
print("pwned")
```
"""

# 含完整 CVE 元数据的 Nuclei 模板（cvss-metrics/cvss-score/remediation/vendor/product）
SAMPLE_NUCLEI_YAML_CVE_META = """id: apache-log4j2-rce-cve-meta

info:
  name: Apache Log4j2 JNDI RCE
  author: security-team
  severity: critical
  description: Log4j2 JNDI lookup RCE.
  remediation: Upgrade to Log4j 2.15.0 or later.
  classification:
    cve-id:
      - CVE-2021-44228
    cvss-metrics: "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
    cvss-score: 9.8
  metadata:
    max-request: 1
    vendor: apache
    product: log4j

http:
  - method: GET
    path:
      - "{{BaseURL}}/test"
"""


class TestFormatDetector:
    """格式嗅探器测试。"""

    def test_detect_nuclei_yaml(self) -> None:
        from app.services.import_service import FormatDetector

        assert FormatDetector.detect(SAMPLE_NUCLEI_YAML) == "nuclei"

    def test_detect_json(self) -> None:
        from app.services.import_service import FormatDetector

        assert FormatDetector.detect(SAMPLE_JSON) == "json"

    def test_detect_json_single(self) -> None:
        from app.services.import_service import FormatDetector

        single = '{"name": "test", "content": "test"}'
        assert FormatDetector.detect(single) == "json"

    def test_detect_by_extension(self) -> None:
        from app.services.import_service import FormatDetector

        # Nuclei YAML by extension
        assert FormatDetector.detect("some content", "test.yaml") == "nuclei"
        # JSON by extension
        assert FormatDetector.detect("some content", "test.json") == "json"

    def test_detect_fallback(self) -> None:
        from app.services.import_service import FormatDetector

        # 未知格式降级为 raw-script
        # 使用包含 YAML 允许但非模板的内容触发 fallback
        assert FormatDetector.detect("\x00\x00\x00\x00binary data") == "raw-script"

    def test_detect_markdown_frontmatter(self) -> None:
        from app.services.import_service import FormatDetector

        # front-matter 起始的文档识别为 markdown（粘贴模式，无扩展名）
        assert FormatDetector.detect(SAMPLE_MD) == "markdown"

    def test_detect_markdown_by_extension(self) -> None:
        from app.services.import_service import FormatDetector

        assert FormatDetector.detect("# title", "doc.md") == "markdown"
        assert FormatDetector.detect("plain text", "doc.markdown") == "markdown"

    def test_detect_markdown_heading(self) -> None:
        from app.services.import_service import FormatDetector

        # 顶格 ATX 标题（# 后带空格）识别为 markdown
        assert FormatDetector.detect("# 漏洞概述\n\n正文", None) == "markdown"

    def test_detect_shebang_not_markdown(self) -> None:
        from app.services.import_service import FormatDetector

        # #! 无空格，不误判为 markdown；按扩展名归为 raw-script
        assert FormatDetector.detect("#!/bin/bash\necho hi", "run.sh") == "raw-script"


class TestImport:
    """POC 导入接口测试。"""

    @staticmethod
    def _import_content(
        client: TestClient, auth_header: dict, content: str, filename: str | None = None
    ) -> dict:
        """辅助：通过文本粘贴导入。"""
        params = {"content": content, "source": "imported"}
        if filename:
            params["filename"] = filename
        resp = client.post("/api/v1/import", params=params, headers=auth_header)
        assert resp.status_code == 200, f"import failed: {resp.text}"
        return resp.json()["data"]

    def test_import_yaml_success(self, client: TestClient, auth_header: dict) -> None:
        """导入 YAML 模板成功。"""
        result = self._import_content(client, auth_header, SAMPLE_NUCLEI_YAML)
        assert result["total"] == 1
        assert result["success"] == 1
        assert result["skipped"] == 0
        assert len(result["failed"]) == 0

        # 验证 POC 已入库
        resp = client.get("/api/v1/pocs/search?q=test-import-yaml", headers=auth_header)
        data = resp.json()["data"]
        assert data["total"] >= 1

    def test_import_json_success(self, client: TestClient, auth_header: dict) -> None:
        """导入 JSON 成功（多文档）。"""
        result = self._import_content(client, auth_header, SAMPLE_JSON)
        assert result["total"] == 2
        assert result["success"] == 2
        assert result["skipped"] == 0

    def test_import_duplicate(self, client: TestClient, auth_header: dict) -> None:
        """重复导入相同内容自动跳过。"""
        # 第一次导入
        result1 = self._import_content(client, auth_header, SAMPLE_NUCLEI_YAML)
        assert result1["success"] == 1

        # 第二次导入相同内容
        result2 = self._import_content(client, auth_header, SAMPLE_NUCLEI_YAML)
        assert result2["success"] == 0
        assert result2["skipped"] == 1

    def test_import_multiple_yaml(self, client: TestClient, auth_header: dict) -> None:
        """导入多个 YAML 模板（--- 分隔）。"""
        multi_yaml = SAMPLE_NUCLEI_YAML + "---\n" + SAMPLE_NUCLEI_YAML_2
        result = self._import_content(client, auth_header, multi_yaml)
        assert result["success"] >= 1

    def test_import_no_auth(self, client: TestClient) -> None:
        """未认证导入返回 401。"""
        resp = client.post("/api/v1/import", params={"content": SAMPLE_NUCLEI_YAML})
        assert resp.status_code == 401

    def test_import_empty_content(self, client: TestClient, auth_header: dict) -> None:
        """空内容导入返回 422。"""
        resp = client.post("/api/v1/import", params={}, headers=auth_header)
        assert resp.status_code == 422

    def test_import_with_cve(self, client: TestClient, auth_header: dict) -> None:
        """导入带 CVE 的 JSON 自动创建漏洞记录。"""
        result = self._import_content(client, auth_header, SAMPLE_JSON)
        assert result["success"] == 2

        # 验证 CVE 已创建
        resp = client.get("/api/v1/vulns?q=CVE-2024-0002", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] >= 1

    def test_import_syncs_cve_meta_to_new_vuln(
        self, client: TestClient, auth_header: dict, db: Session
    ) -> None:
        """导入带 CVE 元数据的 Nuclei 模板：CVE 不存在时自动创建并填充全部字段。"""
        result = self._import_content(client, auth_header, SAMPLE_NUCLEI_YAML_CVE_META)
        assert result["success"] == 1

        from app.models.poc import Vuln

        vuln = db.scalar(select(Vuln).where(Vuln.cve_id == "CVE-2021-44228"))
        assert vuln is not None
        assert vuln.cvss == 9.8
        assert vuln.cvss_metrics == "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
        assert vuln.severity == "critical"
        assert vuln.vendor == "apache"
        assert vuln.product == [{"vendor": "apache", "product": "log4j"}]
        assert vuln.remediation == {"mitigation": "Upgrade to Log4j 2.15.0 or later."}

    def test_import_syncs_cve_meta_fills_missing_only(
        self, client: TestClient, auth_header: dict, db: Session
    ) -> None:
        """导入时 CVE 已存在：仅补充空缺字段，不覆盖已有值。"""
        from app.models.poc import Vuln

        # 预置一条已有部分字段的 CVE
        existing = Vuln(
            cve_id="CVE-2021-44228",
            vendor="Apache Software Foundation",
            cvss=7.5,
            remediation={"workaround": "set log4j2.formatMsgNoLookups=true"},
        )
        db.add(existing)
        db.commit()

        result = self._import_content(client, auth_header, SAMPLE_NUCLEI_YAML_CVE_META)
        assert result["success"] == 1

        db.refresh(existing)
        # 已有值保持不变
        assert existing.cvss == 7.5
        assert existing.vendor == "Apache Software Foundation"
        assert existing.remediation["workaround"] == "set log4j2.formatMsgNoLookups=true"
        # 空缺字段被补充
        assert existing.cvss_metrics == "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
        assert existing.severity == "critical"
        assert existing.product == [{"vendor": "apache", "product": "log4j"}]
        # remediation.mitigation 被补入（workaround 保留）
        assert existing.remediation["mitigation"] == "Upgrade to Log4j 2.15.0 or later."

    def test_import_markdown_success(self, client: TestClient, auth_header: dict) -> None:
        """导入 Markdown 文档成功，front-matter 字段正确映射。"""
        result = self._import_content(client, auth_header, SAMPLE_MD)
        assert result["total"] == 1
        assert result["success"] == 1
        assert result["skipped"] == 0

        # 验证 POC 已入库且 format=markdown，severity/CVE 已从 front-matter 映射
        resp = client.get("/api/v1/pocs/search?q=test-markdown-doc", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] >= 1
        item = data["items"][0]
        assert item["format"] == "markdown"
        assert item["severity"] == "high"
        assert "CVE-2024-9999" in item["cve_ids"]

    def test_import_markdown_duplicate(self, client: TestClient, auth_header: dict) -> None:
        """重复导入相同 Markdown 内容自动跳过。"""
        self._import_content(client, auth_header, SAMPLE_MD)
        result2 = self._import_content(client, auth_header, SAMPLE_MD)
        assert result2["success"] == 0
        assert result2["skipped"] == 1


# ── 标签匹配测试 ────────────────────────────────────────────────────────


class TestImportTagMatching:
    """导入时标签自动匹配测试。"""

    SAMPLE_WITH_TAGS = """id: test-tag-matching

info:
  name: Test Tag Matching
  severity: medium
  author: tester
  tags: rce,oob,struts
  description: Test POC for tag matching

http:
  - method: GET
    path:
      - "{{BaseURL}}/test"
"""

    SAMPLE_WITH_NS_TAGS = """id: test-ns-tag-matching

info:
  name: Test NS Tag Matching
  severity: high
  author: tester
  tags: type:cve,technique:rce
  description: Test POC for namespace tag matching

http:
  - method: GET
    path:
      - "{{BaseURL}}/test"
"""

    def test_import_tags_match_existing_case_insensitive(
        self, client: TestClient, auth_header: dict, db: Session
    ) -> None:
        """导入时标签名不区分大小写匹配已有标签。"""
        # 预先创建标签 "RCE"（大写），namespace="technique"
        from app.models.poc import Tag

        tag = Tag(namespace="technique", name="RCE")
        db.add(tag)
        db.commit()

        # 使用 db 直接调用 _resolve_tag 测试标签匹配
        from app.services.import_service import _resolve_tag

        resolved = _resolve_tag(db, "rce")
        assert resolved.id == tag.id
        assert resolved.namespace == "technique"
        assert resolved.name == "RCE"

    def test_import_new_tag_default_namespace(
        self, client: TestClient, auth_header: dict, db: Session
    ) -> None:
        """导入时不存在标签自动创建，namespace 默认 general。"""
        from app.services.import_service import _resolve_tag

        resolved = _resolve_tag(db, "nonexistent-tag-xyz")
        assert resolved.namespace == "general"
        assert resolved.name == "nonexistent-tag-xyz"

    def test_import_tag_with_namespace_hint(self, client: TestClient, auth_header: dict, db: Session) -> None:
        """导入标签含 namespace:name 格式，解析后创建。"""
        from app.models.poc import Tag

        # 预先创建 namespace "type" 的标签
        existing = Tag(namespace="type", name="cve")
        db.add(existing)
        db.commit()

        from app.services.import_service import _resolve_tag

        # "type:CVE" → 大小写不敏感匹配到 namespace=type, name=cve
        resolved = _resolve_tag(db, "type:CVE")
        assert resolved.id == existing.id
        assert resolved.namespace == "type"
        assert resolved.name == "cve"

    def test_import_tag_new_namespace(self, client: TestClient, auth_header: dict, db: Session) -> None:
        """导入标签指定了不存在的 namespace，沿用输入 namespace。"""
        from app.services.import_service import _resolve_tag

        resolved = _resolve_tag(db, "custom-ns:my-tag")
        assert resolved.namespace == "custom-ns"
        assert resolved.name == "my-tag"

    def test_import_poc_tags_matched_via_full_flow(
        self, client: TestClient, auth_header: dict, db: Session
    ) -> None:
        """完整导入流程中标签自动匹配生效。"""
        from app.models.poc import Tag as TagModel

        # 预先创建两个标签（不同 namespace）
        db.add(TagModel(namespace="technique", name="rce"))
        db.add(TagModel(namespace="technique", name="oob"))
        db.flush()
        db.commit()

        # 导入含 rce/oob/struts 的 POC
        params = {"content": self.SAMPLE_WITH_TAGS, "source": "imported"}
        resp = client.post("/api/v1/import", params=params, headers=auth_header)
        assert resp.status_code == 200
        result = resp.json()["data"]
        assert result["success"] == 1

        # 验证标签：rce → technique:rce, oob → technique:oob, struts → general:struts
        resp = client.get("/api/v1/pocs/search?q=test-tag-matching", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] >= 1
        item = data["items"][0]
        tag_namespaces = {t["namespace"] for t in item["tags"]}
        tag_names = {t["name"] for t in item["tags"]}
        assert "technique" in tag_namespaces
        assert "general" in tag_namespaces
        assert "rce" in tag_names or "RCE" in tag_names
        assert "struts" in tag_names

    def test_import_poc_ns_tags(self, client: TestClient, auth_header: dict, db: Session) -> None:
        """导入 namespace:name 格式的标签。"""
        # 导入含 type:cve, technique:rce 的 POC
        params = {"content": self.SAMPLE_WITH_NS_TAGS, "source": "imported"}
        resp = client.post("/api/v1/import", params=params, headers=auth_header)
        assert resp.status_code == 200
        result = resp.json()["data"]
        assert result["success"] == 1

        # 验证标签已创建
        resp = client.get("/api/v1/pocs/search?q=test-ns-tag-matching", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] >= 1
        item = data["items"][0]
        tag_namespaces = {t["namespace"] for t in item["tags"]}
        assert "type" in tag_namespaces
        assert "technique" in tag_namespaces

    def test_tag_match_unifies_case_and_separators(
        self, client: TestClient, auth_header: dict, db: Session
    ) -> None:
        """标签匹配兼容大小写与 -/_ 差异，命中后复用我们自创建的标签。"""
        from app.models.poc import Tag
        from app.services.import_service import _resolve_tag

        # 自创建标签：混合大小写 + 连字符
        ours = Tag(namespace="technique", name="SQL-Injection")
        db.add(ours)
        db.commit()

        # 导入侧各种写法都应命中同一条
        for raw in ("sql_injection", "SQL_Injection", "sql-injection", "SQL-INJECTION"):
            resolved = _resolve_tag(db, raw)
            assert resolved.id == ours.id, f"未命中: {raw}"
            assert resolved.name == "SQL-Injection", f"名称被改写: {raw}"

    def test_tag_new_canonical_naming(self, client: TestClient, auth_header: dict, db: Session) -> None:
        """未命中的导入标签以规范命名（小写 + 连字符）创建。"""
        from app.services.import_service import _resolve_tag

        resolved = _resolve_tag(db, "SQL_Injection")
        assert resolved.namespace == "general"
        assert resolved.name == "sql-injection"  # 规范化：小写 + 下划线转连字符

    def test_tag_match_with_digits(self, client: TestClient, auth_header: dict, db: Session) -> None:
        """含数字的标签在大小写/分隔符变体下同样命中同一条自创建标签。"""
        from app.models.poc import Tag
        from app.services.import_service import _resolve_tag

        # 自创建标签含数字 + 连字符
        ours = Tag(namespace="general", name="CVE-2021-44228")
        db.add(ours)
        db.commit()

        # 导入侧各种写法（含下划线/大小写变体）都应命中同一条
        for raw in ("cve_2021_44228", "CVE_2021-44228", "cve-2021-44228", "CVE-2021-44228"):
            resolved = _resolve_tag(db, raw)
            assert resolved.id == ours.id, f"未命中: {raw}"
            assert resolved.name == "CVE-2021-44228", f"名称被改写: {raw}"

    def test_tag_match_alphanumeric_mixed(self, client: TestClient, auth_header: dict, db: Session) -> None:
        """字母+数字混合（如 Log4j2）的标签变体同样命中，且未命中时规范创建。"""
        from app.models.poc import Tag
        from app.services.import_service import _resolve_tag

        ours = Tag(namespace="technique", name="Log4j2-RCE")
        db.add(ours)
        db.commit()

        for raw in ("log4j2_rce", "LOG4J2_RCE", "log4j2-rce"):
            resolved = _resolve_tag(db, raw)
            assert resolved.id == ours.id, f"未命中: {raw}"

        # 未命中：纯数字开头的新标签规范创建（数字保留）
        new_tag = _resolve_tag(db, "2021_Log4Shell")
        assert new_tag.name == "2021-log4shell"


class TestExport:
    """POC 导出接口测试。"""

    def test_export_json(self, client: TestClient, auth_header: dict) -> None:
        """导出为 JSON 格式。"""
        # 先导入一个 POC

        # 通过 API 创建 POC
        create_data = {
            "name": "test-export-poc",
            "title": "Export Test",
            "severity": "info",
            "content": "id: test-export-poc\n\ninfo:\n  name: Export Test\n  severity: info\n",
            "author": "tester",
        }
        resp = client.post("/api/v1/pocs", json=create_data, headers=auth_header)
        assert resp.status_code == 200
        poc_id = resp.json()["data"]["id"]

        # 导出
        resp = client.get(f"/api/v1/export?ids={poc_id}&format=json", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["format"] == "json"
        assert data["count"] == 1
        exported = json.loads(data["content"])
        assert len(exported) == 1
        assert exported[0]["name"] == "test-export-poc"

    def test_export_nuclei(self, client: TestClient, auth_header: dict) -> None:
        """导出为 Nuclei YAML 格式。"""
        create_data = {
            "name": "test-export-nuclei",
            "title": "Export Nuclei",
            "severity": "high",
            "content": 'id: test-export-nuclei\n\ninfo:\n  name: Export Nuclei\n  severity: high\n\nhttp:\n  - method: GET\n    path:\n      - "{{BaseURL}}/test"\n',
        }
        resp = client.post("/api/v1/pocs", json=create_data, headers=auth_header)
        assert resp.status_code == 200
        poc_id = resp.json()["data"]["id"]

        resp = client.get(f"/api/v1/export?ids={poc_id}&format=nuclei", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["format"] == "nuclei"
        assert data["count"] == 1
        # 内容应包含原始的 YAML 模板
        assert "test-export-nuclei" in data["content"]

    def test_export_empty_ids(self, client: TestClient, auth_header: dict) -> None:
        """空 ID 列表导出返回空内容。"""
        resp = client.get("/api/v1/export?ids=&format=json", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["count"] == 0

    def test_export_no_auth(self, client: TestClient) -> None:
        """未认证导出返回 401。"""
        resp = client.get("/api/v1/export?ids=1&format=json")
        assert resp.status_code == 401
