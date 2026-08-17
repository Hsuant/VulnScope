"""CVE 批量导入管道与接口测试。

覆盖：
- 格式判定（json / jsonl / yaml / markdown）
- 解析与字段归一化（键名变体、类型转换）
- 导入 upsert（新建 / 补缺 / 跳过 / 失败汇总）
- 接口权限与超限
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.poc import AuditLog, Vuln
from app.services import vuln_import_service
from app.services.vuln_parser import detect_format, parse


def _auth(client: TestClient) -> dict[str, str]:
    token = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"}).json()[
        "data"
    ]["access_token"]
    return {"Authorization": f"Bearer {token}"}


JSON_ARRAY = json.dumps(
    [
        {
            "cve_id": "CVE-2021-44228",
            "vendor": "apache",
            "title": "Log4j2 JNDI RCE",
            "cvss": 9.8,
            "severity": "critical",
            "cvss_metrics": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
            "product": [{"vendor": "apache", "product": "log4j"}],
            "remediation": {"mitigation": "升级到 2.15.0"},
            "reference": [{"url": "https://nvd.nist.gov/vuln/detail/CVE-2021-44228", "label": "NVD"}],
        },
        {"cve_id": "CVE-2021-45046", "vendor": "apache", "cvss": 9.0, "severity": "critical"},
    ]
)

JSONL = "\n".join(
    [
        json.dumps({"cve_id": "CVE-2021-44228", "vendor": "apache", "cvss": 9.8}),
        json.dumps({"cve_id": "CVE-2021-45046", "severity": "high"}),
        "",
        json.dumps({"cve_id": "CVE-2022-22222", "title": "Demo"}),
    ]
)

YAML = """- cve_id: CVE-2021-44228
  vendor: apache
  cvss: 9.8
  severity: critical
- cve_id: CVE-2022-99999
  vendor: nginx
  title: Demo
"""

MARKDOWN = """---
cve_id: CVE-2021-44228
vendor: apache
severity: critical
---

# 漏洞概述

