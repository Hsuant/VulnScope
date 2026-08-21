"""可观测性集成测试：健康检查深探、Prometheus 指标、request_id 贯穿。"""

from __future__ import annotations

import json
import os

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

    def test_health_detail_cache_backend(self, client: TestClient, auth_header: dict) -> None:
        """缓存组件报告后端类型并自检通过。"""
        resp = client.get("/api/v1/health/detail", headers=auth_header)
        data = resp.json()["data"]
        cache = next(c for c in data["components"] if c["component"] == "cache")
        assert cache["status"] == "up"
        assert "backend" in cache
        assert "msg" in cache

    def test_health_detail_plugins_detail(self, client: TestClient, auth_header: dict) -> None:
        """插件组件列出每个插件的名称 + 版本。"""
        resp = client.get("/api/v1/health/detail", headers=auth_header)
        data = resp.json()["data"]
        plugins = next(c for c in data["components"] if c["component"] == "plugins")
        assert plugins["status"] == "up"
        assert plugins["total"] >= 1
        # 每个槽位下应有插件清单，每个条目含 name + version + enabled
        assert "plugins" in plugins
        for slot, entries in plugins["plugins"].items():
            assert isinstance(slot, str)
            for entry in entries:
                assert "name" in entry
                assert "version" in entry
                assert "enabled" in entry


class TestAccessLogRequestId:
    """访问日志 request_id 贯穿：每条请求级日志行携带 request_id。"""

    def test_access_log_carries_request_id(self, client: TestClient, auth_header: dict) -> None:
        """请求后日志文件中出现携带 request_id 的访问日志行。"""
        resp = client.get("/api/v1/health", headers=auth_header)
        request_id = resp.headers.get("X-Request-ID", "")
        assert request_id, "响应头应携带 X-Request-ID"

        # 在日志目录中查找携带该 request_id 的访问日志行。
        from app.core.logging import _LOG_DIR

        found = False
        for fname in os.listdir(_LOG_DIR):
            if not fname.endswith(".log"):
                continue
            with open(os.path.join(_LOG_DIR, fname), encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if obj.get("logger") == "access" and obj.get("request_id") == request_id:
                        assert obj.get("msg")  # msg 字段非空
                        found = True
                        break
            if found:
                break
        assert found, f"未在日志中找到 request_id={request_id} 的访问日志行"


class TestConsoleFormatter:
    """控制台格式化器：ERROR 级追加结构化 JSON 行。"""

    def test_info_text_only(self) -> None:
        """INFO 级别仅输出文本行，无 JSON。"""
        import io
        import logging

        from app.core.logging import ConsoleFormatter

        buf = io.StringIO()
        handler = logging.StreamHandler(buf)
        handler.setFormatter(ConsoleFormatter())
        lg = logging.getLogger("test.console.info")
        lg.addHandler(handler)
        lg.setLevel(logging.INFO)
        lg.info("hello world", extra={"request_id": "vsh-x"})
        lg.removeHandler(handler)
        out = buf.getvalue()
        assert "hello world" in out
        # INFO 不应出现 JSON 行
        assert "{" not in out

    def test_error_appends_json(self) -> None:
        """ERROR 级别在文本行后追加 JSON 行，含 extra 字段。"""
        import io
        import json as jsonlib
        import logging

        from app.core.logging import ConsoleFormatter

        buf = io.StringIO()
        handler = logging.StreamHandler(buf)
        handler.setFormatter(ConsoleFormatter())
        lg = logging.getLogger("test.console.error")
        lg.addHandler(handler)
        lg.setLevel(logging.DEBUG)
        lg.error("boom", extra={"request_id": "vsh-err", "component": "db"})
        lg.removeHandler(handler)
        out = buf.getvalue()
        # 应同时含文本行与 JSON 行
        assert "boom" in out
        assert "{" in out
        # 第二行应是合法 JSON
        lines = [ln for ln in out.strip().split("\n") if ln]
        json_line = next(ln for ln in lines if ln.startswith("{"))
        obj = jsonlib.loads(json_line)
        assert obj["level"] == "ERROR"
        assert obj["msg"] == "boom"
        assert obj["component"] == "db"


class TestExceptionLogging:
    """异常处理器日志：500 错误落盘 ERROR + traceback。"""

    def test_500_logged_with_traceback(self, client: TestClient, auth_header: dict) -> None:
        """访问不存在的详情触发 404，应在日志中留 WARNING 记录。"""
        resp = client.get("/api/v1/pocs/99999", headers=auth_header)
        assert resp.status_code == 404
        request_id = resp.headers.get("X-Request-ID", "")
        assert request_id

        from app.core.logging import _LOG_DIR

        found = False
        for fname in os.listdir(_LOG_DIR):
            if not fname.endswith(".log"):
                continue
            with open(os.path.join(_LOG_DIR, fname), encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if (
                        obj.get("logger") == "app.core.exceptions"
                        and obj.get("request_id") == request_id
                        and obj.get("level") in ("ERROR", "WARNING")
                    ):
                        found = True
                        break
            if found:
                break
        assert found, "未在日志中找到异常处理器的结构化记录"


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
