from .categories import router as categories_router
from .channels import router as channels_router
from .search import router as search_router
from .downloads import router as downloads_router

__all__ = [
    "categories_router",
    "channels_router",
    "search_router",
    "downloads_router"
]