正文描述内容。
"""


class TestVulnParser:
    """格式判定与解析。"""

    def test_detect_by_extension(self) -> None:
        assert detect_format("x", "a.json") == "json"
        assert detect_format("x", "a.jsonl") == "jsonl"
        assert detect_format("x", "a.yaml") == "yaml"
        assert detect_format("x", "a.md") == "markdown"

    def test_detect_json_content(self) -> None:
        assert detect_format('[{"cve_id":"CVE-2021-44228"}]') == "json"
        assert detect_format('{"cve_id":"CVE-2021-44228"}') == "json"

    def test_detect_jsonl_content(self) -> None:
        text = '{"cve_id":"CVE-2021-44228"}\n{"cve_id":"CVE-2021-45046"}'
        assert detect_format(text) == "jsonl"

    def test_detect_markdown_frontmatter(self) -> None:
        assert detect_format("---\ncve_id: CVE-2021-44228\n---\nbody") == "markdown"

    def test_parse_json_key_aliases(self) -> None:
        from app.services.vuln_parser import from_dict

        items = parse('{"cve":"CVE-2021-44228","cvss_score":"9.8","cvss-metrics":"CVSS:3.1/AV:N"}', "json")
        assert len(items) == 1
        r = from_dict(items[0])
        assert r.cve_id == "CVE-2021-44228"
        assert r.cvss == 9.8
        assert r.cvss_metrics == "CVSS:3.1/AV:N"

    def test_parse_jsonl_skips_blank_lines(self) -> None:
        items = parse(JSONL, "jsonl")
        assert len(items) == 3

    def test_parse_yaml_list(self) -> None:
        items = parse(YAML, "yaml")
        assert len(items) == 2
        assert items[0]["cve_id"] == "CVE-2021-44228"
        assert items[1]["vendor"] == "nginx"

    def test_parse_markdown_frontmatter_and_body(self) -> None:
        from app.services.vuln_parser import from_dict

        items = parse(MARKDOWN, "markdown")
        assert len(items) == 1
        r = from_dict(items[0])
        assert r.cve_id == "CVE-2021-44228"
        assert r.vendor == "apache"
        assert "正文描述内容" in (r.description or "")

    def test_from_dict_invalid_cve_id_raises(self) -> None:
        from app.services.vuln_parser import from_dict

        try:
            from_dict({"cve_id": "not-a-cve"})
            pytest.fail("应抛错")
        except ValueError:
            pass


class TestVulnImportService:
    """导入 upsert 行为。"""

    def test_import_creates_new(self, db: Session) -> None:
        result = vuln_import_service.import_vulns(db, JSON_ARRAY)
        assert result.total == 2
        assert result.created == 2
        assert result.updated == 0
        assert result.skipped == 0
        assert result.success == 2
        assert db.query(Vuln).filter(Vuln.cve_id == "CVE-2021-44228").count() == 1

    def test_import_fill_missing_only(self, db: Session) -> None:
        vuln_import_service.import_vulns(db, JSONL)
        # 第二次导入：已存在 → 仅补缺，不覆盖
        result2 = vuln_import_service.import_vulns(
            db,
            json.dumps(
                {"cve_id": "CVE-2021-44228", "vendor": "Apache Software Foundation", "title": "New Title"}
            ),
        )
        assert result2.updated == 1
        existing = db.query(Vuln).filter(Vuln.cve_id == "CVE-2021-44228").one()
        # vendor 已有值，不被覆盖
        assert existing.vendor == "apache"
        # title 空缺，被补充
        assert existing.title == "New Title"

    def test_import_skipped_when_nothing_to_fill(self, db: Session) -> None:
        vuln_import_service.import_vulns(db, JSON_ARRAY)
        result2 = vuln_import_service.import_vulns(db, JSON_ARRAY)
        assert result2.skipped == 2
        assert result2.created == 0
        assert result2.updated == 0

    def test_import_partial_failure(self, db: Session) -> None:
        bad = json.dumps(
            [
                {"cve_id": "CVE-2021-44228", "vendor": "apache"},
                {"cve_id": "not-a-cve"},
                {"cve_id": "CVE-2022-33333", "vendor": "nginx"},
            ]
        )
        result = vuln_import_service.import_vulns(db, bad)
        assert result.created == 2
        assert len(result.failed) == 1
        assert "非法" in result.failed[0]["error"]

    def test_import_writes_audit_logs(self, db: Session) -> None:
        vuln_import_service.import_vulns(db, JSON_ARRAY, user_id=1)
        created_logs = db.query(AuditLog).filter(AuditLog.action == "vuln.created").count()
        batch_logs = db.query(AuditLog).filter(AuditLog.action == "vuln.batch_imported").count()
        assert created_logs == 2
        assert batch_logs == 1


class TestVulnImportApi:
    """导入接口。"""

    def test_import_paste_success(self, client: TestClient, auth_header: dict) -> None:
        resp = client.post(
            "/api/v1/vulns/import",
            params={"content": JSON_ARRAY},
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 2
        assert data["created"] == 2

    def test_import_no_auth(self, client: TestClient) -> None:
        resp = client.post("/api/v1/vulns/import", params={"content": JSON_ARRAY})
        assert resp.status_code == 401

    def test_import_viewer_forbidden(self, client: TestClient) -> None:
        admin = _auth(client)
        client.post(
            "/api/v1/users",
            json={"username": "vimp", "password": "password123", "role": "viewer"},
            headers=admin,
        )
        token = client.post(
            "/api/v1/auth/login", json={"username": "vimp", "password": "password123"}
        ).json()["data"]["access_token"]
        resp = client.post(
            "/api/v1/vulns/import",
            params={"content": JSON_ARRAY},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_import_empty_payload(self, client: TestClient, auth_header: dict) -> None:
        resp = client.post("/api/v1/vulns/import", headers=auth_header)
        assert resp.status_code == 422
