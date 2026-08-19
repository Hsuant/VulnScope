"""网络相关工具：客户端 IP 提取。

生产部署经 Nginx 反向代理时，request.client.host 取到的是代理地址，
需解析 X-Forwarded-For 链取最左侧真实客户端 IP。本工具统一该逻辑，
供限流、审计等场景复用，避免各处重复实现不一致。
"""

from __future__ import annotations

from fastapi import Request


def get_client_ip(request: Request, trusted_proxies: int = 1) -> str:
    """提取真实客户端 IP。

    解析优先级：X-Forwarded-For 链左起第 (trusted_proxies) 个地址 → X-Real-IP →
    request.client.host → 兜底 "unknown"。

    Args:
        request: FastAPI 请求对象。
        trusted_proxies: 前置可信代理跳数。XFF 链最左侧为原始客户端，
            每经一层代理追加一个地址；直连或单层反代取第 0 个即可。

    Returns:
        客户端 IP 字符串；无法判定时返回 "unknown"。
    """
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        parts = [ip.strip() for ip in xff.split(",") if ip.strip()]
        if parts:
            idx = min(trusted_proxies - 1, len(parts) - 1)
            return parts[idx]

    real_ip = request.headers.get("x-real-ip", "").strip()
    if real_ip:
        return real_ip

    return request.client.host if request.client else "unknown"
