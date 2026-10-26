from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, get_current_admin
from app.models.supplier import Supplier
from app.models.product import Product
from app.models.user import User
from app.schemas.supplier import SupplierCreate, SupplierUpdate, SupplierOut

router = APIRouter(prefix="/suppliers", tags=["Proveedores"])


@router.get("", response_model=List[SupplierOut], summary="Listar todos los proveedores")
def get_suppliers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    return db.query(Supplier).offset(skip).limit(limit).all()


@router.get("/{supplier_id}", response_model=SupplierOut, summary="Obtener proveedor por ID")
def get_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")
    return supplier


@router.post("", response_model=SupplierOut, status_code=status.HTTP_201_CREATED, summary="Crear proveedor (Solo Admin)")
def create_supplier(
    supplier_in: SupplierCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin)
):
    existing = db.query(Supplier).filter(Supplier.name.ilike(supplier_in.name)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un proveedor con ese nombre"
        )
    supplier = Supplier(**supplier_in.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.put("/{supplier_id}", response_model=SupplierOut, summary="Actualizar proveedor (Solo Admin)")
def update_supplier(
    supplier_id: int,
    supplier_in: SupplierUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin)
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")

    update_data = supplier_in.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"] != supplier.name:
        existing = db.query(Supplier).filter(Supplier.name.ilike(update_data["name"])).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe otro proveedor con ese nombre"
            )

    for field, value in update_data.items():
        setattr(supplier, field, value)

    db.commit()
    db.refresh(supplier)
    return supplier


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar proveedor (Solo Admin)")
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin)
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")

    # Desasociar productos
    db.query(Product).filter(Product.supplier_id == supplier_id).update({Product.supplier_id: None})
    db.delete(supplier)
    db.commit()
    return None
