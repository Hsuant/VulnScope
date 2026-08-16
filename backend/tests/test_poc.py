"""POC CRUD API 集成测试。

测试覆盖：
- 创建 POC（含重复检测、关联关系）
- 查询 POC 列表（含过滤、搜索、分页、排序）
- 获取 POC 详情
- 更新 POC（含内容变更版本快照、状态流转）
- 删除 POC
- 克隆 POC
- 版本历史
- 权限控制
"""

from __future__ import annotations

from fastapi.testclient import TestClient

# ── 测试数据 ────────────────────────────────────────────────────────────

SAMPLE_POC_CREATE = {
    "name": "test-poc-rce",
    "title": "Test POC RCE",
    "description": "A test POC for RCE vulnerability",
    "severity": "critical",
    "format": "nuclei",
    "content": 'id: test-poc-rce\n\ninfo:\n  name: Test POC RCE\n  severity: critical\n  author: tester\n\nhttp:\n  - method: GET\n    path:\n      - "{{BaseURL}}/test"\n',
    "author": "tester",
    "source": "manual",
    "status": "draft",
    "cve_ids": ["CVE-2024-0001"],
    "tag_ids": [],
    "category_ids": [],
}

SAMPLE_POC_UPDATE = {
    "title": "Updated POC Title",
    "severity": "high",
    "status": "active",
}

SAMPLE_POC_CONTENT_V2 = 'id: test-poc-rce\n\ninfo:\n  name: Test POC RCE v2\n  severity: critical\n  author: tester\n\nhttp:\n  - method: POST\n    path:\n      - "{{BaseURL}}/v2/test"\n'


