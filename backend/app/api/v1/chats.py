import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_company_id, get_current_user, get_db
from app.models.user import User
from app.schemas.chat import (
    ChatCreate,
    ChatResponse,
    ChatUpdate,
    SendMessageRequest,
    SendMessageResponse,
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chats", tags=["Chats"])


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
    chat = await service.create_chat(
        company_id=company_id,
        user_id=current_user.id,
        title=body.title,
        ai_provider=body.ai_provider,
        model=body.model,
        agent_id=body.agent_id,
    )
    return ChatResponse(
        id=chat.id,
        title=chat.title,
        ai_provider=chat.ai_provider,
        model=chat.model,
        token_count=chat.token_count,
        is_archived=chat.is_archived,
        created_at=chat.created_at.isoformat(),
        message_count=0,
    )


@router.get("/{chat_id}/messages")
async def get_chat_messages(
    chat_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ChatService(db)
    return await service.get_chat_history(chat_id, page, page_size)


@router.post("/{chat_id}/messages", response_model=SendMessageResponse)
async def send_message(
    chat_id: uuid.UUID,
    body: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ChatService(db)
    result = await service.send_message(chat_id, current_user.id, body.content)
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
    db: AsyncSession = Depends(get_db),
):
    service = ChatService(db)
    chat = await service.chat_repo.update(chat_id, **body.model_dump(exclude_none=True))
    if not chat:
        raise HTTPException(status_code=404, detail="Chat topilmadi")
    return {"id": chat.id, "title": chat.title, "is_archived": chat.is_archived}


@router.delete("/{chat_id}")
async def delete_chat(
    chat_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    from app.repositories.chat_repo import ChatRepository

    repo = ChatRepository(db)
    result = await repo.soft_delete(chat_id)
    if not result:
        raise HTTPException(status_code=404, detail="Chat topilmadi")
    return {"message": "Chat o'chirildi"}
