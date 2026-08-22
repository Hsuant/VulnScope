"""订阅 Pydantic schema：请求校验、响应序列化。"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SubscriptionCreate(BaseModel):
    """创建订阅请求体。"""

    sub_type: str = Field(
        ..., description="订阅类型: cve / vendor / tag",
        pattern=r"^(cve|vendor|tag)$",
    )
    target_id: str = Field(
        ..., max_length=128, description="目标标识: CVE编号 / 厂商slug / 标签ID"
    )
    notify_on_update: bool = Field(default=True, description="POC 更新时通知")
    notify_on_new: bool = Field(default=True, description="新 POC 导入时通知")


class SubscriptionUpdate(BaseModel):
    """更新订阅请求体（所有字段可选）。"""

    notify_on_update: bool | None = Field(default=None, description="POC 更新时通知")
    notify_on_new: bool | None = Field(default=None, description="新 POC 导入时通知")


class SubscriptionResponse(BaseModel):
    """订阅响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    sub_type: str
    target_id: str
    target_display: str | None = Field(
        default=None, description="对端名称（CVE标题/厂商名/标签名），由服务端填充"
    )
    notify_on_update: bool = True
    notify_on_new: bool = True
    created_at: dt.datetime | None = None

    @field_validator("sub_type")
    @classmethod
    def _check_sub_type(cls, v: str) -> str:
        if v not in {"cve", "vendor", "tag"}:
            raise ValueError(f"非法订阅类型: {v}")
        return v