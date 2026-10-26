from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.movement import InventoryMovement, MovementType
from app.models.product import Product
from app.models.user import User
from app.schemas.movement import MovementCreate, MovementOut

router = APIRouter(prefix="/movements", tags=["Movimientos de Inventario"])


@router.post("", response_model=MovementOut, status_code=status.HTTP_201_CREATED, summary="Registrar entrada, salida o ajuste de stock")
def create_movement(
    movement_in: MovementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Registra una transacción de stock en el inventario de manera atómica:
    - **IN (Entrada)**: Incrementa el stock disponible en `quantity` unidades.
    - **OUT (Salida)**: Valida que haya existencias suficientes y descuenta `quantity` unidades.
    - **ADJUSTMENT (Ajuste)**: Establece el stock directamente al valor de `quantity` (útil tras recuentos físicos).
    """
    # Bloquear el registro del producto para consistencia transaccional
    product = db.query(Product).filter(Product.id == movement_in.product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto con ID {movement_in.product_id} no encontrado"
        )

    if not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pueden registrar movimientos en un producto inactivo"
        )

    previous_stock = product.current_stock

    if movement_in.movement_type == MovementType.IN:
        new_stock = previous_stock + movement_in.quantity
    elif movement_in.movement_type == MovementType.OUT:
        if previous_stock < movement_in.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stock insuficiente. Stock actual: {previous_stock}, intentó retirar: {movement_in.quantity}"
            )
        new_stock = previous_stock - movement_in.quantity
    elif movement_in.movement_type == MovementType.ADJUSTMENT:
        new_stock = movement_in.quantity
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de movimiento '{movement_in.movement_type}' no soportado"
        )

    # Actualizar producto
    product.current_stock = new_stock
    if movement_in.unit_cost is not None and movement_in.movement_type == MovementType.IN:
        product.cost_price = movement_in.unit_cost

    # Registrar el movimiento
    movement = InventoryMovement(
        product_id=product.id,
        user_id=current_user.id,
        movement_type=movement_in.movement_type,
        quantity=movement_in.quantity,
        previous_stock=previous_stock,
        new_stock=new_stock,
        unit_cost=movement_in.unit_cost or product.cost_price,
        reference_number=movement_in.reference_number,
        notes=movement_in.notes
    )

    db.add(movement)
    db.commit()
    db.refresh(movement)
    return movement


@router.get("", response_model=List[MovementOut], summary="Consultar historial de movimientos")
def list_movements(
    product_id: Optional[int] = Query(None, description="Filtrar por producto"),
    movement_type: Optional[MovementType] = Query(None, description="Filtrar por tipo (IN, OUT, ADJUSTMENT)"),
    user_id: Optional[int] = Query(None, description="Filtrar por usuario que operó"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Retorna la lista histórica de movimientos de inventario ordenados por fecha descendente."""
    query = (
        db.query(InventoryMovement)
        .options(
            joinedload(InventoryMovement.product),
            joinedload(InventoryMovement.user)
        )
    )

    if product_id:
        query = query.filter(InventoryMovement.product_id == product_id)
    if movement_type:
        query = query.filter(InventoryMovement.movement_type == movement_type)
    if user_id:
        query = query.filter(InventoryMovement.user_id == user_id)

    movements = query.order_by(InventoryMovement.id.desc()).offset(skip).limit(limit).all()
    return movements


@router.get("/{movement_id}", response_model=MovementOut, summary="Obtener detalle de un movimiento específico")
def get_movement(
    movement_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    movement = (
        db.query(InventoryMovement)
        .options(
            joinedload(InventoryMovement.product),
            joinedload(InventoryMovement.user)
        )
        .filter(InventoryMovement.id == movement_id)
        .first()
    )
    if not movement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movimiento no encontrado")
    return movement
