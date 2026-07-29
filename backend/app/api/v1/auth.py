from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.auth import (
    AuthResponse,
    GoogleLoginRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    access_token, refresh_token, user = await service.register(
        email=body.email,
        password=body.password,
        first_name=body.first_name,
        last_name=body.last_name,
        company_name=body.company_name,
    )
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "avatar_url": user.avatar_url,
            "position": user.position,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "company_id": user.company_id,
            "role_id": user.role_id,
            "created_at": user.created_at.isoformat(),
        },
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    access_token, refresh_token, user = await service.login(
        email=body.email, password=body.password
    )
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "avatar_url": user.avatar_url,
            "position": user.position,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "company_id": user.company_id,
            "role_id": user.role_id,
            "created_at": user.created_at.isoformat(),
        },
    )


@router.post("/google", response_model=AuthResponse)
async def google_login(body: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    access_token, refresh_token, user = await service.google_login(
        email=body.email,
        google_id=body.google_id,
        display_name=body.display_name,
        photo_url=body.photo_url,
    )
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "avatar_url": user.avatar_url,
            "position": user.position,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "company_id": user.company_id,
            "role_id": user.role_id,
            "created_at": user.created_at.isoformat(),
        },
    )


@router.post("/refresh")
async def refresh_token(body: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    access_token, refresh_token = await service.refresh_token(body.refresh_token)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}
