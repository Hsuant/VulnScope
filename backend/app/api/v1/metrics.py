"""Prometheus 指标端点（``GET /metrics``）。

输出 Prometheus TEXT 格式（text/plain; version=0.0.4），供抓取器消费。
挂载于应用根路径（非 API 前缀之下），不要求认证——仅当抓取器部署在可信内网。
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.core.metrics import init_metrics, registry

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def metrics() -> PlainTextResponse:
    """渲染全部注册指标（进程基础指标在渲染时现算）。"""
    init_metrics()  # 幂等：确保指标装配后渲染
    return PlainTextResponse(registry.render(), media_type="text/plain; version=0.0.4")
