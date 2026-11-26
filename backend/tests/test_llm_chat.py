import json
import httpx
import pytest

from app import config
from app.services import llm_service


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


@pytest.mark.anyio
async def test_openrouter_enriches_ingredients_and_nutrients_and_caches(client, monkeypatch):
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "sk-or-test-key")

    login = await client.post(
        "/api/auth/login",
        json={"email": "demo@dinebot.com", "password": "demo1234"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    sess = await client.get("/api/chat/session", headers=headers)
    rest_id = sess.json()["nearby_restaurants"][0]["id"]

    orig_post = httpx.AsyncClient.post
    openrouter_calls = 0

    async def fake_post(self, url, **kwargs):
        nonlocal openrouter_calls
        if not str(url).startswith(config.OPENROUTER_BASE_URL):
            return await orig_post(self, url, **kwargs)

        openrouter_calls += 1
        req_payload = kwargs.get("json") or {}
        user_content = req_payload["messages"][-1]["content"]
        # Extract dish IDs sent to enrichment prompt
        dishes_json = user_content.split("Dishes:", 1)[1]
        dishes = json.loads(dishes_json)

        enriched_items = [
            {
                "id": d["id"],
                "ingredients": ["Quinoa", "Grilled chicken", "Bell peppers", "Tahini"],
                "calories_kcal": 495,
                "protein_g": 41.5,
                "carbs_g": 42.0,
                "fat_g": 15.0,
                "fiber_g": 8.0,
                "dietary_tags": ["High-Protein", "Gluten-Free"],
                "allergens": ["Sesame"],
                "health_note": "Lean high-protein bowl",
            }
            for d in dishes
        ]
        return _FakeResponse(
            {"choices": [{"message": {"content": json.dumps({"items": enriched_items})}}]}
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    # First selection triggers 1 batched OpenRouter call
    res1 = await client.post(
        "/api/chat/action",
        headers=headers,
        json={"action": "select_restaurant", "restaurant_id": rest_id},
    )
    assert res1.status_code == 200
    body1 = res1.json()
    assert body1["llm_provider"] == "openrouter"
    assert body1["state"] == "VIEWING_MENU"
    assert openrouter_calls == 1
    assert body1["menu_items"][0]["nutrition_source"] == "openrouter_llm"
    assert body1["menu_items"][0]["ingredients"] == ["Quinoa", "Grilled chicken", "Bell peppers", "Tahini"]
    assert body1["menu_items"][0]["calories_kcal"] == 495
    assert body1["menu_items"][0]["allergens"] == ["Sesame"]
    assert body1["menu_items"][0]["health_note"] == "Lean high-protein bowl"

    # Go back and re-select -> cached in SQLite, zero additional LLM calls
    await client.post("/api/chat/action", headers=headers, json={"action": "go_back"})
    res2 = await client.post(
        "/api/chat/action",
        headers=headers,
        json={"action": "select_restaurant", "restaurant_id": rest_id},
    )
    assert res2.status_code == 200
    assert openrouter_calls == 1


@pytest.mark.anyio
async def test_openrouter_natural_language_chat_and_nutrition_qa(client, monkeypatch):
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "sk-or-test-key")

    login = await client.post(
        "/api/auth/login",
        json={"email": "demo@dinebot.com", "password": "demo1234"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    sess = await client.get("/api/chat/session", headers=headers)
    target_rest = sess.json()["nearby_restaurants"][0]

    orig_post = httpx.AsyncClient.post

    async def fake_post(self, url, **kwargs):
        if not str(url).startswith(config.OPENROUTER_BASE_URL):
            return await orig_post(self, url, **kwargs)

        payload = kwargs.get("json") or {}
        last_msg = payload["messages"][-1]["content"]
        if "Dishes:" in last_msg:
            dishes = json.loads(last_msg.split("Dishes:", 1)[1])
            enriched = [
                {
                    "id": d["id"],
                    "ingredients": ["Ingredient A", "Ingredient B"],
                    "calories_kcal": 410,
                    "protein_g": 33.0,
                    "carbs_g": 35.0,
                    "fat_g": 12.0,
                    "fiber_g": 6.0,
                    "dietary_tags": ["High-Protein"],
                }
                for d in dishes
            ]
            return _FakeResponse(
                {"choices": [{"message": {"content": json.dumps({"items": enriched})}}]}
            )

        user_msg = last_msg.lower()
        if "select" in user_msg or "green" in user_msg:
            content = {
                "reply": f"Opening {target_rest['name']} with AI-fetched ingredients and macros.",
                "action": "select_restaurant",
                "restaurant_id": target_rest["id"],
            }
        else:
            content = {
                "reply": "Each bowl includes high-protein ingredients at 410 kcal.",
                "action": "stay",
            }
        return _FakeResponse({"choices": [{"message": {"content": json.dumps(content)}}]})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    res1 = await client.post(
        "/api/chat/action",
        headers=headers,
        json={"action": "message", "text": "Select GreenBowl Kitchen"},
    )
    assert res1.status_code == 200
    body1 = res1.json()
    assert body1["llm_provider"] == "openrouter"
    assert body1["state"] == "VIEWING_MENU"

    res2 = await client.post(
        "/api/chat/action",
        headers=headers,
        json={"action": "message", "text": "What ingredients and calories are in the bowl?"},
    )
    assert res2.status_code == 200
    assert "410 kcal" in res2.json()["messages"][-1]["text"].lower()


@pytest.mark.anyio
async def test_llm_offline_graceful_fallback(client, monkeypatch):
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "sk-or-test-key")

    login = await client.post(
        "/api/auth/login",
        json={"email": "demo@dinebot.com", "password": "demo1234"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    sess = await client.get("/api/chat/session", headers=headers)
    rest_id = sess.json()["nearby_restaurants"][0]["id"]

    orig_post = httpx.AsyncClient.post

    async def failing_post(self, url, **kwargs):
        if not str(url).startswith(config.OPENROUTER_BASE_URL):
            return await orig_post(self, url, **kwargs)
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(httpx.AsyncClient, "post", failing_post)
    llm_service._status_cache = (0.0, "fallback")

    await client.post(
        "/api/chat/action",
        headers=headers,
        json={"action": "select_restaurant", "restaurant_id": rest_id},
    )

    res = await client.post(
        "/api/chat/action",
        headers=headers,
        json={"action": "message", "text": "Which dish has the lowest calories?"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["llm_provider"] == "fallback"
    assert body["state"] == "VIEWING_MENU"
    assert "kcal" in body["messages"][-1]["text"].lower()


@pytest.mark.anyio
async def test_health_recommend_openrouter_and_cache_plus_fallback(client, monkeypatch):
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "sk-or-test-key")

    login = await client.post(
        "/api/auth/login",
        json={"email": "demo@dinebot.com", "password": "demo1234"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    sess = await client.get("/api/chat/session", headers=headers)
    first_rest = sess.json()["nearby_restaurants"][0]

    orig_post = httpx.AsyncClient.post
    calls = 0

    async def fake_post(self, url, **kwargs):
        nonlocal calls
        if not str(url).startswith(config.OPENROUTER_BASE_URL):
            return await orig_post(self, url, **kwargs)
        calls += 1
        body = {
            "reply": f"{first_rest['name']} is best for high-protein dining.",
            "recommendations": [
                {
                    "restaurant_id": first_rest["id"],
                    "badge": "Best High-Protein",
                    "reason": "42g+ protein bowls under 550 kcal",
                    "recommended_dishes": ["Quinoa Grilled Chicken Bowl"],
                }
            ],
        }
        return _FakeResponse({"choices": [{"message": {"content": json.dumps(body)}}]})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    r1 = await client.post(
        "/api/chat/health-recommend",
        headers=headers,
        json={"goal": "High Protein"},
    )
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["state"] == "NEARBY_LIST"
    assert d1["health_goal"] == "High Protein"
    assert len(d1["recommendations"]) == 1
    assert d1["recommendations"][0]["restaurant_id"] == first_rest["id"]
    assert calls == 1

    # Second identical goal hits 5-min cache with 0 extra LLM calls
    r2 = await client.post(
        "/api/chat/action",
        headers=headers,
        json={"action": "recommend_healthy", "goal": "High Protein"},
    )
    assert r2.status_code == 200
    assert calls == 1

    # Offline fallback scoring still returns healthy recommendations for another goal
    async def failing_post(self, url, **kwargs):
        if not str(url).startswith(config.OPENROUTER_BASE_URL):
            return await orig_post(self, url, **kwargs)
        raise httpx.ConnectError("Offline")

    monkeypatch.setattr(httpx.AsyncClient, "post", failing_post)
    r3 = await client.post(
        "/api/chat/health-recommend",
        headers=headers,
        json={"goal": "Low Calorie"},
    )
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["llm_provider"] == "fallback"
    assert len(d3["recommendations"]) >= 1


@pytest.mark.anyio
async def test_greetings_zero_tokens_and_local_catalog_protein_grounding(client, monkeypatch):
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "sk-or-test-key")

    login = await client.post(
        "/api/auth/login",
        json={"email": "demo@dinebot.com", "password": "demo1234"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    orig_post = httpx.AsyncClient.post
    llm_calls = 0
    captured_prompt = ""

    async def fake_post(self, url, **kwargs):
        nonlocal llm_calls, captured_prompt
        if not str(url).startswith(config.OPENROUTER_BASE_URL):
            return await orig_post(self, url, **kwargs)
        llm_calls += 1
        captured_prompt = kwargs["json"]["messages"][0]["content"]
        return _FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "reply": "Try Peri-Peri Chicken & Sweet Potato at MacroPlate Bistro (46.0g protein, 470 kcal).",
                                    "action": "stay",
                                }
                            )
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    # 1. Greeting consumes 0 OpenRouter calls and replies warmly by name
    hi_res = await client.post(
        "/api/chat/action",
        headers=headers,
        json={"action": "message", "text": "Hi!"},
    )
    assert hi_res.status_code == 200
    assert llm_calls == 0
    assert "alex" in hi_res.json()["messages"][-1]["text"].lower()

    # 2. Protein dish question on NEARBY_LIST sends real nearby SQLite dishes in Ctx
    protein_res = await client.post(
        "/api/chat/action",
        headers=headers,
        json={"action": "message", "text": "Tell me a good dish suitable for my protein"},
    )
    assert protein_res.status_code == 200
    assert llm_calls == 1
    assert "MacroPlate Bistro" in captured_prompt
    assert "Peri-Peri Chicken & Sweet Potato" in captured_prompt
    assert "MacroPlate Bistro" in protein_res.json()["messages"][-1]["text"]

    # 3. Offline fallback on NEARBY_LIST also returns real SQLite dishes with restaurant names
    async def failing_post(self, url, **kwargs):
        if not str(url).startswith(config.OPENROUTER_BASE_URL):
            return await orig_post(self, url, **kwargs)
        raise httpx.ConnectError("Offline")

    monkeypatch.setattr(httpx.AsyncClient, "post", failing_post)
    fb_res = await client.post(
        "/api/chat/action",
        headers=headers,
        json={"action": "message", "text": "Tell me a good dish suitable for my protein"},
    )
    assert fb_res.status_code == 200
    fb_text = fb_res.json()["messages"][-1]["text"]
    assert "MacroPlate Bistro" in fb_text
    assert "46.0g protein" in fb_text

    # 4. Polite goodbye moves cleanly to ENDED without creating a booking
    bye_res = await client.post(
        "/api/chat/action",
        headers=headers,
        json={"action": "message", "text": "bye, catch you later"},
    )
    assert bye_res.status_code == 200
    assert bye_res.json()["state"] == "ENDED"
