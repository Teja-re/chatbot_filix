import aiosqlite
from fastapi import APIRouter, Depends

from app.database import get_db
from app.schemas import BookingCreate, BookingOut
from app.security import get_current_user
from app.services import booking_service

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


@router.post("", response_model=BookingOut, status_code=201)
async def create_booking(
    payload: BookingCreate,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    return await booking_service.create_booking(db, current_user["id"], payload)


@router.get("/my", response_model=list[BookingOut])
async def my_bookings(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    return await booking_service.list_user_bookings(db, current_user["id"])


@router.patch("/{booking_id}/cancel", response_model=BookingOut)
async def cancel_booking(
    booking_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    return await booking_service.cancel_booking(db, current_user["id"], booking_id)
