from datetime import timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, get_current_admin
from app.models.user import User, UserRole
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.security import verify_password, get_password_hash, create_access_token

router = APIRouter(prefix="/auth", tags=["Autenticación y Usuarios"])


@router.post("/login", response_model=Token, summary="Iniciar sesión y obtener JWT")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Endpoint compatible con OAuth2 Password Flow (Swagger UI /docs).
    Envía `username` (puede ser username o email) y `password`.
    """
    user = (
        db.query(User)
        .filter((User.username == form_data.username) | (User.email == form_data.username))
        .first()
    )

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cuenta de usuario desactivada"
        )

    access_token = create_access_token(subject=str(user.id))
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED, summary="Registrar nuevo usuario")
def register(
    user_in: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Registra un nuevo usuario en el sistema.
    Si es el primer usuario en la base de datos, se le asigna rol de administrador automáticamente.
    """
    # Verificar si ya existe username o email
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario ya está registrado."
        )
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado."
        )

    # Si es el primer usuario registrado, otorgar admin automáticamente
    is_first_user = db.query(User).count() == 0
    assigned_role = UserRole.ADMIN if is_first_user else user_in.role

    new_user = User(
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
        role=assigned_role,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.get("/me", response_model=UserOut, summary="Obtener perfil del usuario actual")
def get_me(current_user: User = Depends(get_current_user)):
    """Retorna los datos del usuario actualmente autenticado con el token Bearer."""
    return current_user


@router.get("/users", response_model=List[UserOut], summary="Listar todos los usuarios (Solo Administradores)")
def list_users(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin)
):
    """Lista todos los usuarios del sistema. Requiere permisos de Administrador."""
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.patch("/users/{user_id}", response_model=UserOut, summary="Actualizar usuario (Solo Administradores)")
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin)
):
    """Permite al administrador modificar rol, estado activo o datos de un usuario."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    update_data = user_in.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
        user.hashed_password = get_password_hash(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user
