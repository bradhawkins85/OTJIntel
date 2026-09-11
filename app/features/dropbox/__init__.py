from app.core.features import FeaturePack

from .admin_routes import router as admin_router
from .api_routes import router as api_router

PACK = FeaturePack(slug="dropbox", version="1.0.0", routers=(api_router, admin_router))

__all__ = ["PACK"]
