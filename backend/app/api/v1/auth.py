from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_company_id, get_current_user, get_current_user_id, get_db
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    GoogleLoginRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _user_response(user: User) -> dict:
    return {
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
    }


@router.post("/register", response_model=AuthResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    access_token, refresh_token, user = await service.register(
        email=body.email, password=body.password,
        first_name=body.first_name, last_name=body.last_name,
        company_name=body.company_name,
    )
    return AuthResponse(access_token=access_token, refresh_token=refresh_token, user=_user_response(user))


@router.post("/login")
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Login with lockout protection. Returns MFA flag if MFA is enabled."""
    service = AuthService(db)
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    access_token, refresh_token, user, requires_mfa = await service.login(
        email=body.email, password=body.password, ip_address=ip, user_agent=ua,
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "requires_mfa": requires_mfa,
        "user": _user_response(user),
    }


@router.post("/mfa/verify")
async def verify_mfa_login(body: dict, db: AsyncSession = Depends(get_db)):
    """Verify MFA code after login to receive full tokens."""
    import uuid as _uuid
    service = AuthService(db)
    user_id = _uuid.UUID(body["user_id"])
    code = body["code"]
    access_token, refresh_token, user = await service.verify_mfa_login(user_id, code)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": _user_response(user),
    }


@router.post("/logout")
async def logout(
    user_id = Depends(get_current_user_id),
    company_id = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Logout: revoke all active sessions."""
    service = AuthService(db)
    count = await service.logout(user_id, company_id)
    return {"success": True, "revoked_sessions": count}


@router.post("/google", response_model=AuthResponse)
async def google_login(body: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    access_token, refresh_token, user = await service.google_login(
        email=body.email, google_id=body.google_id,
        display_name=body.display_name, photo_url=body.photo_url,
    )
    return AuthResponse(access_token=access_token, refresh_token=refresh_token, user=_user_response(user))


@router.post("/refresh")
async def refresh_token(body: RefreshTokenRequest, request: Request, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    access_token, refresh_token = await service.refresh_token(body.refresh_token, ip_address=ip, user_agent=ua)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


# ---------------------------------------------------------------------------
# Password Reset
# ---------------------------------------------------------------------------

class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str


@router.post("/password/reset-request")
async def request_password_reset(body: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    """Request a password reset token."""
    service = AuthService(db)
    token = await service.request_password_reset(body.email)
    # In production, send email here. For now return token for testing.
    return {
        "success": True,
        "message": "Agar email mavjud bo'lsa, parol tiklash havolasi yuborildi.",
        "debug_token": token,  # Remove in production
    }


@router.post("/password/reset-confirm")
async def confirm_password_reset(body: PasswordResetConfirmRequest, db: AsyncSession = Depends(get_db)):
    """Confirm password reset with token."""
    service = AuthService(db)
    success = await service.confirm_password_reset(body.token, body.new_password)
    return {"success": success, "message": "Parol muvaffaqiyatli yangilandi"}
