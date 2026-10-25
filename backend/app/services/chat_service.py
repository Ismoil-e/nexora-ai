import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Chat, ChatMessage
from app.models.user import User
from app.repositories.chat_repo import ChatMessageRepository, ChatRepository
from app.schemas.chat import LegacyChatMessage
from app.services.ai_service import AIService


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.chat_repo = ChatRepository(db)
        self.message_repo = ChatMessageRepository(db)

    async def create_chat(
        self,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str = "New Chat",
        ai_provider: str = "gemini",
        model: str = "gemini-2.5-flash",
        agent_id: uuid.UUID | None = None,
    ) -> Chat:
        return await self.chat_repo.create(
            company_id=company_id,
            user_id=user_id,
            title=title,
            ai_provider=ai_provider,
            model=model,
            agent_id=agent_id,
        )

    async def get_or_create_persistent_chat(
        self, company_id: uuid.UUID, user_id: uuid.UUID
    ) -> Chat:
        # Serialize first-time creation per user so simultaneous tabs reuse one chat.
        await self.db.execute(
            select(User.id).where(User.id == user_id).with_for_update()
        )
        chat = await self.chat_repo.get_persistent_for_user(company_id, user_id)
        if chat:
            return chat
        return await self.create_chat(
            company_id=company_id,
            user_id=user_id,
            title="Yagona suhbat",
        )

    async def get_user_chats(
        self,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        chats, total = await self.chat_repo.get_by_company(
            company_id, user_id, page, page_size
        )
        items = []
        for chat in chats:
            msg_count = len(chat.messages) if chat.messages else 0
            items.append({
                "id": chat.id,
                "title": chat.title,
                "ai_provider": chat.ai_provider,
                "model": chat.model,
                "token_count": chat.token_count,
                "is_archived": chat.is_archived,
                "message_count": msg_count,
                "created_at": chat.created_at.isoformat(),
                "updated_at": chat.updated_at.isoformat(),
            })
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    @staticmethod
    def _metadata(message: ChatMessage) -> dict[str, Any]:
        if not message.meta_data:
            return {}
        try:
            value = json.loads(message.meta_data)
        except (TypeError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}

    @classmethod
    def _serialize_message(cls, message: ChatMessage) -> dict:
        metadata = cls._metadata(message)
        return {
            "id": str(message.id),
            "chat_id": str(message.chat_id),
            "role": message.role,
            "content": message.content,
            "token_count": message.token_count,
            "created_at": message.created_at.isoformat(),
            "attachment_name": metadata.get("attachment_name"),
            "sources": metadata.get("sources") or [],
            "legacy_timestamp": metadata.get("legacy_timestamp"),
        }

    async def send_message(
        self,
        chat_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str,
        attachment_name: str | None = None,
    ) -> dict | None:
        chat = await self.chat_repo.get_owned(chat_id, user_id)
        if not chat:
            return None

        previous_messages = await self.message_repo.get_recent_by_chat(chat_id, limit=20)
        history = [
            {"role": message.role, "content": message.content}
            for message in previous_messages
        ]

        user_metadata = {}
        if attachment_name:
            user_metadata["attachment_name"] = attachment_name
        user_msg = await self.message_repo.create(
            chat_id=chat_id,
            user_id=user_id,
            role="user",
            content=content,
            token_count=len(content.split()),
            created_at=datetime.now(timezone.utc),
            meta_data=json.dumps(user_metadata, ensure_ascii=False) if user_metadata else None,
        )

        ai_response = await AIService(
            self.db, company_id=chat.company_id, user_id=user_id
        ).chat(
            provider=chat.ai_provider,
            model=chat.model,
            messages=history + [{"role": "user", "content": content}],
            system_prompt="Sen Nexora AI yordamchisisan. Foydalanuvchilarga o'zbek tilida javob ber.",
        )
        ai_content = ai_response.get("content") or ""
        sources = ai_response.get("sources") or ai_response.get("citations") or []
        if not isinstance(sources, list):
            sources = []
        ai_metadata = {"sources": sources} if sources else {}
        ai_msg = await self.message_repo.create(
            chat_id=chat_id,
            user_id=user_id,
            role="assistant",
            content=ai_content,
            token_count=ai_response.get("token_count", len(ai_content.split())),
            created_at=max(
                datetime.now(timezone.utc),
                user_msg.created_at + timedelta(microseconds=1),
            ),
            meta_data=json.dumps(ai_metadata, ensure_ascii=False) if ai_metadata else None,
        )

        total_tokens = chat.token_count + user_msg.token_count + ai_msg.token_count
        await self.chat_repo.update(chat_id, token_count=total_tokens)

        return {
            "message": self._serialize_message(user_msg),
            "ai_message": self._serialize_message(ai_msg),
            "chat_id": str(chat_id),
            "token_used": ai_response.get("token_count", 0),
        }

    async def import_legacy_history(
        self,
        chat_id: uuid.UUID,
        user_id: uuid.UUID,
        messages: list[LegacyChatMessage],
    ) -> dict:
        chat = await self.chat_repo.get_owned(chat_id, user_id)
        if not chat:
            return {"imported": 0, "already_exists": False}

        _, existing_count = await self.message_repo.get_by_chat(
            chat_id, page=1, page_size=1
        )
        if existing_count:
            return {"imported": 0, "already_exists": True}

        imported = 0
        imported_at = datetime.now(timezone.utc)
        for legacy in messages:
            if not legacy.text.strip():
                continue
            metadata = {
                "legacy_id": legacy.id,
                "legacy_timestamp": legacy.timestamp,
                "attachment_name": legacy.attachment_name,
                "sources": legacy.sources,
            }
            role = "assistant" if legacy.role in {"ai", "assistant"} else "user"
            await self.message_repo.create(
                chat_id=chat_id,
                user_id=user_id if role == "user" else None,
                role=role,
                content=legacy.text,
                token_count=len(legacy.text.split()),
                created_at=imported_at + timedelta(microseconds=imported),
                meta_data=json.dumps(metadata, ensure_ascii=False),
            )
            imported += 1
        return {"imported": imported, "already_exists": False}

    async def send_message_stream(
        self, chat_id: uuid.UUID, user_id: uuid.UUID, content: str
    ):
        import json as json_module

        chat = await self.chat_repo.get_owned(chat_id, user_id)
        if not chat:
            yield f"data: {json_module.dumps({'error': 'Chat topilmadi'})}\n\n"
            return

        previous_messages = await self.message_repo.get_recent_by_chat(chat_id, limit=20)
        history = [
            {"role": message.role, "content": message.content}
            for message in previous_messages
        ]
        user_msg = await self.message_repo.create(
            chat_id=chat_id,
            user_id=user_id,
            role="user",
            content=content,
            token_count=len(content.split()),
            created_at=datetime.now(timezone.utc),
        )

        full_ai_content = []
        async for chunk in AIService(
            self.db, company_id=chat.company_id, user_id=user_id
        ).chat_stream(
            provider=chat.ai_provider,
            model=chat.model,
            messages=history + [{"role": "user", "content": content}],
            system_prompt="Sen Nexora AI yordamchisisan. Foydalanuvchilarga o'zbek tilida javob ber.",
        ):
            full_ai_content.append(chunk)
            payload = json_module.dumps({"content": chunk, "done": False})
            yield f"data: {payload}\n\n"

        complete_text = "".join(full_ai_content)
        ai_msg = await self.message_repo.create(
            chat_id=chat_id,
            user_id=user_id,
            role="assistant",
            content=complete_text,
            token_count=len(complete_text.split()),
            created_at=max(
                datetime.now(timezone.utc),
                user_msg.created_at + timedelta(microseconds=1),
            ),
        )
        total_tokens = chat.token_count + user_msg.token_count + ai_msg.token_count
        await self.chat_repo.update(chat_id, token_count=total_tokens)

        done_payload = json_module.dumps({
            "content": "",
            "done": True,
            "ai_message_id": str(ai_msg.id),
        })
        yield f"data: {done_payload}\n\n"
        yield "data: [DONE]\n\n"

    async def get_chat_history(
        self, chat_id: uuid.UUID, user_id: uuid.UUID, page: int = 1, page_size: int = 50
    ) -> dict | None:
        if not await self.chat_repo.get_owned(chat_id, user_id):
            return None
        messages, total = await self.message_repo.get_by_chat(chat_id, page, page_size)
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [self._serialize_message(message) for message in messages],
        }

