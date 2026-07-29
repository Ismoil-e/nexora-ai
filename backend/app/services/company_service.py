import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.company_repo import CompanyRepository


class CompanyService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.company_repo = CompanyRepository(db)

    async def get_company(self, company_id: uuid.UUID) -> dict:
        company = await self.company_repo.get(company_id)
        if not company:
            return None

        user_count = await self.company_repo.get_user_count(company_id)

        return {
            "id": company.id,
            "name": company.name,
            "slug": company.slug,
            "logo_url": company.logo_url,
            "description": company.description,
            "industry": company.industry,
            "size": company.size,
            "website": company.website,
            "is_active": company.is_active,
            "subscription_plan": company.subscription_plan,
            "ai_credits": company.ai_credits,
            "max_users": company.max_users,
            "user_count": user_count,
            "created_at": company.created_at.isoformat(),
        }

    async def update_company(self, company_id: uuid.UUID, data: dict) -> dict:
        await self.company_repo.update(company_id, **data)
        return await self.get_company(company_id)
