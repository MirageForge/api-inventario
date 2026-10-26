from app.routers.auth import router as auth_router
from app.routers.categories import router as categories_router
from app.routers.suppliers import router as suppliers_router
from app.routers.products import router as products_router
from app.routers.movements import router as movements_router
from app.routers.dashboard import router as dashboard_router

__all__ = [
    "auth_router",
    "categories_router",
    "suppliers_router",
    "products_router",
    "movements_router",
    "dashboard_router",
]
