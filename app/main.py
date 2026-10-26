from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.models.user import User, UserRole
from app.security import get_password_hash
from app.routers import (
    auth_router,
    categories_router,
    suppliers_router,
    products_router,
    movements_router,
    dashboard_router,
)


def init_db():
    """Crea las tablas en la base de datos e inicializa el superusuario si no existe."""
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == settings.FIRST_ADMIN_USERNAME).first()
        if not admin:
            default_admin = User(
                username=settings.FIRST_ADMIN_USERNAME,
                email=settings.FIRST_ADMIN_EMAIL,
                full_name="Administrador del Sistema",
                hashed_password=get_password_hash(settings.FIRST_ADMIN_PASSWORD),
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(default_admin)
            db.commit()
            print(f"[BOOTSTRAP] Superusuario inicial creado: {settings.FIRST_ADMIN_USERNAME}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicio: inicializar base de datos y usuario admin por defecto
    init_db()
    yield
    # Apagado (si fuera necesario liberar recursos)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
# API de Gestión de Inventario y Almacén 📦
Esta API proporciona un sistema integral para gestionar inventarios, productos, proveedores, categorías y trazabilidad de movimientos de stock.

### Características Principales:
* 🔐 **Autenticación JWT y Roles**: Control de accesos basado en roles (`admin` y `operator`).
* 🏷️ **Categorías y Proveedores**: Organización del catálogo y gestión de contactos comerciales.
* 📦 **Productos con Control de Stock**: Gestión de SKU, precios de compra/venta y alertas de reposición automática.
* 🔄 **Movimientos de Stock Atómicos**: Entradas (IN), salidas con validación de stock disponible (OUT) y ajustes de auditoría (ADJUSTMENT).
* 📊 **Dashboard y Métricas en Tiempo Real**: Valoración financiera del inventario (costo vs venta) y reporte de productos críticos.
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montaje de routers con prefijo de API v1
api_prefix = settings.API_V1_PREFIX
app.include_router(auth_router, prefix=api_prefix)
app.include_router(categories_router, prefix=api_prefix)
app.include_router(suppliers_router, prefix=api_prefix)
app.include_router(products_router, prefix=api_prefix)
app.include_router(movements_router, prefix=api_prefix)
app.include_router(dashboard_router, prefix=api_prefix)


@app.get("/", summary="Ruta raíz con información de la API")
def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "api_v1_prefix": settings.API_V1_PREFIX,
        "status": "online"
    }


@app.get("/health", summary="Chequeo de salud del servicio")
def health():
    return {"status": "healthy"}
