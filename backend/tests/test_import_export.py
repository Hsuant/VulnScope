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


class TestFormatDetector:
    """格式嗅探器测试。"""

    def test_detect_nuclei_yaml(self) -> None:
        from app.services.import_service import FormatDetector

        assert FormatDetector.detect(SAMPLE_NUCLEI_YAML) == "nuclei-yaml"

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
        assert FormatDetector.detect("some content", "test.yaml") == "nuclei-yaml"
        # JSON by extension
        assert FormatDetector.detect("some content", "test.json") == "json"

    def test_detect_fallback(self) -> None:
        from app.services.import_service import FormatDetector

        # 未知格式降级为 raw-script
        # 使用包含 YAML 允许但非模板的内容触发 fallback
        assert FormatDetector.detect("\x00\x00\x00\x00binary data") == "raw-script"


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

        resp = client.get(f"/api/v1/export?ids={poc_id}&format=nuclei-yaml", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["format"] == "nuclei-yaml"
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
