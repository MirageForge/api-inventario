from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.movement import MovementType


class MovementCreate(BaseModel):
    product_id: int = Field(..., description="ID del producto a mover")
    movement_type: MovementType = Field(..., description="Tipo de movimiento: IN (Entrada), OUT (Salida), ADJUSTMENT (Ajuste)")
    quantity: int = Field(..., gt=0, description="Cantidad de unidades involucradas (debe ser mayor a 0)")
    unit_cost: Optional[float] = Field(None, ge=0.0, description="Costo unitario registrado (opcional para entradas)")
    reference_number: Optional[str] = Field(None, max_length=100, description="Número de remito, factura u orden de compra")
    notes: Optional[str] = Field(None, description="Observaciones o motivo del movimiento")


class MovementProductInfo(BaseModel):
    id: int
    sku: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class MovementUserInfo(BaseModel):
    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)


class MovementOut(BaseModel):
    id: int
    product_id: int
    user_id: Optional[int]
    movement_type: MovementType
    quantity: int
    previous_stock: int
    new_stock: int
    unit_cost: Optional[float]
    reference_number: Optional[str]
    notes: Optional[str]
    created_at: datetime
    product: Optional[MovementProductInfo] = None
    user: Optional[MovementUserInfo] = None

    model_config = ConfigDict(from_attributes=True)
