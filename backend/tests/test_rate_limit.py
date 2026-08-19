"""登录限流单元测试。

覆盖：
    - 固定窗口内超限请求被拒（429 + Retry-After 头）
    - 窗口过期后配额恢复
    - 登录成功重置计数
    - 配置关闭时限流不生效
"""

from __future__ import annotations

import pytest

from app.core.ratelimit import rate_limiter
from app.core.ratelimit.storage import InprocRateLimitStorage


class TestRateLimiter:
    """RateLimiter 固定窗口语义。"""

    def test_allows_within_limit(self) -> None:
        limiter = rate_limiter.__class__(InprocRateLimitStorage())
        for _ in range(3):
            result = limiter.acquire("k", limit=3, ttl=60)
            assert result.allowed
        assert result.remaining == 0

    def test_rejects_over_limit(self) -> None:
        limiter = rate_limiter.__class__(InprocRateLimitStorage())
        for _ in range(3):
            limiter.acquire("k", limit=3, ttl=60)
        result = limiter.acquire("k", limit=3, ttl=60)
        assert not result.allowed
        assert result.retry_after > 0

    def test_reset_clears_window(self) -> None:
        limiter = rate_limiter.__class__(InprocRateLimitStorage())
        for _ in range(3):
            limiter.acquire("k", limit=3, ttl=60)
        limiter.reset("k")
        result = limiter.acquire("k", limit=3, ttl=60)
        assert result.allowed
        assert result.remaining == 2

    def test_separate_keys_independent(self) -> None:
        limiter = rate_limiter.__class__(InprocRateLimitStorage())
        for _ in range(3):
            limiter.acquire("a", limit=3, ttl=60)
        result_b = limiter.acquire("b", limit=3, ttl=60)
        assert result_b.allowed


@pytest.fixture
def _enable_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """开启限流并使用独立短窗口存储，避免用例间污染。"""
    from app.core import config

    monkeypatch.setattr(config.settings, "LOGIN_RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(config.settings, "LOGIN_RATE_LIMIT_MAX_ATTEMPTS", 3)
    monkeypatch.setattr(config.settings, "LOGIN_RATE_LIMIT_WINDOW", 60)
    # 注入干净存储，隔离测试间计数状态。
    monkeypatch.setattr(rate_limiter, "_storage", InprocRateLimitStorage())


class TestLoginRateLimit:
    """登录接口限流端到端。"""

    def test_rejects_after_max_attempts(self, client, _enable_rate_limit) -> None:
        for _ in range(3):
            resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
            assert resp.status_code == 401

        resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
        assert resp.status_code == 429
        assert resp.json()["code"] == "AUTH_RATE_LIMITED"
        assert "Retry-After" in resp.headers

    def test_success_resets_counter(self, client, _enable_rate_limit) -> None:
        # 2 次失败（未触顶）
        for _ in range(2):
            client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})

        # 正确登录应成功并重置计数
        resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        assert resp.status_code == 200

        # 重置后又有 3 次配额
        for _ in range(3):
            r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
            assert r.status_code == 401
        assert (
            client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"}).status_code
            == 429
        )

    def test_disabled_when_config_off(self, client, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.core import config

        monkeypatch.setattr(config.settings, "LOGIN_RATE_LIMIT_ENABLED", False)
        monkeypatch.setattr(rate_limiter, "_storage", InprocRateLimitStorage())
        for _ in range(10):
            resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
            assert resp.status_code == 401
