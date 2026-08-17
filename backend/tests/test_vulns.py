"""CVE 漏洞库 API 集成测试。

测试覆盖：
- 删除单个 CVE 漏洞（含级联清理 POC 关联、审计日志留痕）
- 批量删除 CVE 漏洞（含去重、跳过不存在的 ID）
- 删除接口的权限控制（未认证 401 / viewer 403）
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.poc import AuditLog, PocVuln, Vuln


def _create_vuln(db: Session, cve_id: str) -> Vuln:
    """直接向会话写入一条 CVE 记录并提交。"""
    vuln = Vuln(cve_id=cve_id)
    db.add(vuln)
    db.commit()
    db.refresh(vuln)
    return vuln


def _resolve_admin_token(client: TestClient) -> str:
    """登录内置管理员，返回 access_token。"""
    resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200, f"login failed: {resp.text}"
    return resp.json()["data"]["access_token"]


def _create_viewer_headers(client: TestClient) -> dict[str, str]:
    """创建 viewer 用户并返回其认证请求头。"""
    admin_token = _resolve_admin_token(client)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    user_data = {"username": "vuln_viewer", "password": "password123", "role": "viewer"}
    resp = client.post("/api/v1/users", json=user_data, headers=admin_headers)
    assert resp.status_code == 200, f"create viewer failed: {resp.text}"
    viewer_token = client.post(
        "/api/v1/auth/login", json={"username": "vuln_viewer", "password": "password123"}
    ).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {viewer_token}"}


class TestVulnDelete:
    """单个 CVE 删除接口测试。"""

    def test_delete_vuln_success(self, client: TestClient, auth_header: dict, db: Session) -> None:
        """删除单个 CVE 成功，且不留孤儿关联记录。"""
        vuln = _create_vuln(db, "CVE-2024-1001")
        vuln_id = vuln.id

        resp = client.delete(f"/api/v1/vulns/{vuln_id}", headers=auth_header)
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] is True

        # 删除后详情不可查，列表总数归零
        resp = client.get(f"/api/v1/vulns/{vuln_id}", headers=auth_header)
        assert resp.status_code == 404
        resp = client.get("/api/v1/vulns", headers=auth_header)
        assert resp.json()["data"]["total"] == 0

    def test_delete_vuln_not_found(self, client: TestClient, auth_header: dict) -> None:
        """删除不存在的 CVE 返回 404。"""
        resp = client.delete("/api/v1/vulns/99999", headers=auth_header)
        assert resp.status_code == 404

    def test_delete_vuln_no_auth(self, client: TestClient, db: Session) -> None:
        """未认证删除返回 401。"""
        vuln = _create_vuln(db, "CVE-2024-1002")
        resp = client.delete(f"/api/v1/vulns/{vuln.id}")
        assert resp.status_code == 401

    def test_delete_vuln_viewer_forbidden(self, client: TestClient, db: Session) -> None:
        """viewer 角色删除返回 403。"""
        vuln = _create_vuln(db, "CVE-2024-1003")
        viewer_headers = _create_viewer_headers(client)
        resp = client.delete(f"/api/v1/vulns/{vuln.id}", headers=viewer_headers)
        assert resp.status_code == 403

    def test_delete_vuln_writes_audit_log(self, client: TestClient, auth_header: dict, db: Session) -> None:
        """删除时写入审计日志，日志内容包含 CVE 编号。"""
        vuln = _create_vuln(db, "CVE-2024-1004")

        resp = client.delete(f"/api/v1/vulns/{vuln.id}", headers=auth_header)
        assert resp.status_code == 200

        logs = db.query(AuditLog).filter(AuditLog.action == "vuln.deleted").all()
        assert len(logs) == 1
        assert logs[0].resource_type == "vuln"
        assert logs[0].resource_id == str(vuln.id)
        assert logs[0].detail == {"cve_id": "CVE-2024-1004", "severity": None}


class TestVulnCreate:
    """CVE 创建接口测试。"""

    def test_create_vuln_success(self, client: TestClient, auth_header: dict) -> None:
        """创建 CVE 成功，返回完整数据。"""
        payload = {
            "cve_id": "CVE-2024-5001",
            "vendor": "apache",
            "title": "Test RCE",
            "cvss": 9.8,
            "severity": "critical",
            "cvss_metrics": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
            "product": [{"vendor": "apache", "product": "log4j"}],
            "remediation": {"mitigation": "upgrade", "workaround": "set flag"},
            "reference": [{"url": "https://example.com", "label": "adv"}],
        }
        resp = client.post("/api/v1/vulns", json=payload, headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["cve_id"] == "CVE-2024-5001"
        assert data["vendor"] == "apache"
        assert data["cvss"] == 9.8
        assert data["poc_count"] == 0

    def test_create_vuln_duplicate_conflict(self, client: TestClient, auth_header: dict, db: Session) -> None:
        """cve_id 重复返回 409。"""
        _create_vuln(db, "CVE-2024-5002")
        resp = client.post("/api/v1/vulns", json={"cve_id": "CVE-2024-5002"}, headers=auth_header)
        assert resp.status_code == 409

    def test_create_vuln_invalid_cve_id(self, client: TestClient, auth_header: dict) -> None:
        """非法 cve_id 格式返回 422。"""
        resp = client.post("/api/v1/vulns", json={"cve_id": "not-a-cve"}, headers=auth_header)
        assert resp.status_code == 422

    def test_create_vuln_no_auth(self, client: TestClient) -> None:
        """未认证创建返回 401。"""
        resp = client.post("/api/v1/vulns", json={"cve_id": "CVE-2024-5003"})
        assert resp.status_code == 401

    def test_create_vuln_viewer_forbidden(self, client: TestClient) -> None:
        """viewer 角色创建返回 403。"""
        viewer_headers = _create_viewer_headers(client)
        resp = client.post("/api/v1/vulns", json={"cve_id": "CVE-2024-5004"}, headers=viewer_headers)
        assert resp.status_code == 403

    def test_create_vuln_writes_audit_log(self, client: TestClient, auth_header: dict, db: Session) -> None:
        """创建时写入审计日志。"""
        client.post("/api/v1/vulns", json={"cve_id": "CVE-2024-5005"}, headers=auth_header)
        logs = db.query(AuditLog).filter(AuditLog.action == "vuln.created").all()
        assert len(logs) == 1
        assert logs[0].detail["cve_id"] == "CVE-2024-5005"


class TestVulnUpdate:
    """CVE 更新接口测试。"""

    def test_update_vuln_success(self, client: TestClient, auth_header: dict, db: Session) -> None:
        """更新 CVE 字段成功，返回最新数据。"""
        vuln = _create_vuln(db, "CVE-2024-3001")
        payload = {
            "vendor": "apache",
            "title": "Log4j2 RCE",
            "description": "JNDI lookup RCE",
            "cvss": 9.8,
            "severity": "critical",
            "cvss_metrics": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
            "product": [{"vendor": "apache", "product": "log4j"}],
            "remediation": {"mitigation": "upgrade to 2.15.0", "workaround": "set formatMsgNoLookups=true"},
            "reference": [{"url": "https://nvd.nist.gov/vuln/detail/CVE-2024-3001", "label": "NVD"}],
        }

        resp = client.put(f"/api/v1/vulns/{vuln.id}", json=payload, headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["vendor"] == "apache"
        assert data["cvss"] == 9.8
        assert data["severity"] == "critical"
        assert data["cvss_metrics"].startswith("CVSS:3.1")
        assert data["product"][0]["vendor"] == "apache"
        assert data["product"][0]["product"] == "log4j"
        assert data["remediation"]["mitigation"] == "upgrade to 2.15.0"
        assert data["reference"][0]["url"].startswith("https://")
        # cve_id 不可改
        assert data["cve_id"] == "CVE-2024-3001"

    def test_update_vuln_clears_fields_with_none(
        self, client: TestClient, auth_header: dict, db: Session
    ) -> None:
        """传 None 清空字段。"""
        vuln = _create_vuln(db, "CVE-2024-3002")
        # 先填值
        client.put(
            f"/api/v1/vulns/{vuln.id}",
            json={"vendor": "apache", "cvss": 7.5},
            headers=auth_header,
        )
        # 再清空
        resp = client.put(
            f"/api/v1/vulns/{vuln.id}",
            json={"vendor": None, "cvss": None},
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["vendor"] is None
        assert data["cvss"] is None

    def test_update_vuln_not_found(self, client: TestClient, auth_header: dict) -> None:
        """更新不存在的 CVE 返回 404。"""
        resp = client.put("/api/v1/vulns/99999", json={"vendor": "x"}, headers=auth_header)
        assert resp.status_code == 404

    def test_update_vuln_no_auth(self, client: TestClient, db: Session) -> None:
        """未认证更新返回 401。"""
        vuln = _create_vuln(db, "CVE-2024-3003")
        resp = client.put(f"/api/v1/vulns/{vuln.id}", json={"vendor": "x"})
        assert resp.status_code == 401

    def test_update_vuln_viewer_forbidden(self, client: TestClient, db: Session) -> None:
        """viewer 角色更新返回 403。"""
        vuln = _create_vuln(db, "CVE-2024-3004")
        viewer_headers = _create_viewer_headers(client)
        resp = client.put(f"/api/v1/vulns/{vuln.id}", json={"vendor": "x"}, headers=viewer_headers)
        assert resp.status_code == 403

    def test_update_vuln_writes_audit_log(self, client: TestClient, auth_header: dict, db: Session) -> None:
        """更新时写入审计日志。"""
        vuln = _create_vuln(db, "CVE-2024-3005")
        client.put(f"/api/v1/vulns/{vuln.id}", json={"vendor": "apache"}, headers=auth_header)

        logs = db.query(AuditLog).filter(AuditLog.action == "vuln.updated").all()
        assert len(logs) == 1
        assert logs[0].resource_id == str(vuln.id)
        assert logs[0].detail["cve_id"] == "CVE-2024-3005"


class TestVulnExport:
    """CVE 导出接口测试。"""

    def test_export_json(self, client: TestClient, auth_header: dict, db: Session) -> None:
        """导出 JSON 含选中 CVE 完整字段。"""
        v1 = _create_vuln(db, "CVE-2024-6001")
        v2 = _create_vuln(db, "CVE-2024-6002")
        # 补充部分字段以便校验字段落地
        v1.vendor = "apache"
        v1.cvss = 9.8
        db.commit()

        resp = client.get(
            "/api/v1/vulns/export",
            params={"ids": f"{v1.id},{v2.id}", "format": "json"},
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["format"] == "json"
        assert data["count"] == 2
        import json as _json

        records = _json.loads(data["content"])
        assert len(records) == 2
        first = next(r for r in records if r["cve_id"] == "CVE-2024-6001")
        assert first["vendor"] == "apache"
        assert first["cvss"] == 9.8
        # 导出字段与导入模板对齐，不含 id/poc_count
        assert "id" not in first
        assert "poc_count" not in first

    def test_export_yaml(self, client: TestClient, auth_header: dict, db: Session) -> None:
        """导出 YAML 为列表文本。"""
        v = _create_vuln(db, "CVE-2024-6003")
        resp = client.get(
            "/api/v1/vulns/export",
            params={"ids": str(v.id), "format": "yaml"},
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["format"] == "yaml"
        assert "CVE-2024-6003" in data["content"]

    def test_export_empty_ids(self, client: TestClient, auth_header: dict) -> None:
        """空 ID 列表返回空内容。"""
        resp = client.get(
            "/api/v1/vulns/export",
            params={"ids": "", "format": "json"},
            headers=auth_header,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["count"] == 0
        assert resp.json()["data"]["content"] == ""

    def test_export_no_auth(self, client: TestClient, db: Session) -> None:
        """未认证导出返回 401。"""
        v = _create_vuln(db, "CVE-2024-6004")
        resp = client.get("/api/v1/vulns/export", params={"ids": str(v.id)})
        assert resp.status_code == 401


class TestVulnBatchDelete:
    """批量删除 CVE 接口测试。"""

    def _setup_vulns(self, db: Session, count: int = 3) -> list[int]:
        ids = []
        for i in range(count):
            vuln = _create_vuln(db, f"CVE-2024-2{i:03d}")
            ids.append(vuln.id)
        return ids

    def test_batch_delete_success(self, client: TestClient, auth_header: dict, db: Session) -> None:
        """批量删除选中 CVE 成功，返回实际删除数量。"""
        ids = self._setup_vulns(db, 3)

        resp = client.request("DELETE", "/api/v1/vulns", json={"ids": ids[:2]}, headers=auth_header)
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted_count"] == 2

        # 剩余 1 条，已删除的详情不可查
        resp = client.get("/api/v1/vulns", headers=auth_header)
        assert resp.json()["data"]["total"] == 1
        resp = client.get(f"/api/v1/vulns/{ids[0]}", headers=auth_header)
        assert resp.status_code == 404

    def test_batch_delete_skips_missing(self, client: TestClient, auth_header: dict, db: Session) -> None:
        """批量删除时，不存在的 ID 静默跳过，不影响其余删除。"""
        ids = self._setup_vulns(db, 2)

        resp = client.request(
            "DELETE", "/api/v1/vulns", json={"ids": [ids[0], ids[1], 99999]}, headers=auth_header
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted_count"] == 2

    def test_batch_delete_empty_ids(self, client: TestClient, auth_header: dict) -> None:
        """请求体为空 ID 列表返回 422。"""
        resp = client.request("DELETE", "/api/v1/vulns", json={"ids": []}, headers=auth_header)
        assert resp.status_code == 422

    def test_batch_delete_no_auth(self, client: TestClient, db: Session) -> None:
        """未认证批量删除返回 401。"""
        ids = self._setup_vulns(db, 1)
        resp = client.request("DELETE", "/api/v1/vulns", json={"ids": ids})
        assert resp.status_code == 401

    def test_batch_delete_viewer_forbidden(self, client: TestClient, db: Session) -> None:
        """viewer 角色批量删除返回 403。"""
        ids = self._setup_vulns(db, 1)
        viewer_headers = _create_viewer_headers(client)
        resp = client.request("DELETE", "/api/v1/vulns", json={"ids": ids}, headers=viewer_headers)
        assert resp.status_code == 403

    def test_batch_delete_cascades_poc_vuln(self, client: TestClient, auth_header: dict, db: Session) -> None:
        """批量删除后，POC 关联记录（poc_vuln）同步清理，POC 本身不受影响。"""
        vuln = _create_vuln(db, "CVE-2024-2500")

        poc_resp = client.post(
            "/api/v1/pocs",
            json={
                "name": "vuln-batch-cascade",
                "title": "Cascade Test",
                "severity": "high",
                "format": "nuclei",
                "content": "id: vuln-batch-cascade\n\ninfo:\n  name: Cascade Test\n  severity: high\n",
                "cve_ids": [vuln.cve_id],
            },
            headers=auth_header,
        )
        assert poc_resp.status_code == 200, f"create poc failed: {poc_resp.text}"
        poc_id = poc_resp.json()["data"]["id"]

        # 删除前存在关联记录
        assert db.query(PocVuln).filter(PocVuln.vuln_id == vuln.id).count() == 1

        resp = client.request("DELETE", "/api/v1/vulns", json={"ids": [vuln.id]}, headers=auth_header)
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted_count"] == 1

        # 关联记录已清理，POC 仍可查询
        assert db.query(PocVuln).filter(PocVuln.vuln_id == vuln.id).count() == 0
        assert db.query(Vuln).filter(Vuln.id == vuln.id).count() == 0
        resp = client.get(f"/api/v1/pocs/{poc_id}", headers=auth_header)
        assert resp.status_code == 200

    def test_batch_delete_writes_audit_logs(self, client: TestClient, auth_header: dict, db: Session) -> None:
        """批量删除为每个被删 CVE 写入一条审计日志。"""
        ids = self._setup_vulns(db, 3)

        resp = client.request("DELETE", "/api/v1/vulns", json={"ids": ids}, headers=auth_header)
        assert resp.status_code == 200

        logs = db.query(AuditLog).filter(AuditLog.action == "vuln.deleted").all()
        assert len(logs) == 3
        assert {int(log.resource_id) for log in logs} == set(ids)
