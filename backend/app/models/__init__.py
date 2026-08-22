"""ORM 模型聚合导出：import 即完成模型注册（init_db.create_all 依赖）。"""

from app.models.comment import PocComment
from app.models.notification import Notification
from app.models.subscription import Subscription
from app.models.poc import (
    AuditLog,
    Category,
    Component,
    Poc,
    PocAffected,
    PocAttachment,
    PocCategory,
    PocDeployment,
    PocSourceRecord,
    PocTag,
    PocVersion,
    PocVuln,
    Product,
    Tag,
    Vendor,
    Vuln,
)
from app.models.user import Role, User

__all__ = [
    "User",
    "Role",
    "Poc",
    "PocVersion",
    "Vuln",
    "PocVuln",
    "Tag",
    "PocTag",
    "Category",
    "PocCategory",
    "Vendor",
    "Product",
    "Component",
    "PocAffected",
    "PocDeployment",
    "PocSourceRecord",
    "PocAttachment",
    "AuditLog",
    "PocComment",
    "Notification",
    "Subscription",
]
