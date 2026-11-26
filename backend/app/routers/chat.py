import aiosqlite
from fastapi import APIRouter, Depends, Query

from pydantic import BaseModel, Field

from app.database import get_db
from app.schemas import ChatActionRequest, ChatSessionOut
from app.security import get_current_user
from app.services import chatbot_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


class HealthRecommendRequest(BaseModel):
    goal: str = Field(default="balanced", min_length=1, max_length=120)
    lat: float | None = None
    lon: float | None = None


@router.get("/session", response_model=ChatSessionOut)
async def get_session(
    lat: float | None = Query(default=None, ge=-90, le=90),
    lon: float | None = Query(default=None, ge=-180, le=180),
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    return await chatbot_service.get_session(db, current_user, lat=lat, lon=lon)


@router.post("/action", response_model=ChatSessionOut)
async def chat_action(
    payload: ChatActionRequest,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    return await chatbot_service.handle_action(db, current_user, payload)


@router.post("/health-recommend", response_model=ChatSessionOut)
async def health_recommend(
    payload: HealthRecommendRequest,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    return await chatbot_service.handle_action(
        db,
        current_user,
        ChatActionRequest(
            action="recommend_healthy",
            goal=payload.goal,
            lat=payload.lat,
            lon=payload.lon,
        ),
    )
