import secrets
import aiosqlite
from fastapi import HTTPException, status

from app import config
from app.schemas import BookingCreate, BookingOut, SlotAvailabilityOut


def _generate_booking_code() -> str:
    return f"BK-{secrets.token_hex(3).upper()}"


async def get_slot_availability(
    db: aiosqlite.Connection,
    restaurant_id: int,
    booking_date: str,
) -> list[SlotAvailabilityOut]:
    cur = await db.execute(
        "SELECT total_seats FROM restaurants WHERE id = ?",
        (restaurant_id,),
    )
    rest = await cur.fetchone()
    if not rest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")

    total_seats = rest["total_seats"]
    cur = await db.execute(
        """
        SELECT time_slot, COALESCE(SUM(party_size), 0) AS booked_seats
        FROM bookings
        WHERE restaurant_id = ? AND booking_date = ? AND status = 'CONFIRMED'
        GROUP BY time_slot
        """,
        (restaurant_id, booking_date),
    )
    booked_by_slot = {row["time_slot"]: row["booked_seats"] for row in await cur.fetchall()}

    return [
        SlotAvailabilityOut(
            time_slot=slot,
            available_seats=max(0, total_seats - booked_by_slot.get(slot, 0)),
        )
        for slot in config.DEFAULT_TIME_SLOTS
    ]


async def create_booking(
    db: aiosqlite.Connection,
    user_id: int,
    payload: BookingCreate,
) -> BookingOut:
    # Ensure no prior implicit read transaction is open before acquiring the SQLite write lock
    if db.in_transaction:
        await db.commit()

    await db.execute("BEGIN IMMEDIATE")
    try:
        cur = await db.execute(
            "SELECT id, name, total_seats FROM restaurants WHERE id = ?",
            (payload.restaurant_id,),
        )
        rest = await cur.fetchone()
        if not rest:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")

        total_seats = rest["total_seats"]
        cur = await db.execute(
            """
            SELECT COALESCE(SUM(party_size), 0) AS booked
            FROM bookings
            WHERE restaurant_id = ? AND booking_date = ? AND time_slot = ? AND status = 'CONFIRMED'
            """,
            (payload.restaurant_id, payload.booking_date, payload.time_slot),
        )
        booked = (await cur.fetchone())["booked"]
        remaining = total_seats - booked

        if payload.party_size > remaining:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Only {max(0, remaining)} seats left for {payload.time_slot} on {payload.booking_date}",
            )

        code = _generate_booking_code()
        cur = await db.execute(
            """
            INSERT INTO bookings (booking_code, user_id, restaurant_id, booking_date, time_slot, party_size, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, 'CONFIRMED', ?)
            """,
            (
                code,
                user_id,
                payload.restaurant_id,
                payload.booking_date,
                payload.time_slot,
                payload.party_size,
                payload.notes.strip(),
            ),
        )
        booking_id = cur.lastrowid
        await db.commit()

        cur = await db.execute(
            """
            SELECT b.id, b.booking_code, b.restaurant_id, r.name AS restaurant_name,
                   b.booking_date, b.time_slot, b.party_size, b.status, b.notes, b.created_at
            FROM bookings b
            JOIN restaurants r ON r.id = b.restaurant_id
            WHERE b.id = ?
            """,
            (booking_id,),
        )
        return BookingOut(**dict(await cur.fetchone()))
    except Exception:
        if db.in_transaction:
            await db.rollback()
        raise


async def list_user_bookings(db: aiosqlite.Connection, user_id: int) -> list[BookingOut]:
    cur = await db.execute(
        """
        SELECT b.id, b.booking_code, b.restaurant_id, r.name AS restaurant_name,
               b.booking_date, b.time_slot, b.party_size, b.status, b.notes, b.created_at
        FROM bookings b
        JOIN restaurants r ON r.id = b.restaurant_id
        WHERE b.user_id = ?
        ORDER BY b.created_at DESC, b.id DESC
        """,
        (user_id,),
    )
    return [BookingOut(**dict(row)) for row in await cur.fetchall()]


async def cancel_booking(db: aiosqlite.Connection, user_id: int, booking_id: int) -> BookingOut:
    cur = await db.execute(
        "SELECT id, user_id, status FROM bookings WHERE id = ?",
        (booking_id,),
    )
    row = await cur.fetchone()
    if not row or row["user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    if row["status"] != "CANCELLED":
        await db.execute(
            "UPDATE bookings SET status = 'CANCELLED' WHERE id = ?",
            (booking_id,),
        )
        await db.commit()

    cur = await db.execute(
        """
        SELECT b.id, b.booking_code, b.restaurant_id, r.name AS restaurant_name,
               b.booking_date, b.time_slot, b.party_size, b.status, b.notes, b.created_at
        FROM bookings b
        JOIN restaurants r ON r.id = b.restaurant_id
        WHERE b.id = ?
        """,
        (booking_id,),
    )
    return BookingOut(**dict(await cur.fetchone()))
