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

    # Productos activos
    active_products = db.query(Product).filter(Product.is_active.is_(True)).all()
    
    low_stock_list = []
    total_units = 0
    total_cost_valuation = 0.0
    total_retail_valuation = 0.0

    for p in active_products:
        setattr(p, "is_low_stock", p.current_stock <= p.min_stock_alert)
        total_units += p.current_stock
        total_cost_valuation += (p.current_stock * (p.cost_price or 0.0))
        total_retail_valuation += (p.current_stock * (p.unit_price or 0.0))
        if p.is_low_stock:
            low_stock_list.append(p)

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
        low_stock_products_count=len(low_stock_list),
        total_units_in_stock=total_units,
        total_inventory_valuation_cost=round(total_cost_valuation, 2),
        total_inventory_valuation_retail=round(total_retail_valuation, 2),
        low_stock_products=low_stock_list[:20],
        recent_movements=recent_movements
    )
