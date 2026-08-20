"""可观测性集成测试：健康检查深探、Prometheus 指标、request_id 贯穿。"""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestHealthDetail:
    """健康检查深探。"""

    def test_health_detail_structure(self, client: TestClient, auth_header: dict) -> None:
        """深探返回结构化组件列表。"""
        resp = client.get("/api/v1/health/detail", headers=auth_header)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == "OK"
        data = body["data"]
        assert data["status"] in ("ok", "degraded")
        assert "components" in data
        names = {c["component"] for c in data["components"]}
        assert "db" in names
        assert "cache" in names
        assert "plugins" in names
        assert "startup" in names

    def test_health_detail_db(self, client: TestClient, auth_header: dict) -> None:
        """数据库组件 up。"""
        resp = client.get("/api/v1/health/detail", headers=auth_header)
        data = resp.json()["data"]
        db = next(c for c in data["components"] if c["component"] == "db")
        assert db["status"] == "up"


class TestMetrics:
    """Prometheus 指标端点。"""

    def test_metrics_endpoint(self, client: TestClient) -> None:
        """/metrics 返回 Prometheus TEXT 格式，含必要指标。"""
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/plain")
        text = resp.text
        # 核心指标标识
        assert "vulnscope_http_requests_total" in text
        assert "vulnscope_http_request_duration_seconds" in text
        assert "vulnscope_http_requests_inflight" in text
        assert "vulnscope_process_uptime_seconds" in text
        assert "vulnscope_python_gc_count" in text
        # Prometheus 格式特征
        assert "# TYPE" in text
        assert "# EOF" in text

    def test_metrics_after_request(self, client: TestClient, auth_header: dict) -> None:
        """请求后指标计数器递增。"""
        # 先发一次请求使指标有值
        client.get("/api/v1/pocs", headers=auth_header)
        resp = client.get("/metrics")
        text = resp.text
        # inflight 应为 0（请求已结束）
        assert any(
            "vulnscope_http_requests_inflight" in line and ("0" in line.split()[-1])
            for line in text.split("\n")
            if line.startswith("vulnscope_http_requests_inflight")
        )
        # 应有状态码 200 的请求计数
        assert 'status="200"' in text


class TestRequestId:
    """request_id 贯穿。"""

    def test_response_header_present(self, client: TestClient, auth_header: dict) -> None:
        """响应头含 X-Request-ID。"""
        resp = client.get("/api/v1/health", headers=auth_header)
        request_id = resp.headers.get("X-Request-ID", "")
        assert request_id.startswith("vsh-"), f"expected vsh- prefix, got {request_id}"

    def test_response_body_matches_header(self, client: TestClient, auth_header: dict) -> None:
        """响应体 request_id 与响应头一致。"""
        resp = client.get("/api/v1/health", headers=auth_header)
        header_id = resp.headers.get("X-Request-ID", "")
        body_id = resp.json().get("request_id", "")
        assert header_id == body_id, f"header={header_id} body={body_id}"

    def test_client_provided_id_preserved(self, client: TestClient, auth_header: dict) -> None:
        """客户端传入的 X-Request-ID 被完整保留。"""
        custom_id = "my-custom-trace-id-123"
        resp = client.get("/api/v1/health", headers={"X-Request-ID": custom_id, **auth_header})
        assert resp.headers.get("X-Request-ID") == custom_id
        assert resp.json().get("request_id") == custom_id

    def test_consistent_on_error_response(self, client: TestClient, auth_header: dict) -> None:
        """错误响应也携带 request_id。"""
        resp = client.get("/api/v1/pocs/99999", headers=auth_header)
        assert resp.status_code == 404
        header_id = resp.headers.get("X-Request-ID", "")
        body_id = resp.json().get("request_id", "")
        assert header_id == body_id
        assert header_id != ""
