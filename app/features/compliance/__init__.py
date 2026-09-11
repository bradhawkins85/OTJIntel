"""Compliance feature pack.

Owns the compliance dashboard/routes:

* ``GET /compliance-checks``
* ``GET /compliance-checks/{assignment_id}``
* ``GET /admin/compliance-checks/library``
"""

from __future__ import annotations

from app.core.features import FeaturePack

from .routes import router as compliance_router


PACK = FeaturePack(
    slug="compliance",
    version="1.2.0",
    routers=(compliance_router,),
)


__all__ = ["PACK"]
