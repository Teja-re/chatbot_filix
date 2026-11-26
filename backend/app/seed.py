import aiosqlite

from app.security import hash_password

RESTAURANTS_SEED = [
    {
        "name": "GreenBowl Kitchen",
        "cuisine": "Healthy Bowls & Salads",
        "address": "12th Main, Indiranagar",
        "latitude": 12.9718,
        "longitude": 77.6412,
        "rating": 4.7,
        "total_seats": 24,
        "open_hours": "10:00 - 22:30",
        "price_tier": "$$",
        "menu": [
            ("Quinoa Grilled Chicken Bowl", "Mains", "Herb-grilled chicken breast, quinoa, roasted peppers, lemon tahini.", 380.0, 520, 42.0, 44.0, 16.0, 8.5, "High-Protein,Gluten-Free"),
            ("Crispy Tofu Edamame Bowl", "Mains", "Tamari-glazed tofu, brown rice, steamed edamame, sesame slaw.", 340.0, 460, 26.0, 48.0, 15.0, 9.0, "Vegan,High-Protein"),
            ("Mediterranean Chickpea Salad", "Salads", "Chickpeas, cucumber, olives, feta, olive oil oregano dressing.", 290.0, 390, 14.0, 36.0, 19.0, 10.5, "Veg,Gluten-Free"),
            ("Berry Chia Protein Parfait", "Desserts", "Greek yogurt, chia seeds, mixed berries, toasted almonds.", 210.0, 240, 16.0, 22.0, 8.0, 6.0, "Veg,Gluten-Free"),
        ],
    },
    {
        "name": "Dakshin Spice House",
        "cuisine": "South Indian",
        "address": "100 Feet Road, Koramangala",
        "latitude": 12.9352,
        "longitude": 77.6245,
        "rating": 4.6,
        "total_seats": 36,
        "open_hours": "07:30 - 22:30",
        "price_tier": "$",
        "menu": [
            ("Ragi Masala Dosa", "Mains", "Crispy finger-millet crepe filled with spiced potato and curry leaves.", 170.0, 340, 9.0, 54.0, 9.0, 7.2, "Vegan,Gluten-Free"),
            ("Pesarattu & Ginger Chutney", "Starters", "Green moong dal crepe high in plant protein with spicy ginger dip.", 150.0, 280, 14.0, 38.0, 6.5, 8.0, "Vegan,High-Protein"),
            ("Malabar Fish Curry & Red Rice", "Mains", "Coconut-tamarind simmered seer fish served with unpolished red rice.", 410.0, 560, 34.0, 52.0, 22.0, 4.5, "Gluten-Free,High-Protein"),
            ("Steamed Idli Platter (3 pcs)", "Starters", "Fermented rice-lentil cakes with vegetable sambar and coconut chutney.", 120.0, 230, 8.0, 42.0, 3.0, 4.0, "Vegan,Gluten-Free"),
        ],
    },
    {
        "name": "Olive & Ember",
        "cuisine": "Mediterranean Grill",
        "address": "Church Street, Central",
        "latitude": 12.9752,
        "longitude": 77.6046,
        "rating": 4.8,
        "total_seats": 20,
        "open_hours": "12:00 - 23:30",
        "price_tier": "$$$",
        "menu": [
            ("Charred Salmon & Asparagus", "Mains", "Atlantic salmon fillet with garlic asparagus and herb olive oil.", 720.0, 490, 40.0, 10.0, 31.0, 3.5, "High-Protein,Gluten-Free"),
            ("Hummus & Za'atar Chicken Plate", "Mains", "Grilled chicken skewers over creamy hummus with warm pita.", 460.0, 540, 38.0, 40.0, 22.0, 7.0, "High-Protein"),
            ("Roasted Cauliflower Tabouli", "Salads", "Parsley, mint, bulgur wheat, pomegranate, spiced cauliflower.", 310.0, 310, 10.0, 44.0, 10.0, 8.5, "Vegan"),
            ("Grilled Halloumi Skewers", "Starters", "Charred halloumi cheese with bell peppers and balsamic glaze.", 330.0, 360, 22.0, 12.0, 24.0, 2.0, "Veg,Gluten-Free"),
        ],
    },
    {
        "name": "Kuro Ramen & Grill",
        "cuisine": "Japanese & Asian",
        "address": "Lavelle Road, Central",
        "latitude": 12.9701,
        "longitude": 77.5990,
        "rating": 4.5,
        "total_seats": 28,
        "open_hours": "12:00 - 23:00",
        "price_tier": "$$",
        "menu": [
            ("Miso Chicken Ramen", "Mains", "Slow-simmered miso broth, grilled chicken, soft egg, bamboo shoots.", 490.0, 580, 35.0, 62.0, 18.0, 4.0, "High-Protein"),
            ("Steamed Sea Salt Edamame", "Starters", "Young soybeans tossed with flaky sea salt and togarashi.", 190.0, 180, 16.0, 14.0, 7.0, 6.5, "Vegan,Gluten-Free"),
            ("Teriyaki Salmon Rice Bowl", "Mains", "Pan-seared salmon, steamed jasmine rice, pickled ginger, bok choy.", 620.0, 610, 36.0, 58.0, 23.0, 3.5, "High-Protein"),
            ("Tofu & Shiitake Clear Soup", "Starters", "Light dashi broth with silken tofu, shiitake mushrooms, scallions.", 220.0, 145, 11.0, 12.0, 5.0, 2.5, "Veg"),
        ],
    },
    {
        "name": "Forno Rustico",
        "cuisine": "Wood-Fired Italian",
        "address": "Jayanagar 4th Block",
        "latitude": 12.9299,
        "longitude": 77.5838,
        "rating": 4.4,
        "total_seats": 32,
        "open_hours": "11:30 - 23:00",
        "price_tier": "$$",
        "menu": [
            ("Sourdough Margherita Pizza", "Mains", "Naturally leavened crust, San Marzano tomato, fresh mozzarella, basil.", 420.0, 640, 26.0, 78.0, 22.0, 4.5, "Veg"),
            ("Grilled Chicken Pesto Zoodles", "Mains", "Spiralized zucchini noodles, basil pesto, cherry tomatoes, chicken.", 450.0, 410, 37.0, 14.0, 23.0, 4.0, "High-Protein,Gluten-Free"),
            ("Minestrone Soup", "Starters", "Classic vegetable, cannellini bean, and herb tomato broth.", 240.0, 210, 9.0, 32.0, 5.0, 7.5, "Vegan"),
            ("Burrata & Heirloom Tomato", "Salads", "Creamy burrata, vine tomatoes, arugula, cold-pressed olive oil.", 390.0, 350, 18.0, 10.0, 27.0, 2.0, "Veg,Gluten-Free"),
        ],
    },
    {
        "name": "MacroPlate Bistro",
        "cuisine": "Fitness & Macro-Balanced",
        "address": "HSR Layout Sector 2",
        "latitude": 12.9121,
        "longitude": 77.6446,
        "rating": 4.7,
        "total_seats": 18,
        "open_hours": "08:00 - 22:00",
        "price_tier": "$$",
        "menu": [
            ("Peri-Peri Chicken & Sweet Potato", "Mains", "Lean peri-peri chicken breast, roasted sweet potato mash, broccoli.", 390.0, 470, 46.0, 42.0, 11.0, 7.0, "High-Protein,Gluten-Free"),
            ("Paneer Tikka Protein Salad", "Salads", "Tandoor-charred low-fat paneer, spinach, peppers, mint yogurt.", 340.0, 380, 28.0, 18.0, 20.0, 5.5, "Veg,High-Protein,Gluten-Free"),
            ("Egg White & Spinach Omelette", "Starters", "Four egg whites, baby spinach, mushrooms, multigrain toast.", 230.0, 260, 27.0, 20.0, 6.0, 4.0, "High-Protein"),
            ("Dark Cacao Whey Smoothie", "Drinks", "Unsweetened almond milk, whey isolate, banana, raw cacao.", 220.0, 240, 28.0, 22.0, 4.0, 4.5, "Veg,High-Protein,Gluten-Free"),
        ],
    },
]


