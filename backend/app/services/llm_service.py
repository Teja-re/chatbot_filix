from datetime import date
import json
import re
import time
import httpx

from app import config
from app.schemas import (
    HealthRecommendationOut,
    MenuItemOut,
    RestaurantOut,
    SlotAvailabilityOut,
)

ALLOWED_ACTIONS = {
    "stay",
    "show_nearby",
    "recommend_healthy",
    "select_restaurant",
    "toggle_like_item",
    "go_back",
    "start_booking",
    "confirm_booking",
    "decline_booking",
}

_status_cache: tuple[float, str] = (0.0, "fallback")
_health_cache: dict[tuple[str, tuple[int, ...]], tuple[float, str, list[HealthRecommendationOut], str]] = {}

_GREETING_PHRASES = {
    "hi",
    "hii",
    "hello",
    "hey",
    "heyy",
    "hiya",
    "howdy",
    "good morning",
    "good afternoon",
    "good evening",
    "how are you",
    "whats up",
    "what is up",
}
_COURTESY_PHRASES = {"thanks", "thank you", "thx", "ty", "ok", "okay", "cool", "great", "awesome", "nice"}
_GOODBYE_PHRASES = ("bye", "goodbye", "see you", "catch you later", "no thanks", "not now", "no booking", "skip", "exit", "maybe later", "don't book")


def clear_health_cache() -> None:
    _health_cache.clear()


def _extract_json(raw: str) -> dict:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(line for line in lines if not line.strip().startswith("```")).strip()
    return json.loads(cleaned)


def _compact_json(data: object) -> str:
    return json.dumps(data, separators=(",", ":"))


