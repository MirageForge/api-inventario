from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.dependencies import get_current_user, get_current_admin
from app.models.category import Category
from app.models.movement import InventoryMovement, MovementType
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.product import ProductCreate, ProductUpdate, ProductOut, ProductDetailOut

router = APIRouter(prefix="/products", tags=["Productos"])


def _attach_computed_fields(product: Product) -> Product:
    setattr(product, "is_low_stock", product.current_stock <= product.min_stock_alert)
    return product


@router.get("", response_model=List[ProductOut], summary="Listar productos con filtros y paginación")
def list_products(
    category_id: Optional[int] = Query(None, description="Filtrar por ID de categoría"),
    supplier_id: Optional[int] = Query(None, description="Filtrar por ID de proveedor"),
    low_stock_only: bool = Query(False, description="Filtrar únicamente productos con stock bajo o en alerta"),
    search: Optional[str] = Query(None, description="Buscar por SKU o nombre del producto"),
    is_active: Optional[bool] = Query(True, description="Filtrar por estado activo"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    query = db.query(Product)

    if is_active is not None:
        query = query.filter(Product.is_active == is_active)

    if category_id:
        query = query.filter(Product.category_id == category_id)

    if supplier_id:
        query = query.filter(Product.supplier_id == supplier_id)

    if low_stock_only:
        query = query.filter(Product.current_stock <= Product.min_stock_alert)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                Product.name.ilike(search_filter),
                Product.sku.ilike(search_filter)
            )
        )

    products = query.order_by(Product.id.desc()).offset(skip).limit(limit).all()
    return [_attach_computed_fields(p) for p in products]


@router.get("/{product_id}", response_model=ProductDetailOut, summary="Obtener detalle de producto con categoría y proveedor")
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    return _attach_computed_fields(product)


@router.post("", response_model=ProductDetailOut, status_code=status.HTTP_201_CREATED, summary="Crear producto (Solo Admin)")
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    # Validar SKU único
    if db.query(Product).filter(Product.sku.ilike(product_in.sku)).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un producto con el SKU '{product_in.sku}'"
        )

    # Validar categoría si se especificó
    if product_in.category_id:
        if not db.query(Category).filter(Category.id == product_in.category_id).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La categoría con ID {product_in.category_id} no existe"
            )

    # Validar proveedor si se especificó
    if product_in.supplier_id:
        if not db.query(Supplier).filter(Supplier.id == product_in.supplier_id).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El proveedor con ID {product_in.supplier_id} no existe"
            )

    product = Product(**product_in.model_dump())
    db.add(product)
    db.flush()

    # Si se crea con inventario inicial mayor a 0, registrar automáticamente el movimiento inicial
    if product.current_stock > 0:
        initial_movement = InventoryMovement(
            product_id=product.id,
            user_id=current_user.id,
            movement_type=MovementType.IN,
            quantity=product.current_stock,
            previous_stock=0,
            new_stock=product.current_stock,
            unit_cost=product.cost_price,
            reference_number="INICIO-INVENTARIO",
            notes="Stock inicial registrado al dar de alta el producto"
        )
        db.add(initial_movement)

    db.commit()
    db.refresh(product)
    return _attach_computed_fields(product)


@router.put("/{product_id}", response_model=ProductDetailOut, summary="Actualizar información de producto (Solo Admin)")
def update_product(
    product_id: int,
    product_in: ProductUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")

    update_data = product_in.model_dump(exclude_unset=True)

    if "sku" in update_data and update_data["sku"] != product.sku:
        existing = db.query(Product).filter(Product.sku.ilike(update_data["sku"])).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe otro producto con el SKU '{update_data['sku']}'"
            )

    if "category_id" in update_data and update_data["category_id"] is not None:
        if not db.query(Category).filter(Category.id == update_data["category_id"]).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Categoría no encontrada")

    if "supplier_id" in update_data and update_data["supplier_id"] is not None:
        if not db.query(Supplier).filter(Supplier.id == update_data["supplier_id"]).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Proveedor no encontrado")

    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return _attach_computed_fields(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Desactivar o eliminar producto (Solo Admin)")
def delete_product(
    product_id: int,
    hard_delete: bool = Query(False, description="Si es True y no tiene movimientos, se elimina definitivamente; si False, se desactiva"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")

    if hard_delete:
        db.delete(product)
    else:
        product.is_active = False

    db.commit()
    return None
