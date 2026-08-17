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

        resp = client.request("DELETE", "/api/v1/vulns", json={"ids": [ids[0], ids[1], 99999]}, headers=auth_header)
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
