from app.core.features import FeaturePack

from .routes import router

PACK = FeaturePack(slug="ai_tag_synonyms", version="1.0.0", routers=(router,))

__all__ = ["PACK"]