class TestPocCreate:
    """POC 创建接口测试。"""

    def test_create_poc_success(self, client: TestClient, auth_header: dict) -> None:
        """正常创建 POC 返回 201 含完整数据。"""
        resp = client.post("/api/v1/pocs", json=SAMPLE_POC_CREATE, headers=auth_header)
        assert resp.status_code == 200, f"create failed: {resp.text}"
        body = resp.json()
        assert body["code"] == "OK"
        data = body["data"]
        assert data["name"] == "test-poc-rce"
        assert data["severity"] == "critical"
        assert data["status"] == "draft"
        assert data["format"] == "nuclei"
        assert data["source"] == "manual"
        assert data["version"] == 1
        assert len(data["uuid"]) == 36
        assert len(data["content_hash"]) == 64
        assert "CVE-2024-0001" in data["cve_ids"]

    def test_create_poc_duplicate_content(self, client: TestClient, auth_header: dict) -> None:
        """相同内容重复创建返回 409。"""
        resp = client.post("/api/v1/pocs", json=SAMPLE_POC_CREATE, headers=auth_header)
        assert resp.status_code == 200

        # 第二次创建相同内容（不同名称）应被拒绝
        dup = dict(SAMPLE_POC_CREATE, name="test-poc-rce-dup")
        resp = client.post("/api/v1/pocs", json=dup, headers=auth_header)
        assert resp.status_code == 409
        assert resp.json()["code"] == "POC_DUPLICATE"

    def test_create_poc_duplicate_name(self, client: TestClient, auth_header: dict) -> None:
        """相同 (name, source) 重复创建返回 409。"""
        resp = client.post("/api/v1/pocs", json=SAMPLE_POC_CREATE, headers=auth_header)
        assert resp.status_code == 200

        # 相同名称+来源
        resp = client.post("/api/v1/pocs", json=SAMPLE_POC_CREATE, headers=auth_header)
        assert resp.status_code == 409
        assert resp.json()["code"] == "POC_DUPLICATE"

    def test_create_poc_no_auth(self, client: TestClient) -> None:
        """未认证创建返回 401。"""
        resp = client.post("/api/v1/pocs", json=SAMPLE_POC_CREATE)
        assert resp.status_code == 401

    def test_create_poc_viewer_forbidden(self, client: TestClient, auth_header: dict) -> None:
        """viewer 角色创建返回 403。"""
        # 先创建一个 viewer 用户
        admin_login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        admin_token = admin_login.json()["data"]["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 创建 viewer 用户
        viewer_data = {"username": "viewer1", "password": "password123", "role": "viewer"}
        resp = client.post("/api/v1/users", json=viewer_data, headers=admin_headers)
        assert resp.status_code == 200

        # viewer 登录
        viewer_login = client.post(
            "/api/v1/auth/login", json={"username": "viewer1", "password": "password123"}
        )
        viewer_token = viewer_login.json()["data"]["access_token"]
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

        # viewer 创建 POC
        resp = client.post("/api/v1/pocs", json=SAMPLE_POC_CREATE, headers=viewer_headers)
        assert resp.status_code == 403

    def test_create_poc_with_tags(self, client: TestClient, auth_header: dict) -> None:
        """创建 POC 时关联标签。"""
        # 先创建标签（使用不冲突的名称）
        tag_data = {"namespace": "attack", "name": "test-poc-tag", "color": "#ff0000"}
        resp = client.post("/api/v1/tags", json=tag_data, headers=auth_header)
        assert resp.status_code == 200
        tag_id = resp.json()["data"]["id"]

        # 创建 POC 并关联标签
        poc_data = dict(SAMPLE_POC_CREATE, name="test-poc-tags", tag_ids=[tag_id])
        resp = client.post("/api/v1/pocs", json=poc_data, headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["tags"]) == 1
        assert data["tags"][0]["name"] == "test-poc-tag"


class TestPocList:
    """POC 列表查询接口测试。"""

    def _create_poc(self, client: TestClient, auth_header: dict, **kwargs) -> dict:
        """辅助：创建 POC 并返回 data。"""
        data = dict(SAMPLE_POC_CREATE, **kwargs)
        resp = client.post("/api/v1/pocs", json=data, headers=auth_header)
        assert resp.status_code == 200
        return resp.json()["data"]

    def test_list_pocs_empty(self, client: TestClient, auth_header: dict) -> None:
        """空列表返回正确分页。"""
        resp = client.get("/api/v1/pocs", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1

    def test_list_pocs_pagination(self, client: TestClient, auth_header: dict) -> None:
        """分页参数正常工作。"""
        for i in range(5):
            self._create_poc(
                client,
                auth_header,
                name=f"test-poc-{i}",
                content=f"id: test-poc-{i}\n\ninfo:\n  name: Test {i}\n  severity: info\n",
            )

        resp = client.get("/api/v1/pocs?page=1&page_size=2", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["total_pages"] == 3

    def test_list_pocs_filter_severity(self, client: TestClient, auth_header: dict) -> None:
        """按严重级别过滤。"""
        self._create_poc(
            client,
            auth_header,
            name="test-critical",
            severity="critical",
            content="id: test-critical\n\ninfo:\n  name: Critical\n  severity: critical\n",
        )
        self._create_poc(
            client,
            auth_header,
            name="test-info",
            severity="info",
            content="id: test-info\n\ninfo:\n  name: Info\n  severity: info\n",
        )

        resp = client.get("/api/v1/pocs?severity=critical", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 1
        assert data["items"][0]["severity"] == "critical"

    def test_list_pocs_search(self, client: TestClient, auth_header: dict) -> None:
        """关键字搜索。"""
        self._create_poc(
            client,
            auth_header,
            name="struts2-s2-045",
            title="Apache Struts2 RCE",
            content="id: struts2-s2-045\n\ninfo:\n  name: Struts2 RCE\n  severity: critical\n",
        )

        resp = client.get("/api/v1/pocs/search?q=struts2", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] >= 1

    def test_list_pocs_sort_by_severity(self, client: TestClient, auth_header: dict) -> None:
        """按严重级别排序。"""
        for sev in ["low", "critical", "medium", "high", "info"]:
            self._create_poc(
                client,
                auth_header,
                name=f"test-{sev}",
                severity=sev,
                content=f"id: test-{sev}\n\ninfo:\n  name: Test {sev}\n  severity: {sev}\n",
            )

        resp = client.get("/api/v1/pocs?sort_by=severity&sort_order=desc", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()["data"]
        severities = [item["severity"] for item in data["items"]]
        # 按权重降序：critical > high > medium > low > info
        assert severities[0] == "critical"


class TestPocDetail:
    """POC 详情接口测试。"""

    def test_get_poc_success(self, client: TestClient, auth_header: dict) -> None:
        """获取 POC 详情包含 content。"""
        resp = client.post("/api/v1/pocs", json=SAMPLE_POC_CREATE, headers=auth_header)
        poc_id = resp.json()["data"]["id"]

        resp = client.get(f"/api/v1/pocs/{poc_id}", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == poc_id
        assert data["content"] is not None
        assert "CVE-2024-0001" in data["cve_ids"]

    def test_get_poc_not_found(self, client: TestClient, auth_header: dict) -> None:
        """不存在的 POC 返回 404。"""
        resp = client.get("/api/v1/pocs/99999", headers=auth_header)
        assert resp.status_code == 404

    def test_get_poc_no_auth(self, client: TestClient) -> None:
        """未认证请求返回 401。"""
        resp = client.get("/api/v1/pocs/1")
        assert resp.status_code == 401


class TestPocUpdate:
    """POC 更新接口测试。"""

    def _create_poc(self, client: TestClient, auth_header: dict) -> dict:
        resp = client.post("/api/v1/pocs", json=SAMPLE_POC_CREATE, headers=auth_header)
        return resp.json()["data"]

    def test_update_poc_basic(self, client: TestClient, auth_header: dict) -> None:
        """更新 POC 基本字段。"""
        poc = self._create_poc(client, auth_header)
        resp = client.put(f"/api/v1/pocs/{poc['id']}", json=SAMPLE_POC_UPDATE, headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["title"] == "Updated POC Title"
        assert data["severity"] == "high"
        assert data["status"] == "active"

    def test_update_poc_content_creates_version(self, client: TestClient, auth_header: dict) -> None:
        """更新内容自动创建版本快照。"""
        poc = self._create_poc(client, auth_header)
        assert poc["version"] == 1

        # 更新内容
        update_data = {"content": SAMPLE_POC_CONTENT_V2}
        resp = client.put(f"/api/v1/pocs/{poc['id']}", json=update_data, headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["version"] >= 2

        # 检查版本历史
        resp = client.get(f"/api/v1/pocs/{poc['id']}/versions", headers=auth_header)
        assert resp.status_code == 200
        versions = resp.json()["data"]
        assert len(versions) >= 1

    def test_update_poc_invalid_status_transition(self, client: TestClient, auth_header: dict) -> None:
        """非法状态流转返回 409。"""
        poc = self._create_poc(client, auth_header)  # status = draft
        # draft → archived 不允许
        resp = client.put(f"/api/v1/pocs/{poc['id']}", json={"status": "archived"}, headers=auth_header)
        assert resp.status_code == 409

    def test_update_poc_partial(self, client: TestClient, auth_header: dict) -> None:
        """部分更新只修改传入字段。"""
        poc = self._create_poc(client, auth_header)
        resp = client.put(f"/api/v1/pocs/{poc['id']}", json={"author": "new-author"}, headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["author"] == "new-author"
        assert data["name"] == poc["name"]  # 未修改


class TestPocStatus:
    """POC 状态流转接口测试。"""

    def test_status_transition_draft_to_active(self, client: TestClient, auth_header: dict) -> None:
        """draft → active 合法。"""
        resp = client.post("/api/v1/pocs", json=SAMPLE_POC_CREATE, headers=auth_header)
        poc_id = resp.json()["data"]["id"]

        resp = client.patch(f"/api/v1/pocs/{poc_id}/status", json={"status": "active"}, headers=auth_header)
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "active"

    def test_status_transition_invalid(self, client: TestClient, auth_header: dict) -> None:
        """draft → archived 非法。"""
        resp = client.post("/api/v1/pocs", json=SAMPLE_POC_CREATE, headers=auth_header)
        poc_id = resp.json()["data"]["id"]

        resp = client.patch(f"/api/v1/pocs/{poc_id}/status", json={"status": "archived"}, headers=auth_header)
        assert resp.status_code == 409


class TestPocClone:
    """POC 克隆接口测试。"""

    def test_clone_poc_success(self, client: TestClient, auth_header: dict) -> None:
        """克隆 POC 成功创建独立副本。"""
        resp = client.post("/api/v1/pocs", json=SAMPLE_POC_CREATE, headers=auth_header)
        poc_id = resp.json()["data"]["id"]

        resp = client.post(f"/api/v1/pocs/{poc_id}/clone", json={"name": "cloned-poc"}, headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "cloned-poc"
        assert data["status"] == "draft"  # 克隆后恒为 draft
        assert data["severity"] == "critical"

    def test_clone_poc_duplicate_name(self, client: TestClient, auth_header: dict) -> None:
        """克隆时名称重复返回 409。"""
        resp = client.post("/api/v1/pocs", json=SAMPLE_POC_CREATE, headers=auth_header)
        poc_id = resp.json()["data"]["id"]

        # 用相同名称克隆
        resp = client.post(f"/api/v1/pocs/{poc_id}/clone", json={"name": "test-poc-rce"}, headers=auth_header)
        assert resp.status_code == 409


class TestPocDelete:
    """POC 删除接口测试。"""

    def test_delete_poc_success(self, client: TestClient, auth_header: dict) -> None:
        """删除 POC 成功。"""
        resp = client.post("/api/v1/pocs", json=SAMPLE_POC_CREATE, headers=auth_header)
        poc_id = resp.json()["data"]["id"]

        resp = client.delete(f"/api/v1/pocs/{poc_id}", headers=auth_header)
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] is True

        # 删除后查询返回 404
        resp = client.get(f"/api/v1/pocs/{poc_id}", headers=auth_header)
        assert resp.status_code == 404

    def test_delete_poc_not_found(self, client: TestClient, auth_header: dict) -> None:
        """删除不存在的 POC 返回 404。"""
        resp = client.delete("/api/v1/pocs/99999", headers=auth_header)
        assert resp.status_code == 404


class TestPocVersions:
    """POC 版本历史接口测试。"""

    def test_versions_empty(self, client: TestClient, auth_header: dict) -> None:
        """新 POC 有首条版本记录。"""
        resp = client.post("/api/v1/pocs", json=SAMPLE_POC_CREATE, headers=auth_header)
        poc_id = resp.json()["data"]["id"]

        resp = client.get(f"/api/v1/pocs/{poc_id}/versions", headers=auth_header)
        assert resp.status_code == 200
        versions = resp.json()["data"]
        assert len(versions) >= 1
        assert versions[0]["version_seq"] == 1


class TestPocSourceRecords:
    """POC 溯源记录接口测试。"""

    def test_source_records_empty(self, client: TestClient, auth_header: dict) -> None:
        """新 POC 溯源记录为空列表。"""
        resp = client.post("/api/v1/pocs", json=SAMPLE_POC_CREATE, headers=auth_header)
        poc_id = resp.json()["data"]["id"]

        resp = client.get(f"/api/v1/pocs/{poc_id}/source-records", headers=auth_header)
        assert resp.status_code == 200
        assert resp.json()["data"] == []
