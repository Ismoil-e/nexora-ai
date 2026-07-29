from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("")
async def list_roles(db: AsyncSession = Depends(get_db)):
    pass


@router.post("")
async def create_role(db: AsyncSession = Depends(get_db)):
    pass


@router.put("/{role_id}")
async def update_role(role_id: str, db: AsyncSession = Depends(get_db)):
    pass


@router.get("/permissions")
async def list_permissions(db: AsyncSession = Depends(get_db)):
    pass
