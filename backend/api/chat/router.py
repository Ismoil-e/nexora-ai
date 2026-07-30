from fastapi import APIRouter

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get("/")
async def get_chats():
    return {"chats": []}
