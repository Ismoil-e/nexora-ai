from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login")
async def login():
    return {"message": "Login endpoint"}
