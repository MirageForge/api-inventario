import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database import Base


class MovementType(str, enum.Enum):
    IN = "IN"                  # Entrada de inventario (compra/recepción)
    OUT = "OUT"                # Salida de inventario (venta/despacho)
    ADJUSTMENT = "ADJUSTMENT"  # Ajuste de inventario (conteo físico/corrección)


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    movement_type = Column(Enum(MovementType), nullable=False)
    quantity = Column(Integer, nullable=False)  # Cantidad involucrada
    previous_stock = Column(Integer, nullable=False)
    new_stock = Column(Integer, nullable=False)
    unit_cost = Column(Float, nullable=True)     # Costo al momento del movimiento
    reference_number = Column(String(100), nullable=True)  # Factura, orden de compra, remito
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    product = relationship("Product", back_populates="movements")
    user = relationship("User", back_populates="movements")
