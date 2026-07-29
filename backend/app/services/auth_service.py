import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.company import Company
from app.models.session import RefreshToken
from app.models.user import User
from app.repositories.company_repo import CompanyRepository
from app.repositories.user_repo import UserRepository
from app.utils.exceptions import ConflictException, UnauthorizedException
from app.utils.helpers import generate_slug


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.company_repo = CompanyRepository(db)

    async def register(self, email: str, password: str, first_name: str,
                        last_name: str, company_name: str) -> tuple[str, str, User]:
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise ConflictException("Bu email bilan profil allaqachon mavjud")

        slug = generate_slug(company_name)
        existing_company = await self.company_repo.get_by_slug(slug)
        if existing_company:
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"

        company = await self.company_repo.create(
            name=company_name,
            slug=slug,
        )

        password_hash = hash_password(password)
        user = await self.user_repo.create(
            company_id=company.id,
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
        )

        access_token = create_access_token(str(user.id), {
            "company_id": str(company.id),
            "email": user.email,
        })
        refresh_token = create_refresh_token(str(user.id))

        await self._save_refresh_token(user.id, refresh_token)

        return access_token, refresh_token, user

    async def login(self, email: str, password: str) -> tuple[str, str, User]:
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise UnauthorizedException("Email yoki parol noto'g'ri")

        if not user.password_hash:
            raise UnauthorizedException("Bu akkaunt Google orqali yaratilgan")

        if not verify_password(password, user.password_hash):
            raise UnauthorizedException("Email yoki parol noto'g'ri")

        if not user.is_active:
            raise UnauthorizedException("Akkaunt faol emas")

        access_token = create_access_token(str(user.id), {
            "company_id": str(user.company_id),
            "email": user.email,
        })
        refresh_token = create_refresh_token(str(user.id))

        await self._save_refresh_token(user.id, refresh_token)

        return access_token, refresh_token, user

    async def google_login(self, email: str, google_id: str, display_name: str | None = None,
                            photo_url: str | None = None) -> tuple[str, str, User]:
        user = await self.user_repo.get_by_google_id(google_id)
        if not user:
            user = await self.user_repo.get_by_email(email)

        if not user:
            slug = generate_slug(f"{display_name or email}-company")
            company = await self.company_repo.create(
                name=f"{display_name or email}'s Company",
                slug=slug,
            )

            name_parts = (display_name or email).split()
            user = await self.user_repo.create(
                company_id=company.id,
                email=email,
                google_id=google_id,
                first_name=name_parts[0] if name_parts else "User",
                last_name=" ".join(name_parts[1:]) if len(name_parts) > 1 else "User",
                avatar_url=photo_url or "",
                is_verified=True,
            )
        else:
            if not user.google_id:
                await self.user_repo.update(user.id, google_id=google_id)
            if photo_url and not user.avatar_url:
                await self.user_repo.update(user.id, avatar_url=photo_url)

        access_token = create_access_token(str(user.id), {
            "company_id": str(user.company_id),
            "email": user.email,
        })
        refresh_token = create_refresh_token(str(user.id))

        await self._save_refresh_token(user.id, refresh_token)

        return access_token, refresh_token, user

    async def refresh_token(self, token: str) -> tuple[str, str]:
        payload = decode_token(token)
        if not payload or payload.get("type") != "refresh":
            raise UnauthorizedException("Yaroqsiz refresh token")

        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException("Token noto'g'ri")

        user = await self.user_repo.get(uuid.UUID(user_id))
        if not user or not user.is_active:
            raise UnauthorizedException("Foydalanuvchi topilmadi")

        new_access = create_access_token(user_id, {
            "company_id": str(user.company_id),
            "email": user.email,
        })
        new_refresh = create_refresh_token(user_id)

        await self._save_refresh_token(user.id, new_refresh)

        return new_access, new_refresh

    async def _save_refresh_token(self, user_id: uuid.UUID, token: str):
        from hashlib import sha256

        token_hash = sha256(token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        stmt = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(stmt)
        await self.db.flush()
