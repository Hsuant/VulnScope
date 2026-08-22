"""Subscription matching engine: given POC data, find matching subscription rules.

When a POC is created/updated, check its CVE, tags, and vendor info
against user subscriptions.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.poc import Poc, Product
from app.models.subscription import Subscription


class SubscriptionMatcher:
    """Subscription matching engine.

    Look up subscription rules by POC relations (CVE, tags, vendor)
    and return (subscription, match_reason) pairs.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def match_poc(self, poc: Poc) -> list[tuple[Subscription, str]]:
        """Run full subscription matching against the given POC.

        Returns:
            list[(Subscription, match_reason)]
        """
        matched: list[tuple[Subscription, str]] = []
        seen: set[tuple[int, str, str]] = set()

        # 1. Match by CVE
        for cve_id in self._get_poc_cve_ids(poc):
            subs = self._find_subscriptions("cve", cve_id)
            for sub in subs:
                key = (sub.user_id, sub.sub_type, sub.target_id)
                if key not in seen:
                    seen.add(key)
                    matched.append((sub, f"cve:{cve_id}"))

        # 2. Match by tag
        for tag_id in self._get_poc_tag_ids(poc):
            subs = self._find_subscriptions("tag", str(tag_id))
            for sub in subs:
                key = (sub.user_id, sub.sub_type, sub.target_id)
                if key not in seen:
                    seen.add(key)
                    matched.append((sub, f"tag:{tag_id}"))

        # 3. Match by vendor
        for vendor_slug in self._get_poc_vendor_slugs(poc):
            subs = self._find_subscriptions("vendor", vendor_slug)
            for sub in subs:
                key = (sub.user_id, sub.sub_type, sub.target_id)
                if key not in seen:
                    seen.add(key)
                    matched.append((sub, f"vendor:{vendor_slug}"))

        return matched

    def _get_poc_cve_ids(self, poc: Poc) -> list[str]:
        if not poc.vulns:
            self._db.refresh(poc, attribute_names=["vulns"])
        return [pv.vuln.cve_id for pv in poc.vulns if pv.vuln]

    def _get_poc_tag_ids(self, poc: Poc) -> list[int]:
        if not poc.tags:
            self._db.refresh(poc, attribute_names=["tags"])
        return [pt.tag.id for pt in poc.tags if pt.tag]

    def _get_poc_vendor_slugs(self, poc: Poc) -> list[str]:
        if not poc.affected:
            self._db.refresh(poc, attribute_names=["affected"])
        slugs: set[str] = set()
        for aff in poc.affected:
            if aff.product_id is None:
                continue
            product = self._db.get(Product, aff.product_id)
            if product and product.vendor:
                slugs.add(product.vendor.slug)
        return list(slugs)

    def _find_subscriptions(self, sub_type: str, target_id: str) -> list[Subscription]:
        stmt = select(Subscription).where(
            Subscription.sub_type == sub_type,
            Subscription.target_id == target_id,
        )
        return list(self._db.scalars(stmt).all())
