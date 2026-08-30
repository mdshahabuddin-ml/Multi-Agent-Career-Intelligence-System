from fastapi import APIRouter
from sqlalchemy import text

from backend.config import settings
from backend.database import get_db

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/")
async def health_check():
    return {"status": "healthy", "service": "careerintel-backend"}


@router.get("/db")
async def db_health_check():
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}