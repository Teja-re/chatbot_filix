from datetime import date, datetime, timezone
import json
import aiosqlite
from fastapi import HTTPException, status

from app.schemas import (
    BookingCreate,
    BookingDraftOut,
    BookingOut,
    ChatActionRequest,
    ChatMessageOut,
    ChatSessionOut,
    HealthRecommendationOut,
)
from app.services import booking_service, llm_service, restaurant_service

STATE_NEARBY = "NEARBY_LIST"
STATE_MENU = "VIEWING_MENU"
STATE_BOOKING = "BOOKING_FORM"
STATE_CONFIRMED = "CONFIRMED"
STATE_ENDED = "ENDED"

MAX_HISTORY = 30


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M")


def _append_msg(history: list[dict], sender: str, text: str) -> list[dict]:
    history.append({"sender": sender, "text": text, "timestamp": _now_iso()})
    return history[-MAX_HISTORY:]


def _quick_actions_for(state: str) -> list[str]:
    if state == STATE_NEARBY:
        return ["Healthy picks for me", "Refresh nearby", "No booking today"]
    if state == STATE_MENU:
        return ["Proceed to book table", "Back to restaurants", "No booking today"]
    if state == STATE_BOOKING:
        return ["Back to menu", "Back to restaurants", "No booking today"]
    if state == STATE_CONFIRMED:
        return ["Browse other restaurants"]
    return ["Browse nearby restaurants"]


async def _load_session_row(db: aiosqlite.Connection, user: dict) -> dict:
    cur = await db.execute(
        "SELECT * FROM chat_sessions WHERE user_id = ?",
        (user["id"],),
    )
    row = await cur.fetchone()
    if row:
        return dict(row)

    initial_history = _append_msg(
        [],
        "bot",
        f"Hi {user['name']}! Welcome to DineBot. Pick a nearby restaurant below, or tap a health goal so AI can recommend the best match.",
    )
    await db.execute(
        """
        INSERT INTO chat_sessions (user_id, state, selected_restaurant_id, liked_item_ids_json, history_json)
        VALUES (?, ?, NULL, '[]', ?)
        """,
        (user["id"], STATE_NEARBY, json.dumps(initial_history)),
    )
    await db.commit()
    cur = await db.execute("SELECT * FROM chat_sessions WHERE user_id = ?", (user["id"],))
    return dict(await cur.fetchone())


async def _save_session(
    db: aiosqlite.Connection,
    user_id: int,
    state: str,
    selected_restaurant_id: int | None,
    liked_ids: list[int],
    history: list[dict],
) -> None:
    await db.execute(
        """
        UPDATE chat_sessions
        SET state = ?,
            selected_restaurant_id = ?,
            liked_item_ids_json = ?,
            history_json = ?,
            updated_at = datetime('now')
        WHERE user_id = ?
        """,
        (state, selected_restaurant_id, json.dumps(liked_ids), json.dumps(history), user_id),
    )
    await db.commit()


async def _build_session_response(
    db: aiosqlite.Connection,
    row: dict,
    lat: float | None = None,
    lon: float | None = None,
    latest_booking: BookingOut | None = None,
    llm_provider: str | None = None,
    recommendations: list[HealthRecommendationOut] | None = None,
    health_goal: str | None = None,
    booking_draft: BookingDraftOut | None = None,
) -> ChatSessionOut:
    state = row["state"]
    selected_id = row["selected_restaurant_id"]
    liked_ids = json.loads(row["liked_item_ids_json"])
    history = [ChatMessageOut(**m) for m in json.loads(row["history_json"])]

    selected_rest = None
    nearby = []
    menu_items = []
    slots = []

    if state == STATE_NEARBY:
        nearby = await restaurant_service.get_nearby_restaurants(db, lat=lat, lon=lon)

    if selected_id is not None:
        selected_rest = await restaurant_service.get_restaurant_by_id(db, selected_id, lat=lat, lon=lon)
        if state in (STATE_MENU, STATE_BOOKING) and selected_rest:
            menu_items = await restaurant_service.ensure_menu_enriched(db, selected_id)
        if state == STATE_BOOKING and selected_rest:
            today = date.today().isoformat()
            slots = await booking_service.get_slot_availability(db, selected_id, today)

    provider = llm_provider or await llm_service.get_provider_status()

    return ChatSessionOut(
        state=state,
        selected_restaurant=selected_rest,
        liked_item_ids=liked_ids,
        messages=history,
        nearby_restaurants=nearby,
        menu_items=menu_items,
        slots=slots,
        latest_booking=latest_booking,
        recommendations=recommendations or [],
        health_goal=health_goal,
        booking_draft=booking_draft,
        quick_actions=_quick_actions_for(state),
        llm_provider=provider,
    )


