"""认证流程测试：登录、凭据校验、刷新、鉴权守卫。"""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestLogin:
    """登录接口（/auth/login）测试。"""

    def test_login_success(self, client: TestClient) -> None:
        """正常凭据返回 access + refresh token 与用户信息。"""
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == "OK"
        data = body["data"]
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "admin"
        assert data["user"]["role"] == "admin"

    def test_login_wrong_password(self, client: TestClient) -> None:
        """错误密码返回 401，不区分原因。"""
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrong"},
        )
        assert resp.status_code == 401
        assert resp.json()["code"] == "AUTH_INVALID_CREDENTIALS"

    def test_login_nonexistent(self, client: TestClient) -> None:
        """不存在的用户也返回 401，不暴露"用户不存在"。"""
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "nobody", "password": "any"},
        )
        assert resp.status_code == 401

    def test_login_empty_fields(self, client: TestClient) -> None:
        """空字段触发 Pydantic 校验，返回 422。"""
        resp = client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 422


class TestMe:
    """当前用户查询（/auth/me）测试。"""

    def test_me_authenticated(self, client: TestClient, auth_header: dict) -> None:
        """有效 token 返回用户信息。"""
        resp = client.get("/api/v1/auth/me", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["username"] == "admin"
        assert data["role"] == "admin"

    def test_me_no_token(self, client: TestClient) -> None:
        """无 token 返回 401。"""
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_me_invalid_token(self, client: TestClient) -> None:
        """伪造 token 返回 401。"""
        headers = {"Authorization": "Bearer fake-token"}
        resp = client.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 401

    def test_me_expired_token(self, client: TestClient) -> None:
        """过期 token 返回 401。"""
        import datetime as dt

        from app.core.security import create_token

        expired = create_token(1, "admin", "admin", "access", dt.timedelta(seconds=-1))
        headers = {"Authorization": f"Bearer {expired}"}
        resp = client.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 401
        assert resp.json()["code"] == "AUTH_TOKEN_EXPIRED"


class TestRefresh:
    """Token 刷新（/auth/refresh）测试。"""

    def test_refresh_success(self, client: TestClient) -> None:
        """有效 refresh token 获得新 token 对。"""
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        refresh_token = login.json()["data"]["refresh_token"]

        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_with_access_token(self, client: TestClient) -> None:
        """用 access token 刷新应被拒绝。"""
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        access_token = login.json()["data"]["access_token"]

        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
        assert resp.status_code == 401
        assert resp.json()["code"] == "AUTH_TOKEN_INVALID"
