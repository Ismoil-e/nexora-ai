from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me")
async def get_me():
    return {"user": "me"}
