from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.category import CategoryOut
from app.schemas.supplier import SupplierOut


class ProductBase(BaseModel):
    sku: str = Field(..., min_length=2, max_length=50, description="Código único de producto (Stock Keeping Unit)")
    name: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = None
    category_id: Optional[int] = None
    supplier_id: Optional[int] = None
    cost_price: float = Field(default=0.0, ge=0.0, description="Precio de costo / adquisición")
    unit_price: float = Field(default=0.0, ge=0.0, description="Precio de venta unitario")
    current_stock: int = Field(default=0, ge=0, description="Stock inicial disponible")
    min_stock_alert: int = Field(default=5, ge=0, description="Umbral para alerta de stock bajo")
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    sku: Optional[str] = Field(None, min_length=2, max_length=50)
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = None
    category_id: Optional[int] = None
    supplier_id: Optional[int] = None
    cost_price: Optional[float] = Field(None, ge=0.0)
    unit_price: Optional[float] = Field(None, ge=0.0)
    min_stock_alert: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ProductOut(ProductBase):
    id: int
    is_low_stock: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductDetailOut(ProductOut):
    category: Optional[CategoryOut] = None
    supplier: Optional[SupplierOut] = None

    model_config = ConfigDict(from_attributes=True)