async def _call_chat_completion(messages: list[dict], max_tokens: int) -> tuple[str, str]:
    """Call OpenRouter first when configured; otherwise try local Ollama."""
    if config.OPENROUTER_API_KEY:
        headers = {
            "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": "DineBot",
        }
        payload = {
            "model": config.OPENROUTER_MODEL,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        print("\n[OpenRouter Request]", flush=True)
        print(f"Model: {config.OPENROUTER_MODEL} | max_tokens={max_tokens}", flush=True)
        for msg in messages:
            print(f"  [{msg['role']}]: {msg['content']}", flush=True)

        async with httpx.AsyncClient(timeout=config.OPENROUTER_TIMEOUT_SECONDS) as client:
            res = await client.post(
                f"{config.OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
            )
            res.raise_for_status()
            body = res.json()
            content = body["choices"][0]["message"]["content"]
            usage = body.get("usage") or {}
            print("[OpenRouter Response]", flush=True)
            print(f"  Output: {content}", flush=True)
            print(
                f"  Tokens -> prompt: {usage.get('prompt_tokens', 'N/A')}, "
                f"completion: {usage.get('completion_tokens', 'N/A')}, "
                f"total: {usage.get('total_tokens', 'N/A')}\n",
                flush=True,
            )
            return content, "openrouter"

    async with httpx.AsyncClient(timeout=config.OLLAMA_TIMEOUT_SECONDS) as client:
        res = await client.post(
            f"{config.OLLAMA_BASE_URL}/api/chat",
            json={
                "model": config.OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "format": "json",
            },
        )
        res.raise_for_status()
        body = res.json()
        return body.get("message", {}).get("content", ""), "ollama"


async def get_provider_status() -> str:
    global _status_cache
    if config.OPENROUTER_API_KEY:
        return "openrouter"

    now = time.monotonic()
    if _status_cache[0] > now:
        return _status_cache[1]

    status_val = "fallback"
    try:
        async with httpx.AsyncClient(timeout=0.35) as client:
            res = await client.get(f"{config.OLLAMA_BASE_URL}/api/tags")
            if res.status_code == 200:
                status_val = "ollama"
    except httpx.HTTPError:
        status_val = "fallback"

    _status_cache = (now + 15.0, status_val)
    return status_val


async def enrich_menu_nutrition(
    restaurant_name: str,
    cuisine: str,
    items: list[MenuItemOut],
) -> tuple[dict[int, dict], str]:
    """Fetch ingredients, nutrients, allergens, and health notes in one batched LLM call."""
    if not items:
        return {}, "fallback"

    compact_dishes = [{"id": m.id, "n": m.name, "d": m.description[:70]} for m in items]
    prompt = (
        f"Restaurant: {restaurant_name} ({cuisine}).\n"
        'Return strict JSON {"items":[{"id":int,"ingredients":[str],'
        '"calories_kcal":int,"protein_g":float,"carbs_g":float,"fat_g":float,"fiber_g":float,'
        '"dietary_tags":[str],"allergens":[str],"health_note":str}]}.\n'
        "Give 4-6 concise ingredients, realistic per-serving macros, common allergens (if any), and a <=5 word health_note.\n"
        f"Dishes:{_compact_json(compact_dishes)}"
    )

    try:
        raw, provider = await _call_chat_completion(
            [{"role": "user", "content": prompt}],
            max_tokens=700,
        )
        parsed = _extract_json(raw)
        enriched: dict[int, dict] = {}
        for entry in parsed.get("items", []):
            item_id = entry.get("id")
            if item_id is None:
                continue
            enriched[int(item_id)] = {
                "ingredients": [str(x).strip() for x in entry.get("ingredients", []) if str(x).strip()][:8],
                "calories_kcal": max(30, min(2500, int(round(float(entry.get("calories_kcal", 350)))))),
                "protein_g": max(0.0, round(float(entry.get("protein_g", 12.0)), 1)),
                "carbs_g": max(0.0, round(float(entry.get("carbs_g", 30.0)), 1)),
                "fat_g": max(0.0, round(float(entry.get("fat_g", 10.0)), 1)),
                "fiber_g": max(0.0, round(float(entry.get("fiber_g", 4.0)), 1)),
                "dietary_tags": [str(t).strip() for t in entry.get("dietary_tags", []) if str(t).strip()][:5],
                "allergens": [str(a).strip() for a in entry.get("allergens", []) if str(a).strip()][:4],
                "health_note": str(entry.get("health_note", "")).strip()[:60],
            }
        return enriched, f"{provider}_llm"
    except (httpx.HTTPError, ValueError, TypeError, KeyError, IndexError) as exc:
        print(f"[OpenRouter Error -> Fallback] {type(exc).__name__}: {exc}", flush=True)
        return {}, "fallback"


def _fallback_health_recommend(
    goal: str,
    restaurants_with_menus: list[tuple[RestaurantOut, list[MenuItemOut]]],
) -> tuple[str, list[HealthRecommendationOut]]:
    g = goal.strip().lower()
    scored: list[tuple[float, RestaurantOut, list[str], str]] = []

    for rest, items in restaurants_with_menus:
        if not items:
            continue
        if "protein" in g or "muscle" in g:
            top = sorted(items, key=lambda m: m.protein_g, reverse=True)
            score = top[0].protein_g
            reason = f"Top dish {top[0].name} packs {top[0].protein_g}g protein."
            badge = "High-Protein Pick"
        elif "low" in g or "cal" in g or "weight" in g or "light" in g:
            top = sorted(items, key=lambda m: m.calories_kcal)
            score = -float(top[0].calories_kcal)
            reason = f"Light options starting at {top[0].calories_kcal} kcal ({top[0].name})."
            badge = "Low-Calorie Pick"
        elif "vegan" in g or "plant" in g or "veg" in g:
            veg_items = [m for m in items if any(t.lower() in ("vegan", "veg") for t in m.dietary_tags)]
            if not veg_items:
                continue
            top = sorted(veg_items, key=lambda m: m.fiber_g, reverse=True)
            score = float(len(veg_items) * 10) + top[0].fiber_g
            reason = f"{len(veg_items)} plant-friendly options including {top[0].name}."
            badge = "Plant-Rich Pick"
        else:
            top = sorted(items, key=lambda m: (m.fiber_g * 2 + m.protein_g - m.calories_kcal / 50.0), reverse=True)
            score = top[0].fiber_g * 2 + top[0].protein_g
            reason = f"Balanced macros led by {top[0].name} ({top[0].fiber_g}g fiber, {top[0].protein_g}g protein)."
            badge = "Healthy Balance"

        scored.append((score, rest, [m.name for m in top[:2]], reason + f"||{badge}"))

    scored.sort(key=lambda row: row[0], reverse=True)
    picks = scored[:3]
    recs = [
        HealthRecommendationOut(
            restaurant_id=rest.id,
            badge=msg.split("||")[1],
            reason=msg.split("||")[0],
            recommended_dishes=dishes,
        )
        for _, rest, dishes, msg in picks
    ]
    if not recs:
        return "No specific health matches found; browse any nearby restaurant below.", []
    names = ", ".join(r.name for _, r, _, _ in picks)
    return f"Top healthy picks for '{goal}': {names}. Tap a highlighted card below to check full macros.", recs


async def recommend_healthy_restaurants(
    goal: str,
    restaurants_with_menus: list[tuple[RestaurantOut, list[MenuItemOut]]],
) -> tuple[str, list[HealthRecommendationOut], str]:
    """Rank nearby restaurants for a health goal using their menu macros (cached 5 min)."""
    norm_goal = goal.strip().lower() or "balanced"
    rest_ids = tuple(r.id for r, _ in restaurants_with_menus)
    cache_key = (norm_goal, rest_ids)
    now = time.monotonic()

    cached = _health_cache.get(cache_key)
    if cached and cached[0] > now:
        return cached[1], cached[2], cached[3]

    compact_catalog = [
        {
            "id": r.id,
            "n": r.name,
            "c": r.cuisine,
            "dishes": [
                {
                    "n": m.name,
                    "kcal": m.calories_kcal,
                    "p": m.protein_g,
                    "fib": m.fiber_g,
                    "tags": m.dietary_tags,
                }
                for m in items
            ],
        }
        for r, items in restaurants_with_menus[:8]
    ]

    prompt = (
        f"User health goal: {goal}.\n"
        "Pick the 2-3 healthiest matching restaurants using ONLY the dish macros provided in Catalog.\n"
        "NEVER invent dishes or restaurants outside Catalog.\n"
        'Return strict JSON: {"reply":str,"recommendations":[{"restaurant_id":int,"badge":str,"reason":str,"recommended_dishes":[str]}]}.\n'
        "Keep badge <=3 words, reason <=14 words, reply <=2 sentences.\n"
        f"Catalog:{_compact_json(compact_catalog)}"
    )

    valid_ids = set(rest_ids)
    try:
        raw, provider = await _call_chat_completion(
            [{"role": "user", "content": prompt}],
            max_tokens=280,
        )
        parsed = _extract_json(raw)
        recs: list[HealthRecommendationOut] = []
        for entry in parsed.get("recommendations", []):
            rid = entry.get("restaurant_id")
            if rid is None or int(rid) not in valid_ids:
                continue
            recs.append(
                HealthRecommendationOut(
                    restaurant_id=int(rid),
                    badge=str(entry.get("badge", "Health Pick")).strip()[:28],
                    reason=str(entry.get("reason", "")).strip()[:120],
                    recommended_dishes=[str(d).strip() for d in entry.get("recommended_dishes", []) if str(d).strip()][:2],
                )
            )
        if recs:
            reply = str(parsed.get("reply", "")).strip() or "Here are the healthiest nearby matches based on dish nutrition."
            if len(_health_cache) > 64:
                _health_cache.clear()
            _health_cache[cache_key] = (now + 300.0, reply, recs, provider)
            return reply, recs, provider
    except (httpx.HTTPError, ValueError, TypeError, KeyError, IndexError) as exc:
        print(f"[OpenRouter Error -> Fallback] {type(exc).__name__}: {exc}", flush=True)
        pass

    reply, recs = _fallback_health_recommend(goal, restaurants_with_menus)
    return reply, recs, "fallback"


def _match_greeting_or_courtesy(text: str, user_name: str, state: str) -> str | None:
    cleaned = re.sub(r"[^a-z0-9\s]", "", text.lower()).strip()
    if not cleaned:
        return None

    if cleaned in _GREETING_PHRASES:
        if state == "VIEWING_MENU":
            return f"Hey {user_name}! You're checking out the menu right now — ask me about any dish's ingredients, calories, or protein, or tap Proceed to Book Table."
        if state == "BOOKING_FORM":
            return f"Hey {user_name}! Tell me your preferred date, time slot, and party size, or use the booking card below."
        return f"Hey {user_name}! How can I help today? Ask me for high-protein or low-calorie dishes nearby, or pick any restaurant below."

    if cleaned in _COURTESY_PHRASES:
        if state == "VIEWING_MENU":
            return f"You're welcome, {user_name}! Ready to book a table, or want to check another nearby restaurant?"
        if state == "CONFIRMED":
            return f"Happy to help, {user_name}! Enjoy your meal — let me know anytime if you want to browse more restaurants."
        return f"Anytime, {user_name}! Let me know what kind of food or health goal you're in the mood for."

    if cleaned in ("help", "what can you do", "menu help"):
        return (
            f"{user_name}, I can suggest the best nearby dishes for your protein or calorie goals, "
            "show ingredients and allergens, build meal combos, and reserve a table."
        )
    return None


def _build_system_prompt(
    state: str,
    user_name: str,
    nearby: list[RestaurantOut],
    selected_restaurant: RestaurantOut | None,
    menu_items: list[MenuItemOut],
    slots: list[SlotAvailabilityOut],
    nearby_with_menus: list[tuple[RestaurantOut, list[MenuItemOut]]],
) -> str:
    if selected_restaurant and menu_items:
        ctx = {
            "user": user_name,
            "st": state,
            "dt": date.today().isoformat(),
            "sel": {"id": selected_restaurant.id, "n": selected_restaurant.name, "c": selected_restaurant.cuisine},
            "menu": [
                {
                    "id": m.id,
                    "n": m.name,
                    "kcal": m.calories_kcal,
                    "p": m.protein_g,
                    "c": m.carbs_g,
                    "f": m.fat_g,
                    "fib": m.fiber_g,
                    "ing": m.ingredients[:5],
                    "alg": m.allergens,
                    "tags": m.dietary_tags,
                }
                for m in menu_items
            ],
            "slots": [{"t": s.time_slot, "left": s.available_seats} for s in slots],
            "other_rest": [{"id": r.id, "n": r.name, "c": r.cuisine} for r in nearby[:6] if r.id != selected_restaurant.id],
        }
    else:
        ctx = {
            "user": user_name,
            "st": state,
            "dt": date.today().isoformat(),
            "catalog": [
                {
                    "id": r.id,
                    "n": r.name,
                    "c": r.cuisine,
                    "km": r.distance_km,
                    "dishes": [
                        {
                            "n": m.name,
                            "kcal": m.calories_kcal,
                            "p": m.protein_g,
                            "fib": m.fiber_g,
                            "tags": m.dietary_tags,
                        }
                        for m in items
                    ],
                }
                for r, items in nearby_with_menus[:8]
            ],
        }

    return (
        "You are DineBot, a warm, conversational WhatsApp restaurant & nutrition concierge.\n"
        "STRICT GROUNDING RULE: You may ONLY recommend, name, or quote restaurants, dishes, ingredients, "
        "allergens, macros, and time slots that exist verbatim in Ctx JSON. "
        "NEVER invent dishes or restaurants from general knowledge. "
        "When the user asks for a dish (e.g. high protein, low calorie, vegan), name exact matching dish(es) "
        "AND their restaurant from Ctx with exact numbers.\n"
        'Return strict JSON: {"reply":str,"action":str,"restaurant_id":int|null,'
        '"item_id":int|null,"goal":str|null,"booking_date":str|null,"time_slot":str|null,"party_size":int|null,"notes":str|null}.\n'
        "Actions: stay, show_nearby, recommend_healthy, select_restaurant, toggle_like_item, go_back, "
        "start_booking, confirm_booking, decline_booking.\n"
        "Use 'stay' for conversational chat, greetings, dish suggestions, or nutrition Q&A. "
        "Use 'select_restaurant' only if the user explicitly asks to open/view a specific restaurant. "
        "Use 'decline_booking' for goodbyes ('bye', 'not today'). Keep reply warm and under 2-3 sentences.\n"
        f"Ctx:{_compact_json(ctx)}"
    )


def _search_catalog_dishes(
    q: str,
    nearby_with_menus: list[tuple[RestaurantOut, list[MenuItemOut]]],
) -> str | None:
    all_pairs = [(rest, item) for rest, items in nearby_with_menus for item in items]
    if not all_pairs:
        return None

    if "protein" in q or "muscle" in q or "gym" in q or "workout" in q:
        top = sorted(all_pairs, key=lambda pair: pair[1].protein_g, reverse=True)[:2]
        picks = "; ".join(
            f"{item.name} at {rest.name} ({item.protein_g}g protein, {item.calories_kcal} kcal)"
            for rest, item in top
        )
        return f"Best high-protein dishes nearby: {picks}. Tap a restaurant below to open its menu."

    if any(w in q for w in ("low", "light", "diet", "calorie", "kcal", "weight")):
        top = sorted(all_pairs, key=lambda pair: pair[1].calories_kcal)[:2]
        picks = "; ".join(
            f"{item.name} at {rest.name} ({item.calories_kcal} kcal, {item.protein_g}g protein)"
            for rest, item in top
        )
        return f"Lightest dishes nearby: {picks}."

    if "vegan" in q:
        vegans = [
            (rest, item)
            for rest, item in all_pairs
            if any(t.lower() == "vegan" for t in item.dietary_tags)
        ][:3]
        if vegans:
            picks = "; ".join(f"{item.name} at {rest.name} ({item.calories_kcal} kcal)" for rest, item in vegans)
            return f"Vegan dishes available nearby: {picks}."
        return "No strictly vegan dishes found in the nearby list."

    if "fiber" in q or "healthy" in q or "good dish" in q or "suggest" in q:
        top = sorted(all_pairs, key=lambda pair: (pair[1].fiber_g * 2 + pair[1].protein_g), reverse=True)[:2]
        picks = "; ".join(
            f"{item.name} at {rest.name} ({item.protein_g}g protein, {item.fiber_g}g fiber, {item.calories_kcal} kcal)"
            for rest, item in top
        )
        return f"Top healthy dishes nearby: {picks}."

    return None


def _fallback_interpret(
    state: str,
    user_name: str,
    text: str,
    nearby: list[RestaurantOut],
    selected_restaurant: RestaurantOut | None,
    menu_items: list[MenuItemOut],
    nearby_with_menus: list[tuple[RestaurantOut, list[MenuItemOut]]],
) -> dict:
    q = text.strip().lower()

    if any(re.search(rf"\b{re.escape(w)}\b", q) for w in _GOODBYE_PHRASES):
        return {"provider": "fallback", "action": "decline_booking", "reply": f"Goodbye {user_name}! No booking was made — come back anytime."}

    if any(re.search(rf"\b{re.escape(w)}\b", q) for w in ("other restaurant", "another restaurant", "restaurants", "nearby", "start over", "restart")):
        return {"provider": "fallback", "action": "show_nearby", "reply": None}

    if re.search(r"\b(back|previous)\b", q):
        return {"provider": "fallback", "action": "go_back", "reply": None}

    if re.search(r"\b(book|reserve|table|proceed)\b", q):
        return {"provider": "fallback", "action": "start_booking", "reply": None}

    if menu_items and any(w in q for w in ("combo", "meal", "ingredient", "allergen", "protein", "calorie", "kcal", "carb", "fat", "fiber", "healthy", "vegan", "veg")):
        if "combo" in q or "meal" in q:
            sorted_items = sorted(menu_items, key=lambda m: m.calories_kcal)
            if len(sorted_items) >= 2:
                a, b = sorted_items[0], sorted_items[1]
                return {
                    "provider": "fallback",
                    "action": "stay",
                    "reply": f"Light combo at {selected_restaurant.name}: {a.name} + {b.name} = {a.calories_kcal + b.calories_kcal} kcal, {round(a.protein_g + b.protein_g, 1)}g protein.",
                }
        if "ingredient" in q:
            first = menu_items[0]
            ing = ", ".join(first.ingredients) if first.ingredients else first.description
            return {"provider": "fallback", "action": "stay", "reply": f"{first.name} ingredients: {ing}."}
        if "protein" in q:
            top = max(menu_items, key=lambda m: m.protein_g)
            return {
                "provider": "fallback",
                "action": "stay",
                "reply": f"Top protein pick at {selected_restaurant.name}: {top.name} ({top.protein_g}g protein, {top.calories_kcal} kcal).",
            }
        if any(w in q for w in ("low", "light", "diet", "calorie", "kcal")):
            light = min(menu_items, key=lambda m: m.calories_kcal)
            return {
                "provider": "fallback",
                "action": "stay",
                "reply": f"Lightest dish at {selected_restaurant.name}: {light.name} ({light.calories_kcal} kcal, {light.protein_g}g protein, {light.fiber_g}g fiber).",
            }
        if "vegan" in q:
            vegans = [m.name for m in menu_items if any(t.lower() == "vegan" for t in m.dietary_tags)]
            reply = (
                f"Vegan options at {selected_restaurant.name}: {', '.join(vegans)}."
                if vegans
                else f"No strictly vegan dishes at {selected_restaurant.name}; go back to check Dakshin Spice House or GreenBowl Kitchen."
            )
            return {"provider": "fallback", "action": "stay", "reply": reply}

    # When no menu is open (or asking across nearby places), recommend exact dishes from nearby SQLite catalog
    if not menu_items and any(w in q for w in ("dish", "food", "eat", "protein", "calorie", "kcal", "vegan", "fiber", "healthy", "suggest", "workout", "gym", "diet")):
        catalog_reply = _search_catalog_dishes(q, nearby_with_menus)
        if catalog_reply:
            return {"provider": "fallback", "action": "stay", "reply": catalog_reply}

    for rest in nearby:
        if rest.name.lower() in q or (len(q) >= 4 and q in rest.name.lower()):
            return {"provider": "fallback", "action": "select_restaurant", "restaurant_id": rest.id, "reply": None}

    for item in menu_items:
        if item.name.lower() in q:
            ing = ", ".join(item.ingredients) if item.ingredients else item.description
            return {
                "provider": "fallback",
                "action": "stay",
                "reply": f"{item.name} ({ing}): {item.calories_kcal} kcal, {item.protein_g}g protein, {item.carbs_g}g carbs, {item.fat_g}g fat, {item.fiber_g}g fiber.",
            }

    return {
        "provider": "fallback",
        "action": "stay",
        "reply": f"{user_name}, tap any restaurant or ask me for high-protein, low-calorie, or vegan dishes from nearby menus.",
    }


async def interpret_message(
    state: str,
    user_name: str,
    text: str,
    nearby: list[RestaurantOut],
    selected_restaurant: RestaurantOut | None,
    menu_items: list[MenuItemOut],
    slots: list[SlotAvailabilityOut],
    recent_messages: list[dict],
    nearby_with_menus: list[tuple[RestaurantOut, list[MenuItemOut]]] | None = None,
) -> dict:
    global _status_cache
    catalog_pairs = nearby_with_menus or []

    # Fast 0-token warm response for pure greetings/thanks unless LLM greetings are explicitly enabled
    if not config.LLM_GREETINGS_USE_AI:
        quick_reply = _match_greeting_or_courtesy(text, user_name, state)
        if quick_reply is not None:
            provider = await get_provider_status()
            return {"provider": provider, "action": "stay", "reply": quick_reply}

    system_prompt = _build_system_prompt(
        state=state,
        user_name=user_name,
        nearby=nearby,
        selected_restaurant=selected_restaurant,
        menu_items=menu_items,
        slots=slots,
        nearby_with_menus=catalog_pairs,
    )

    messages = [{"role": "system", "content": system_prompt}]
    for msg in recent_messages[-6:]:
        role = "assistant" if msg["sender"] == "bot" else "user"
        messages.append({"role": role, "content": msg["text"]})
    messages.append({"role": "user", "content": text})

    try:
        raw_content, provider = await _call_chat_completion(messages, max_tokens=220)
        parsed = _extract_json(raw_content)

        action = parsed.get("action", "stay")
        if action not in ALLOWED_ACTIONS:
            action = "stay"

        _status_cache = (time.monotonic() + 15.0, provider)
        return {
            "provider": provider,
            "action": action,
            "reply": parsed.get("reply"),
            "restaurant_id": parsed.get("restaurant_id"),
            "item_id": parsed.get("item_id"),
            "goal": parsed.get("goal"),
            "booking_date": parsed.get("booking_date"),
            "time_slot": parsed.get("time_slot"),
            "party_size": parsed.get("party_size"),
            "notes": parsed.get("notes"),
        }
    except (httpx.HTTPError, ValueError, TypeError, KeyError, IndexError) as exc:
        print(f"[OpenRouter Error -> Fallback] {type(exc).__name__}: {exc}", flush=True)
        _status_cache = (time.monotonic() + 15.0, "fallback")
        return _fallback_interpret(
            state=state,
            user_name=user_name,
            text=text,
            nearby=nearby,
            selected_restaurant=selected_restaurant,
            menu_items=menu_items,
            nearby_with_menus=catalog_pairs,
        )
