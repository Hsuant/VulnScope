"""评论 API 路由。

评论挂载于 /pocs/{poc_id}/comments 下（评论属于 POC 资源的子资源）。
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.deps import CurrentUser, DbSession
from app.schemas.comment import CommentCreate, CommentUpdate
from app.schemas.common import ok
from app.services.comment_service import CommentService

router = APIRouter(prefix="/pocs", tags=["comments"])


@router.get("/{poc_id}/comments")
def list_comments(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    poc_id: int,
) -> dict:
    """获取 POC 的所有评论（树形结构，顶级评论 + 嵌套回复）。"""
    service = CommentService(db, user.id)
    tree = service.list_for_poc(poc_id)
    items = [c.model_dump() for c in tree]
    return ok(items, request)


@router.post("/{poc_id}/comments")
def create_comment(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    poc_id: int,
    body: CommentCreate,
) -> dict:
    """发表评论或回复。

    支持回复已有评论（body.parent_id 指定父评论 ID）。
    最大嵌套深度 2 级，超过时自动挂到上一级。
    """
    service = CommentService(db, user.id)
    service.create(poc_id, body)
    # 重新加载完整的树形结构获取最新状态
    tree = service.list_for_poc(poc_id)
    return ok([c.model_dump() for c in tree], request)


@router.put("/comments/{comment_id}")
def update_comment(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    comment_id: int,
    body: CommentUpdate,
) -> dict:
    """编辑评论（仅作者本人，30 分钟内可编辑）。"""
    service = CommentService(db, user.id)
    comment = service.update(comment_id, body)
    # 获取所属 POC 的完整评论树
    tree = service.list_for_poc(comment.poc_id)
    return ok([c.model_dump() for c in tree], request)


@router.delete("/comments/{comment_id}")
def delete_comment(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    comment_id: int,
) -> dict:
    """删除评论（仅作者本人）。

    有子回复时软删除（保留占位），无子回复时硬删除。
    """
    service = CommentService(db, user.id)
    service.delete(comment_id)
    return ok({"deleted": True, "comment_id": comment_id}, request)
