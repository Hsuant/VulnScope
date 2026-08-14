"""标签管理相关 Pydantic schema。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TagCreate(BaseModel):
    """创建标签请求体。"""

    namespace: str = Field(default="general", max_length=32, description="命名空间")
    name: str = Field(..., min_length=1, max_length=64, description="标签名")
    color: str | None = Field(
        default=None, max_length=7, pattern=r"^#[0-9a-fA-F]{6}$", description="颜色十六进制"
    )
    description: str | None = Field(default=None, max_length=255, description="描述")


class TagUpdate(BaseModel):
    """更新标签请求体。"""

    namespace: str | None = Field(default=None, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=64)
    color: str | None = Field(default=None, max_length=7, pattern=r"^#[0-9a-fA-F]{6}$")
    description: str | None = None


class TagResponse(BaseModel):
    """标签响应体。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    namespace: str = "general"
    name: str
    color: str | None = None
    description: str | None = None
    poc_count: int = 0


class TagList(BaseModel):
    """标签列表（含分页）。"""

    items: list[TagResponse]
    total: int
