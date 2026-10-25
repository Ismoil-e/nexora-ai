import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_company_id, get_current_user, get_db
from app.models.user import User
from app.schemas.chat import (
    ChatCreate,
    ChatResponse,
    ChatUpdate,
    ImportChatHistoryRequest,
    SendMessageRequest,
    SendMessageResponse,
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chats", tags=["Chats"])


def _chat_response(chat, message_count: int = 0) -> ChatResponse:
    return ChatResponse(
        id=chat.id,
        title=chat.title,
        ai_provider=chat.ai_provider,
        model=chat.model,
        token_count=chat.token_count,
        is_archived=chat.is_archived,
        created_at=chat.created_at.isoformat(),
        message_count=message_count,
    )


@router.get("")
async def list_chats(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ChatService(db)
    return await service.get_user_chats(company_id, current_user.id, page, page_size)


@router.post("", response_model=ChatResponse)
async def create_chat(
    body: ChatCreate,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ChatService(db)
    chat = await service.get_or_create_persistent_chat(company_id, current_user.id)
    return _chat_response(chat, len(chat.messages) if chat.messages else 0)


@router.post("/persistent", response_model=ChatResponse)
async def get_or_create_persistent_chat(
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the user's single long-lived chat, creating it only once."""
    service = ChatService(db)
    chat = await service.get_or_create_persistent_chat(company_id, current_user.id)
    return _chat_response(chat, len(chat.messages) if chat.messages else 0)


@router.get("/{chat_id}/messages")
async def get_chat_messages(
    chat_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ChatService(db)
    result = await service.get_chat_history(chat_id, current_user.id, page, page_size)
    if result is None:
        raise HTTPException(status_code=404, detail="Chat topilmadi")
    return result


@router.post("/{chat_id}/history/import")
async def import_chat_history(
    chat_id: uuid.UUID,
    body: ImportChatHistoryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ChatService(db)
    result = await service.import_legacy_history(chat_id, current_user.id, body.messages)
    if result["imported"] == 0 and not result["already_exists"]:
        raise HTTPException(status_code=404, detail="Chat topilmadi")
    return result


@router.post("/{chat_id}/messages", response_model=SendMessageResponse)
async def send_message(
    chat_id: uuid.UUID,
    body: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ChatService(db)
    result = await service.send_message(
        chat_id,
        current_user.id,
        body.content,
        attachment_name=body.attachment_name,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Chat topilmadi")
    return result


@router.post("/{chat_id}/stream")
async def send_message_stream(
    chat_id: uuid.UUID,
    body: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import StreamingResponse

    service = ChatService(db)
    generator = service.send_message_stream(chat_id, current_user.id, body.content)
    return StreamingResponse(generator, media_type="text/event-stream")



@router.put("/{chat_id}")
async def update_chat(
    chat_id: uuid.UUID,
    body: ChatUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ChatService(db)
    if not await service.chat_repo.get_owned(chat_id, current_user.id):
        raise HTTPException(status_code=404, detail="Chat topilmadi")
    chat = await service.chat_repo.update(chat_id, **body.model_dump(exclude_none=True))
    if not chat:
        raise HTTPException(status_code=404, detail="Chat topilmadi")
    return {"id": chat.id, "title": chat.title, "is_archived": chat.is_archived}
