from typing import List
from pydantic import BaseModel
from app.schemas.product import ProductOut
from app.schemas.movement import MovementOut


class DashboardSummary(BaseModel):
    total_products: int
    total_categories: int
    total_suppliers: int
    low_stock_products_count: int
    total_units_in_stock: int
    total_inventory_valuation_cost: float
    total_inventory_valuation_retail: float
    low_stock_products: List[ProductOut]
    recent_movements: List[MovementOut]
