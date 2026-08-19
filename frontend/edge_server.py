"""VulnScope 前端边缘服务。

职责：
    - 托管 SPA 静态产物（vite 构建的 dist），history 模式 fallback 到 index.html；
    - 反向代理 /api/* 到后端容器，透传方法/头/体。

设计约束：仅基于自建 vulnscope 镜像（Python + httpx + Starlette），不引入
nginx/node 镜像，满足"全栈均使用 vulnscope 镜像"的部署要求。
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, Response
from starlette.routing import Route

_DIST = Path(os.environ.get("DIST_DIR", "/app/dist"))
_BACKEND = os.environ.get("BACKEND_URL", "http://backend:8000")

# 逐跳头与由 ASGI/代理重新计算的头，转发时需剔除，避免污染下游/上游。
_HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
    "content-encoding",
}

# 复用连接的异步客户端；管理后台流量有限，单客户端足够。
_client = httpx.AsyncClient(base_url=_BACKEND, timeout=60.0, follow_redirects=False)


async def _api_proxy(request: Request) -> Response:
    """反向代理 /api/* 到后端，透传方法、头、查询串与请求体。"""
    path = request.url.path
    if request.url.query:
        path = f"{path}?{request.url.query}"
    headers = [(k, v) for k, v in request.headers.items() if k.lower() not in _HOP_BY_HOP]
    upstream = _client.build_request(
        request.method, path, headers=headers, content=await request.body()
    )
    resp = await _client.send(upstream, stream=True)
    body = await resp.aread()
    await resp.aclose()
    # Response 基类要求 headers 为 Mapping，转为 dict；逐跳头已剔除。
    out_headers = {
        k: v for k, v in resp.headers.multi_items() if k.lower() not in _HOP_BY_HOP
    }
    return Response(body, status_code=resp.status_code, headers=out_headers)


def _serve_static(rel_path: str) -> Response:
    """返回静态文件；不存在则回退 index.html（SPA history 模式）。"""
    candidate = _DIST / rel_path
    if candidate.is_file():
        return FileResponse(candidate)
    # 目录型请求尝试其下 index.html
    index = candidate / "index.html"
    if index.is_file():
        return FileResponse(index)
    return FileResponse(_DIST / "index.html")


async def _spa(request: Request) -> Response:
    return _serve_static(request.path_params.get("path", ""))


async def _spa_root(request: Request) -> Response:  # noqa: ARG001
    return FileResponse(_DIST / "index.html")


# 路由顺序：/api 优先于 SPA 兜底，避免接口请求被静态层吞掉。
routes = [
    Route(
        "/api/{path:path}",
        _api_proxy,
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    ),
    Route("/", _spa_root, methods=["GET"]),
    Route("/{path:path}", _spa, methods=["GET", "HEAD"]),
]

app = Starlette(routes=routes)
