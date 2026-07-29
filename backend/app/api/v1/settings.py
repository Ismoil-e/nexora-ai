from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_company_id, get_db

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/company")
async def get_company_settings(
    company_id=Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    pass


@router.put("/company")
async def update_company_settings(
    company_id=Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    pass
