import asyncio
from datetime import date
import pytest


@pytest.mark.anyio
async def test_concurrent_bookings_do_not_overbook(client):
    login = await client.post(
        "/api/auth/login",
        json={"email": "demo@dinebot.com", "password": "demo1234"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # Find restaurant with smallest seat count (MacroPlate Bistro has 18 seats)
    nearby = (await client.get("/api/restaurants/nearby", headers=headers)).json()
    target = min(nearby, key=lambda r: r["total_seats"])
    rest_id = target["id"]
    seats = target["total_seats"]

    today = date.today().isoformat()
    # Try booking more than half the seats twice concurrently
    party = (seats // 2) + 2

    async def attempt_book():
        return await client.post(
            "/api/bookings",
            headers=headers,
            json={
                "restaurant_id": rest_id,
                "booking_date": today,
                "time_slot": "20:30",
                "party_size": party,
                "notes": "",
            },
        )

    res1, res2 = await asyncio.gather(attempt_book(), attempt_book())
    statuses = sorted([res1.status_code, res2.status_code])
    assert statuses == [201, 409]
