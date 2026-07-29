import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_company_id, get_db
from app.schemas.company import CompanyResponse, CompanyUpdate
from app.services.company_service import CompanyService

router = APIRouter(prefix="/companies", tags=["Companies"])


@router.get("/me", response_model=CompanyResponse)
async def get_my_company(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = CompanyService(db)
    return await service.get_company(company_id)


@router.put("/me", response_model=CompanyResponse)
async def update_my_company(
    body: CompanyUpdate,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = CompanyService(db)
    return await service.update_company(company_id, body.model_dump(exclude_none=True))
