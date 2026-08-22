"""评论 Pydantic schema：请求校验、响应序列化、树形结构。"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ── 请求体 ─────────────────────────────────────────────────


class CommentCreate(BaseModel):
    """创建评论请求体。"""

    content: str = Field(..., min_length=1, max_length=10000, description="评论内容（纯文本）")
    parent_id: int | None = Field(default=None, description="父评论 ID，NULL 表示顶级评论")

    @field_validator("content")
    @classmethod
    def _check_content(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("评论内容不能为空")
        return stripped


class CommentUpdate(BaseModel):
    """编辑评论请求体。"""

    content: str = Field(..., min_length=1, max_length=10000, description="修改后的评论内容")

    @field_validator("content")
    @classmethod
    def _check_content(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("评论内容不能为空")
        return stripped


# ── 响应体 ─────────────────────────────────────────────────


class CommentResponse(BaseModel):
    """评论响应（含嵌套回复）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    poc_id: int
    user_id: int
    username: str = ""
    content: str
    parent_id: int | None = None
    edited: bool = False
    deleted: bool = False
    created_at: dt.datetime | None = None
    updated_at: dt.datetime | None = None
    replies: list[CommentResponse] = []


class CommentDeleteResponse(BaseModel):
    """删除评论响应。"""

    deleted: bool = True
    comment_id: int
