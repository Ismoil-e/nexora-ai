import uuid
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Permission, Role, RolePermission
from app.schemas.security import RoleCreate, RoleUpdate
from app.utils.exceptions import NotFoundException, ValidationException


class RoleService:
    """Service managing RBAC roles and permissions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_roles(self, company_id: uuid.UUID) -> List[Role]:
        res = await self.db.scalars(
            select(Role).where(Role.company_id == company_id, Role.deleted_at.is_(None)).order_by(Role.priority.desc(), Role.name)
        )
        return list(res.all())

    async def list_permissions(self) -> List[Permission]:
        res = await self.db.scalars(select(Permission).order_by(Permission.module, Permission.code))
        perms = list(res.all())
        if not perms:
            # Seed default system permissions if empty
            perms = await self._seed_default_permissions()
        return perms

    async def create_role(self, company_id: uuid.UUID, payload: RoleCreate) -> Role:
        role = Role(
            company_id=company_id,
            name=payload.name,
            description=payload.description,
            is_system=False,
        )
        self.db.add(role)
        await self.db.flush()

        if payload.permission_ids:
            for pid in payload.permission_ids:
                rp = RolePermission(role_id=role.id, permission_id=pid)
                self.db.add(rp)

        await self.db.commit()
        await self.db.refresh(role)
        return role

    async def update_role(self, company_id: uuid.UUID, role_id: uuid.UUID, payload: RoleUpdate) -> Role:
        role = await self.db.get(Role, role_id)
        if not role or role.company_id != company_id or role.deleted_at is not None:
            raise NotFoundException("Rol topilmadi")
        if role.is_system:
            raise ValidationException("Tizim rolini o'zgartirib bo'lmaydi")

        if payload.name is not None:
            role.name = payload.name
        if payload.description is not None:
            role.description = payload.description

        if payload.permission_ids is not None:
            # Clear old role permissions and reassign
            await self.db.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
            for pid in payload.permission_ids:
                rp = RolePermission(role_id=role.id, permission_id=pid)
                self.db.add(rp)

        await self.db.commit()
        await self.db.refresh(role)
        return role

    async def delete_role(self, company_id: uuid.UUID, role_id: uuid.UUID) -> bool:
        """Soft-delete a role. System roles cannot be deleted."""
        role = await self.db.get(Role, role_id)
        if not role or role.company_id != company_id or role.deleted_at is not None:
            raise NotFoundException("Rol topilmadi")
        if role.is_system:
            raise ValidationException("Tizim rolini o'chirib bo'lmaydi")

        from datetime import datetime, timezone
        role.deleted_at = datetime.now(timezone.utc)
        await self.db.commit()
        return True

    async def _seed_default_permissions(self) -> List[Permission]:
        defaults = [
            # Document permissions
            ("document.read", "Hujjatlarni o'qish", "Hujjatlar va bilimlarni o'qish", "document"),
            ("document.write", "Hujjat yuklash va tahrirlash", "Yangi hujjatlar kiritish", "document"),
            ("document.delete", "Hujjatni o'chirish", "Hujjatlarni o'chirish", "document"),
            ("document.share", "Hujjatni ulashish", "Hujjatga boshqalarni ruxsat berish", "document"),
            # Chat permissions
            ("chat.read", "Suhbatlarni ko'rish", "AI suhbatlar tarixini o'qish", "chat"),
            ("chat.export", "Suhbatni eksport qilish", "Suhbat tarixini yuklab olish", "chat"),
            # Memory permissions
            ("memory.read", "Xotirani o'qish", "Second Brain xotirasini o'qish", "memory"),
            ("memory.write", "Xotirani yozish", "Second Brain ga ma'lumot qo'shish", "memory"),
            # Agent permissions
            ("agent.execute", "AI Agentlarni ishlatish", "AI Agent qobiliyatlarini chaqirish", "agent"),
            ("agent.manage", "Agentlarni boshqarish", "Agentlarni yaratish va sozlash", "agent"),
            # Workflow permissions
            ("workflow.execute", "Ish oqimlarini bajarish", "Ish oqimlarini ishga tushirish", "workflow"),
            ("workflow.manage", "Ish oqimlarini boshqarish", "Ish oqimlarini yaratish va tahrirlash", "workflow"),
            # Task permissions
            ("task.read", "Vazifalarni ko'rish", "Vazifalar ro'yxatini ko'rish", "task"),
            ("task.create", "Vazifa yaratish", "Yangi vazifalar yaratish", "task"),
            # BI permissions
            ("bi.read", "Biznes tahlilni ko'rish", "KPI va tahlillarni ko'rish", "bi"),
            ("bi.manage", "BI boshqarish", "KPI va boshqaruv panellarini sozlash", "bi"),
            # Integration permissions
            ("integration.execute", "Integratsiyalarni chaqirish", "Tashqi tizimlar bilan ishlash", "integration"),
            # Notification permissions
            ("notification.send", "Bildirishnoma yuborish", "Bildirishnomalar yuborish", "notification"),
            # Report permissions
            ("report.read", "Hisobotlarni ko'rish", "Hisobotlarni ko'rish", "report"),
            ("report.generate", "Hisobot yaratish", "Yangi hisobotlar yaratish", "report"),
            # Dashboard permissions
            ("dashboard.read", "Panelni ko'rish", "Dashboard ma'lumotlarini ko'rish", "dashboard"),
            # Admin permissions
            ("admin.manage", "Admin boshqaruvi", "To'liq korporativ boshqaruv", "admin"),
            # Security permissions
            ("security.manage", "Xavfsizlik boshqaruvi", "Xavfsizlik sozlamalarini boshqarish", "security"),
        ]
        created = []
        for code, name, desc, mod in defaults:
            p = Permission(code=code, name=name, description=desc, module=mod)
            self.db.add(p)
            created.append(p)
        await self.db.commit()
        for p in created:
            await self.db.refresh(p)
        return created
