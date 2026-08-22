"""Subscription event consumers: listen to poc.created / poc.updated,
run matching, and create notification records.

These handlers are registered on EventBus, invoked asynchronously by
event_bus.publish. Each handler uses its own DB session; exceptions
are only logged and do not block the main flow.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.events import DomainEvent, EventTypes, event_bus
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.notification import Notification
from app.models.poc import Poc
from app.services.poc_service import _load_poc_relations
from app.services.subscription_matcher import SubscriptionMatcher

logger = get_logger(__name__)


def _load_poc(db: Session, poc_id: int) -> Poc | None:
    stmt = _load_poc_relations(select(Poc).where(Poc.id == poc_id))
    return db.scalar(stmt)


def _action_label(event_type: str) -> str:
    labels = {
        "poc.created": "imported",
        "poc.updated": "updated",
        "poc.version_created": "content updated",
        "poc.status_changed": "status changed",
    }
    return labels.get(event_type, "changed")


def _build_title(sub_type: str, target_id: str, event_type: str) -> str:
    action = "new" if event_type == "poc.created" else "updated"
    type_label = {"cve": "CVE", "vendor": "Vendor", "tag": "Tag"}.get(sub_type, sub_type)
    return f"[{type_label}] {target_id} has {action} POC"


def _handle_poc_event(event: DomainEvent, event_type: str) -> None:
    """Generic POC event handler: match subscriptions, create notifications."""
    poc_id_str = event.aggregate_id
    if not poc_id_str:
        logger.warning("subscription handler: missing aggregate_id in event %s", event.type)
        return

    try:
        poc_id = int(poc_id_str)
    except (ValueError, TypeError):
        logger.warning("subscription handler: invalid aggregate_id %s", poc_id_str)
        return

    db = SessionLocal()
    try:
        poc = _load_poc(db, poc_id)
        if poc is None:
            logger.warning("subscription handler: poc %d not found", poc_id)
            return

        matcher = SubscriptionMatcher(db)
        matches = matcher.match_poc(poc)

        if not matches:
            return

        created_count = 0
        for sub, _match_reason in matches:
            if event_type == "poc.created" and not sub.notify_on_new:
                continue
            if (
                event_type in ("poc.updated", "poc.version_created", "poc.status_changed")
                and not sub.notify_on_update
            ):
                continue

            title = _build_title(sub.sub_type, sub.target_id, event_type)
            content = f"POC '{poc.name}' {_action_label(event_type)}"

            notif = Notification(
                user_id=sub.user_id,
                notification_type=event_type,
                title=title,
                content=content,
                sub_type=sub.sub_type,
                sub_target=sub.target_id,
                ref_type="poc",
                ref_id=poc.id,
                is_read=False,
                read_at=None,
            )
            db.add(notif)
            created_count += 1

        db.commit()
        if created_count:
            logger.info("subscription handler: poc %d created %d notifications", poc_id, created_count)
    except Exception:
        logger.exception("subscription handler failed for poc %s", poc_id_str)
        db.rollback()
    finally:
        db.close()


def handle_poc_created(event: DomainEvent) -> None:
    _handle_poc_event(event, "poc.created")


def handle_poc_updated(event: DomainEvent) -> None:
    _handle_poc_event(event, "poc.updated")


def register_subscription_handlers() -> None:
    """Register subscription event handlers on EventBus. Call once at startup."""
    event_bus.subscribe(EventTypes.POC_CREATED.value, handle_poc_created)
    event_bus.subscribe(EventTypes.POC_UPDATED.value, handle_poc_updated)
    event_bus.subscribe(EventTypes.POC_VERSION_CREATED.value, handle_poc_updated)
    event_bus.subscribe(EventTypes.POC_STATUS_CHANGED.value, handle_poc_updated)
    logger.info("registered subscription event handlers for 4 event types")
