"""?? Pydantic schema????????????"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field


class NotificationResponse(BaseModel):
    """??????"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    notification_type: str
    title: str
    content: str
    sub_type: str
    sub_target: str
    ref_type: str
    ref_id: int
    is_read: bool
    read_at: dt.datetime | None = None
    created_at: dt.datetime | None = None


class NotificationListResponse(BaseModel):
    """????????????"""

    items: list[NotificationResponse]
    total: int
    unread_count: int
    page: int
    page_size: int
