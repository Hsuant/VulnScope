"""导入导出 API 路由。

POST /api/v1/import — 上传文件/粘贴文本导入（multipart, 限 10MB）
GET  /api/v1/export — 导出 POC（JSON / nuclei-yaml）
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile

from app.api.deps import CurrentUser, DbSession, require_roles
from app.core.security import Role
from app.models.user import User
from app.schemas.common import ok
from app.services import import_service

router = APIRouter(tags=["import-export"])


@router.post("/import")
async def import_pocs(
    request: Request,
    db: DbSession,
    user: User = Depends(require_roles(Role.EDITOR, Role.ADMIN)),
    file: UploadFile | None = None,
    files: list[UploadFile] = File(default=[]),
    content: str | None = Query(default=None, description="POC 内容文本（粘贴模式）"),
    source: str = Query(default="imported", description="来源类型"),
    default_status: str = Query(default="draft", description="导入后默认状态"),
) -> dict:
    """导入 POC（支持单文件 / 批量文件上传 / 文本粘贴）。

    批量上传：多次以 `files` 字段提交文件，每个文件独立走导入管道，
    结果汇总为一份报告。单文件可继续用 `file` 字段（向后兼容）。
    单文件上传限制 10MB，支持格式：
    - nuclei-yaml（.yaml/.yml）
    - JSON（.json）
    - pocsuite3（.py）
    - raw-script（其他脚本）

    导入管道自动完成格式嗅探、解析、归一化、去重。
    返回导入结果报告（成功/跳过/失败数量及错误详情）。
    """
    from app.core.exceptions import AppError, ErrorCode
    from app.schemas.poc import PocImportResult

    MAX_SIZE = 10 * 1024 * 1024
    ip = request.client.host if request.client else None

    # 归一化为待处理文件列表
    upload_files: list[UploadFile] = []
    if files:
        upload_files.extend(files)
    if file:
        upload_files.append(file)

    # 批量文件模式：逐个文件导入并汇总结果
    if upload_files:
        merged = PocImportResult()
        for f in upload_files:
            file_content = await f.read()
            if len(file_content) > MAX_SIZE:
                merged.total += 1
                merged.failed.append(
                    {
                        "name": f.filename,
                        "error": "文件大小超过 10MB 限制",
                    }
                )
                merged.skipped += 1
                continue
            sub = import_service.import_pocs(
                db,
                raw_content=file_content,
                filename=f.filename,
                source=source,
                user_id=user.id,
                ip=ip,
                default_status=default_status,
            )
            merged.total += sub.total
            merged.success += sub.success
            merged.skipped += sub.skipped
            # 失败条目补充来源文件名，便于定位
            for item in sub.failed:
                if f.filename and "name" not in item:
                    item = {"name": f.filename, **item}
                merged.failed.append(item)
        return ok(merged.model_dump(), request)

    # 粘贴模式
    if content:
        result = import_service.import_pocs(
            db,
            raw_content=content,
            filename=None,
            source=source,
            user_id=user.id,
            ip=ip,
            default_status=default_status,
        )
        return ok(result.model_dump(), request)

    raise AppError(ErrorCode.REQUEST_INVALID, "请提供文件或粘贴内容")


@router.get("/export")
def export_pocs(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    ids: str = Query(..., description="POC ID 列表（逗号分隔）"),
    format: str = Query(default="json", description="导出格式: json / nuclei-yaml"),
) -> dict:
    """导出 POC。

    支持导出为 JSON 或 Nuclei YAML 格式。
    JSON 格式包含完整元数据；Nuclei 格式为纯模板文本（多个模板用 --- 分隔）。
    """
    poc_ids = [int(x.strip()) for x in ids.split(",") if x.strip()]
    if not poc_ids:
        return ok({"content": "", "format": format, "count": 0}, request)

    content = import_service.export_pocs(db, poc_ids, export_format=format)

    return ok(
        {
            "content": content,
            "format": format,
            "count": len(poc_ids),
        },
        request,
    )