async def seed_database(conn: aiosqlite.Connection) -> None:
    cursor = await conn.execute("SELECT COUNT(*) FROM restaurants")
    (restaurant_count,) = await cursor.fetchone()

    if restaurant_count == 0:
        for rest in RESTAURANTS_SEED:
            cur = await conn.execute(
                """
                INSERT INTO restaurants
                    (name, cuisine, address, latitude, longitude, rating, total_seats, open_hours, price_tier)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rest["name"],
                    rest["cuisine"],
                    rest["address"],
                    rest["latitude"],
                    rest["longitude"],
                    rest["rating"],
                    rest["total_seats"],
                    rest["open_hours"],
                    rest["price_tier"],
                ),
            )
            restaurant_id = cur.lastrowid
            await conn.executemany(
                """
                INSERT INTO menu_items
                    (restaurant_id, name, category, description, price, calories_kcal, protein_g, carbs_g, fat_g, fiber_g, dietary_tags, ingredients, nutrition_source, allergens, health_note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', 'pending', '[]', '')
                """,
                [(restaurant_id, *item) for item in rest["menu"]],
            )

    demo_email = "demo@dinebot.com"
    cur = await conn.execute("SELECT id FROM users WHERE email = ?", (demo_email,))
    if await cur.fetchone() is None:
        await conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Alex", demo_email, hash_password("demo1234")),
        )

    await conn.commit()