async def get_session(
    db: aiosqlite.Connection,
    user: dict,
    lat: float | None = None,
    lon: float | None = None,
) -> ChatSessionOut:
    row = await _load_session_row(db, user)
    return await _build_session_response(db, row, lat=lat, lon=lon)


async def handle_action(
    db: aiosqlite.Connection,
    user: dict,
    req: ChatActionRequest,
) -> ChatSessionOut:
    row = await _load_session_row(db, user)
    state = row["state"]
    selected_id = row["selected_restaurant_id"]
    liked_ids: list[int] = json.loads(row["liked_item_ids_json"])
    history: list[dict] = json.loads(row["history_json"])

    latest_booking: BookingOut | None = None
    recommendations: list[HealthRecommendationOut] = []
    health_goal: str | None = None
    booking_draft: BookingDraftOut | None = None
    llm_reply: str | None = None
    llm_provider: str | None = None

    action = req.action
    if action == "message" and req.text:
        user_text = req.text.strip()
        history = _append_msg(history, "user", user_text)

        nearby_ctx = await restaurant_service.get_nearby_restaurants(db, lat=req.lat, lon=req.lon)
        nearby_with_menus = await restaurant_service.get_restaurants_with_menus(db, nearby_ctx)
        selected_ctx = (
            await restaurant_service.get_restaurant_by_id(db, selected_id, lat=req.lat, lon=req.lon)
            if selected_id is not None
            else None
        )
        menu_ctx = (
            await restaurant_service.get_restaurant_menu(db, selected_id)
            if selected_id is not None
            else []
        )
        slots_ctx = (
            await booking_service.get_slot_availability(db, selected_id, date.today().isoformat())
            if selected_id is not None
            else []
        )

        llm_result = await llm_service.interpret_message(
            state=state,
            user_name=user["name"],
            text=user_text,
            nearby=nearby_ctx,
            selected_restaurant=selected_ctx,
            menu_items=menu_ctx,
            slots=slots_ctx,
            recent_messages=history[:-1],
            nearby_with_menus=nearby_with_menus,
        )
        llm_provider = llm_result["provider"]
        llm_reply = llm_result.get("reply")
        action = llm_result["action"]

        if req.restaurant_id is None and llm_result.get("restaurant_id") is not None:
            req.restaurant_id = llm_result["restaurant_id"]
        if req.item_id is None and llm_result.get("item_id") is not None:
            req.item_id = llm_result["item_id"]
        if req.goal is None and llm_result.get("goal"):
            req.goal = llm_result["goal"]
        if req.booking_date is None and llm_result.get("booking_date"):
            req.booking_date = llm_result["booking_date"]
        if req.time_slot is None and llm_result.get("time_slot"):
            req.time_slot = llm_result["time_slot"]
        if req.party_size is None and llm_result.get("party_size") is not None:
            req.party_size = llm_result["party_size"]
        if req.notes is None and llm_result.get("notes"):
            req.notes = llm_result["notes"]

    if action == "recommend_healthy":
        goal = (req.goal or "balanced").strip()
        if goal.lower() == "clear":
            state = STATE_NEARBY
            selected_id = None
            liked_ids = []
            recommendations = []
            health_goal = None
        else:
            state = STATE_NEARBY
            selected_id = None
            liked_ids = []
            nearby = await restaurant_service.get_nearby_restaurants(db, lat=req.lat, lon=req.lon)
            rest_with_menus = await restaurant_service.get_restaurants_with_menus(db, nearby)
            rec_reply, recommendations, rec_provider = await llm_service.recommend_healthy_restaurants(
                goal, rest_with_menus
            )
            llm_provider = rec_provider
            health_goal = goal
            history = _append_msg(history, "bot", rec_reply)

    elif action == "stay":
        if state == STATE_BOOKING and any([req.booking_date, req.time_slot, req.party_size, req.notes]):
            booking_draft = BookingDraftOut(
                booking_date=req.booking_date,
                time_slot=req.time_slot,
                party_size=req.party_size,
                notes=req.notes,
            )
        history = _append_msg(
            history,
            "bot",
            llm_reply or "Ask me about healthy restaurants, dish ingredients, combos, or tap an option below.",
        )

    elif action in ("show_nearby", "restart"):
        state = STATE_NEARBY
        selected_id = None
        liked_ids = []
        history = _append_msg(
            history,
            "bot",
            llm_reply or "Here is the nearby restaurants list. Pick one or choose a health goal for AI suggestions.",
        )

    elif action == "select_restaurant":
        if not req.restaurant_id:
            state = STATE_NEARBY
            history = _append_msg(
                history,
                "bot",
                llm_reply or "Please select one of the nearby restaurants below.",
            )
        else:
            rest = await restaurant_service.get_restaurant_by_id(db, req.restaurant_id, lat=req.lat, lon=req.lon)
            if not rest:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")
            state = STATE_MENU
            selected_id = rest.id
            liked_ids = []
            await restaurant_service.ensure_menu_enriched(db, rest.id)
            history = _append_msg(
                history,
                "bot",
                llm_reply
                or f"Showing {rest.name} ({rest.cuisine}). Review the AI-fetched ingredients & nutrient values below, like dishes you enjoy, or go back to pick another restaurant.",
            )

    elif action == "toggle_like_item":
        if not req.item_id:
            history = _append_msg(history, "bot", llm_reply or "Tap Like on any dish card to save it.")
        else:
            if req.item_id in liked_ids:
                liked_ids.remove(req.item_id)
            else:
                liked_ids.append(req.item_id)
            if llm_reply:
                history = _append_msg(history, "bot", llm_reply)

    elif action == "go_back":
        if state == STATE_BOOKING and selected_id is not None:
            state = STATE_MENU
            history = _append_msg(
                history,
                "bot",
                llm_reply or "Back to the menu. Feel free to review dishes or pick another restaurant.",
            )
        else:
            state = STATE_NEARBY
            selected_id = None
            liked_ids = []
            history = _append_msg(
                history,
                "bot",
                llm_reply or "No problem — pick another nearby restaurant from the list.",
            )

    elif action == "start_booking":
        if selected_id is None:
            state = STATE_NEARBY
            history = _append_msg(history, "bot", llm_reply or "Please select a restaurant first before booking a table.")
        else:
            state = STATE_BOOKING
            if any([req.booking_date, req.time_slot, req.party_size, req.notes]):
                booking_draft = BookingDraftOut(
                    booking_date=req.booking_date,
                    time_slot=req.time_slot,
                    party_size=req.party_size,
                    notes=req.notes,
                )
            history = _append_msg(
                history,
                "bot",
                llm_reply or "Great choice! Pick a date, time slot, and party size to reserve your table.",
            )

    elif action == "confirm_booking":
        if selected_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No restaurant selected")
        if not req.booking_date or not req.time_slot or not req.party_size:
            state = STATE_BOOKING
            booking_draft = BookingDraftOut(
                booking_date=req.booking_date,
                time_slot=req.time_slot,
                party_size=req.party_size,
                notes=req.notes,
            )
            history = _append_msg(
                history,
                "bot",
                "Please choose a date, time slot, and guest count below to confirm your table.",
            )
        else:
            note_parts = []
            if req.notes:
                note_parts.append(req.notes.strip())
            macro_note = ""
            if liked_ids:
                menu = await restaurant_service.get_restaurant_menu(db, selected_id)
                liked_items = [m for m in menu if m.id in liked_ids]
                if liked_items:
                    total_kcal = sum(m.calories_kcal for m in liked_items)
                    total_prot = round(sum(m.protein_g for m in liked_items), 1)
                    liked_names = ", ".join(m.name for m in liked_items)
                    macro_note = f" ({total_kcal} kcal, {total_prot}g protein total)"
                    note_parts.append(f"Liked dishes: {liked_names}{macro_note}")

            latest_booking = await booking_service.create_booking(
                db,
                user["id"],
                BookingCreate(
                    restaurant_id=selected_id,
                    booking_date=req.booking_date,
                    time_slot=req.time_slot,
                    party_size=req.party_size,
                    notes=" | ".join(note_parts),
                ),
            )
            state = STATE_CONFIRMED
            history = _append_msg(
                history,
                "bot",
                f"Table confirmed at {latest_booking.restaurant_name} on {latest_booking.booking_date} at {latest_booking.time_slot} for {latest_booking.party_size} guests. Booking code: {latest_booking.booking_code}.{macro_note}",
            )

    elif action == "decline_booking":
        state = STATE_ENDED
        selected_id = None
        liked_ids = []
        history = _append_msg(
            history,
            "bot",
            llm_reply
            or "Alright, no table was booked. Whenever you feel like dining out, tap 'Browse Nearby Restaurants' to start again.",
        )

    else:
        history = _append_msg(
            history,
            "bot",
            "Use the buttons below or type 'back', 'book', 'nearby', or 'no thanks' to continue.",
        )

    await _save_session(db, user["id"], state, selected_id, liked_ids, history)
    updated_row = await _load_session_row(db, user)
    return await _build_session_response(
        db,
        updated_row,
        lat=req.lat,
        lon=req.lon,
        latest_booking=latest_booking,
        llm_provider=llm_provider,
        recommendations=recommendations,
        health_goal=health_goal,
        booking_draft=booking_draft,
    )
