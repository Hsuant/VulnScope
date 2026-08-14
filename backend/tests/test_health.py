"""健康检查 / 存活探测。"""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestHealth:
    def test_health_ok(self, client: TestClient) -> None:
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == "OK"
        assert body["data"]["status"] == "ok"
        assert body["data"]["db"] == "up"

    def test_health_structure(self, client: TestClient) -> None:
        """响应包含统一包装字段。"""
        resp = client.get("/api/v1/health")
        body = resp.json()
        assert "code" in body
        assert "message" in body
        assert "data" in body
        assert "request_id" in body
