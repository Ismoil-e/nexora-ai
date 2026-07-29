import uuid

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.security import decode_token
from app.repositories.user_repo import UserRepository


async def get_db() -> AsyncSession:
    async for session in get_async_session():
        yield session


async def get_current_user_id(
    authorization: str = Header(None),
) -> uuid.UUID:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token talab qilinadi",
        )

    token = authorization.split(" ")[1]
    payload = decode_token(token)

    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yaroqsiz token",
        )

    return uuid.UUID(payload["sub"])


async def get_current_user(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    user_repo = UserRepository(db)
    user = await user_repo.get(user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Foydalanuvchi topilmadi",
        )
    return user


async def get_current_company_id(
    current_user=Depends(get_current_user),
) -> uuid.UUID:
    return current_user.company_id
