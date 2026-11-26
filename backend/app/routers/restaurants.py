import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.database import get_db
from app.schemas import MenuItemOut, RestaurantOut, SlotAvailabilityOut
from app.security import get_current_user
from app.services import booking_service, restaurant_service

router = APIRouter(prefix="/api/restaurants", tags=["restaurants"])


@router.get("/nearby", response_model=list[RestaurantOut])
async def nearby_restaurants(
    lat: float | None = Query(default=None, ge=-90, le=90),
    lon: float | None = Query(default=None, ge=-180, le=180),
    radius_km: float = Query(default=15.0, gt=0, le=200),
    limit: int = Query(default=20, ge=1, le=50),
    _: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    return await restaurant_service.get_nearby_restaurants(
        db, lat=lat, lon=lon, radius_km=radius_km, limit=limit
    )


@router.get("/{restaurant_id}/menu", response_model=list[MenuItemOut])
async def restaurant_menu(
    restaurant_id: int,
    response: Response,
    dietary: str | None = Query(default=None),
    max_calories: int | None = Query(default=None, gt=0),
    _: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    rest = await restaurant_service.get_restaurant_by_id(db, restaurant_id)
    if not rest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")

    response.headers["Cache-Control"] = "private, max-age=30"
    return await restaurant_service.get_restaurant_menu(
        db, restaurant_id, dietary=dietary, max_calories=max_calories
    )


@router.post("/{restaurant_id}/menu/enrich", response_model=list[MenuItemOut])
async def refresh_restaurant_menu_nutrition(
    restaurant_id: int,
    _: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    rest = await restaurant_service.get_restaurant_by_id(db, restaurant_id)
    if not rest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")
    return await restaurant_service.ensure_menu_enriched(db, restaurant_id, force=True)


@router.get("/{restaurant_id}/slots", response_model=list[SlotAvailabilityOut])
async def restaurant_slots(
    restaurant_id: int,
    booking_date: str = Query(pattern=r"^\d{4}-\d{2}-\d{2}$"),
    _: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    return await booking_service.get_slot_availability(db, restaurant_id, booking_date)
