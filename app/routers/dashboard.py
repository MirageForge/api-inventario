from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.database import get_db
from app.dependencies import get_current_user
from app.models.category import Category
from app.models.movement import InventoryMovement
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.dashboard import DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["Dashboard y Reportes"])


@router.get("/summary", response_model=DashboardSummary, summary="Resumen ejecutivo del inventario y métricas clave")
def get_dashboard_summary(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """
    Calcula en tiempo real los indicadores clave del almacén:
    - Cantidad total de productos, categorías y proveedores.
    - Cantidad de productos en nivel crítico de stock.
    - Valor total de inventario a costo de adquisición y a precio de venta.
    - Lista de productos en alerta y últimos movimientos.
    """
    total_products = db.query(Product).filter(Product.is_active.is_(True)).count()
    total_categories = db.query(Category).count()
    total_suppliers = db.query(Supplier).count()

    # Métricas agregadas calculadas directamente en base de datos (previene fugas de memoria y OOM)
    aggregations = (
        db.query(
            func.coalesce(func.sum(Product.current_stock), 0).label("total_units"),
            func.coalesce(func.sum(Product.current_stock * Product.cost_price), 0.0).label("total_cost"),
            func.coalesce(func.sum(Product.current_stock * Product.unit_price), 0.0).label("total_retail"),
        )
        .filter(Product.is_active.is_(True))
        .first()
    )

    total_units = int(aggregations.total_units) if aggregations else 0
    total_cost_valuation = float(aggregations.total_cost) if aggregations else 0.0
    total_retail_valuation = float(aggregations.total_retail) if aggregations else 0.0

    # Consulta optimizada de productos con alerta de stock crítico
    low_stock_query = (
        db.query(Product)
        .filter(
            Product.is_active.is_(True),
            Product.current_stock <= Product.min_stock_alert
        )
    )
    low_stock_count = low_stock_query.count()
    low_stock_products = low_stock_query.order_by(Product.current_stock.asc()).limit(20).all()
    for p in low_stock_products:
        setattr(p, "is_low_stock", True)

    # Últimos 10 movimientos
    recent_movements = (
        db.query(InventoryMovement)
        .options(
            joinedload(InventoryMovement.product),
            joinedload(InventoryMovement.user)
        )
        .order_by(InventoryMovement.id.desc())
        .limit(10)
        .all()
    )

    return DashboardSummary(
        total_products=total_products,
        total_categories=total_categories,
        total_suppliers=total_suppliers,
        low_stock_products_count=low_stock_count,
        total_units_in_stock=total_units,
        total_inventory_valuation_cost=round(total_cost_valuation, 2),
        total_inventory_valuation_retail=round(total_retail_valuation, 2),
        low_stock_products=low_stock_products,
        recent_movements=recent_movements
    )
