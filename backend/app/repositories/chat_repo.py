import uuid

from sqlalchemy import func, select

from app.models.chat import Chat, ChatMessage
from app.repositories.base import BaseRepository
from app.utils.helpers import paginate


class ChatRepository(BaseRepository[Chat]):
    def __init__(self, db):
        super().__init__(Chat, db)

    async def get_persistent_for_user(self, company_id: uuid.UUID, user_id: uuid.UUID) -> Chat | None:
        stmt = (
            select(Chat)
            .where(
                Chat.company_id == company_id,
                Chat.user_id == user_id,
                Chat.deleted_at.is_(None),
            )
            .order_by(Chat.created_at.asc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_owned(self, chat_id: uuid.UUID, user_id: uuid.UUID) -> Chat | None:
        stmt = select(Chat).where(
            Chat.id == chat_id,
            Chat.user_id == user_id,
            Chat.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_company(self, company_id: uuid.UUID, user_id: uuid.UUID | None = None,
                              page: int = 1, page_size: int = 20) -> tuple[list[Chat], int]:
        offset, limit = paginate(page, page_size)
        filters = [Chat.company_id == company_id, Chat.deleted_at.is_(None)]
        if user_id:
            filters.append(Chat.user_id == user_id)

        stmt = (
            select(Chat)
            .where(*filters)
            .offset(offset).limit(limit)
            .order_by(Chat.updated_at.desc())
        )
        result = await self.db.execute(stmt)
        chats = list(result.scalars().all())

        count_stmt = select(func.count()).select_from(Chat).where(*filters)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()

        return chats, total


class ChatMessageRepository(BaseRepository[ChatMessage]):
    def __init__(self, db):
        super().__init__(ChatMessage, db)

    async def get_by_chat(self, chat_id: uuid.UUID, page: int = 1, page_size: int = 50) -> tuple[list[ChatMessage], int]:
        offset, limit = paginate(page, page_size)

        stmt = (
            select(ChatMessage)
            .where(ChatMessage.chat_id == chat_id, ChatMessage.deleted_at.is_(None))
            .offset(offset).limit(limit)
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        )
        result = await self.db.execute(stmt)
        messages = list(result.scalars().all())

        count_stmt = (
            select(func.count())
            .select_from(ChatMessage)
            .where(ChatMessage.chat_id == chat_id, ChatMessage.deleted_at.is_(None))
        )
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()

        return messages, total

    async def get_recent_by_chat(self, chat_id: uuid.UUID, limit: int = 20) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.chat_id == chat_id, ChatMessage.deleted_at.is_(None))
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(reversed(result.scalars().all()))
