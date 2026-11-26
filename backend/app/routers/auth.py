import aiosqlite
from fastapi import APIRouter, Depends

from app.database import get_db
from app.schemas import AuthResponse, LoginRequest, RegisterRequest, UserOut
from app.security import get_current_user
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(payload: RegisterRequest, db: aiosqlite.Connection = Depends(get_db)):
    return await auth_service.register_user(db, payload)


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, db: aiosqlite.Connection = Depends(get_db)):
    return await auth_service.login_user(db, payload)


@router.get("/me", response_model=UserOut)
async def me(current_user: dict = Depends(get_current_user)):
    return UserOut(
        id=current_user["id"],
        name=current_user["name"],
        email=current_user["email"],
    )
