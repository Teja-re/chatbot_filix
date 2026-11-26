from datetime import date
import pytest


@pytest.mark.anyio
async def test_full_chatbot_flow_back_and_book(client):
    login = await client.post(
        "/api/auth/login",
        json={"email": "demo@dinebot.com", "password": "demo1234"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # 1. Start session -> nearby restaurants appear
    sess = await client.get("/api/chat/session", headers=headers)
    assert sess.status_code == 200
    body = sess.json()
    assert body["state"] == "NEARBY_LIST"
    assert len(body["nearby_restaurants"]) >= 2

    first_rest = body["nearby_restaurants"][0]
    second_rest = body["nearby_restaurants"][1]

    # 2. Select first restaurant -> menu with nutrient values appears
    res = await client.post(
        "/api/chat/action",
        headers=headers,
        json={"action": "select_restaurant", "restaurant_id": first_rest["id"]},
    )
    assert res.status_code == 200
    menu_state = res.json()
    assert menu_state["state"] == "VIEWING_MENU"
    assert len(menu_state["menu_items"]) >= 3
    first_item = menu_state["menu_items"][0]
    assert first_item["calories_kcal"] > 0
    assert "protein_g" in first_item
    assert "carbs_g" in first_item
    assert "fat_g" in first_item
    assert "fiber_g" in first_item

    # 3. Go back and select a different restaurant
    back_res = await client.post(
        "/api/chat/action",
        headers=headers,
        json={"action": "go_back"},
    )
    assert back_res.status_code == 200
    assert back_res.json()["state"] == "NEARBY_LIST"

    res2 = await client.post(
        "/api/chat/action",
        headers=headers,
        json={"action": "select_restaurant", "restaurant_id": second_rest["id"]},
    )
    assert res2.status_code == 200
    second_menu = res2.json()
    assert second_menu["selected_restaurant"]["id"] == second_rest["id"]

    # Like a dish and proceed to book table
    liked_item_id = second_menu["menu_items"][0]["id"]
    like_res = await client.post(
        "/api/chat/action",
        headers=headers,
        json={"action": "toggle_like_item", "item_id": liked_item_id},
    )
    assert liked_item_id in like_res.json()["liked_item_ids"]

    start_book = await client.post(
        "/api/chat/action",
        headers=headers,
        json={"action": "start_booking"},
    )
    assert start_book.status_code == 200
    assert start_book.json()["state"] == "BOOKING_FORM"

    today = date.today().isoformat()
    confirm = await client.post(
        "/api/chat/action",
        headers=headers,
        json={
            "action": "confirm_booking",
            "booking_date": today,
            "time_slot": "19:00",
            "party_size": 4,
            "notes": "Window table",
        },
    )
    assert confirm.status_code == 200
    confirmed_data = confirm.json()
    assert confirmed_data["state"] == "CONFIRMED"
    assert confirmed_data["latest_booking"]["restaurant_id"] == second_rest["id"]
    assert "Liked dishes:" in confirmed_data["latest_booking"]["notes"]

    # Verify booking shows up in /api/bookings/my and can be cancelled
    my_bookings = await client.get("/api/bookings/my", headers=headers)
    assert len(my_bookings.json()) == 1
    booking_id = my_bookings.json()[0]["id"]

    cancel = await client.patch(f"/api/bookings/{booking_id}/cancel", headers=headers)
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "CANCELLED"


@pytest.mark.anyio
async def test_user_can_decline_without_booking(client):
    login = await client.post(
        "/api/auth/login",
        json={"email": "demo@dinebot.com", "password": "demo1234"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    sess = await client.get("/api/chat/session", headers=headers)
    rest_id = sess.json()["nearby_restaurants"][0]["id"]

    await client.post(
        "/api/chat/action",
        headers=headers,
        json={"action": "select_restaurant", "restaurant_id": rest_id},
    )

    declined = await client.post(
        "/api/chat/action",
        headers=headers,
        json={"action": "decline_booking"},
    )
    assert declined.status_code == 200
    assert declined.json()["state"] == "ENDED"

    my_bookings = await client.get("/api/bookings/my", headers=headers)
    assert my_bookings.json() == []
