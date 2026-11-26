import json
import math
import time
import aiosqlite

from app import config
from app.schemas import MenuItemOut, RestaurantOut
from app.services import llm_service

# Simple TTL cache: restaurant_id -> (expires_at, list[MenuItemOut])
_menu_cache: dict[int, tuple[float, list[MenuItemOut]]] = {}


def clear_menu_cache(restaurant_id: int | None = None) -> None:
    if restaurant_id is None:
        _menu_cache.clear()
    else:
        _menu_cache.pop(restaurant_id, None)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return 2 * earth_km * math.asin(math.sqrt(a))


def _row_to_restaurant(row: aiosqlite.Row, lat: float, lon: float) -> RestaurantOut:
    dist = round(haversine_km(lat, lon, row["latitude"], row["longitude"]), 2)
    return RestaurantOut(
        id=row["id"],
        name=row["name"],
        cuisine=row["cuisine"],
        address=row["address"],
        latitude=row["latitude"],
        longitude=row["longitude"],
        rating=row["rating"],
        total_seats=row["total_seats"],
        open_hours=row["open_hours"],
        price_tier=row["price_tier"],
        distance_km=dist,
    )


async def get_nearby_restaurants(
    db: aiosqlite.Connection,
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float = 15.0,
    limit: int = 20,
) -> list[RestaurantOut]:
    ref_lat = config.DEFAULT_LAT if lat is None else lat
    ref_lon = config.DEFAULT_LON if lon is None else lon

    lat_delta = radius_km / 111.0
    cos_lat = max(abs(math.cos(math.radians(ref_lat))), 0.01)
    lon_delta = radius_km / (111.0 * cos_lat)

    cursor = await db.execute(
        """
        SELECT id, name, cuisine, address, latitude, longitude, rating, total_seats, open_hours, price_tier
        FROM restaurants
        WHERE latitude BETWEEN ? AND ?
          AND longitude BETWEEN ? AND ?
        """,
        (ref_lat - lat_delta, ref_lat + lat_delta, ref_lon - lon_delta, ref_lon + lon_delta),
    )
    rows = await cursor.fetchall()

    results = [_row_to_restaurant(r, ref_lat, ref_lon) for r in rows]
    results = [r for r in results if r.distance_km <= radius_km]

    if not results:
        cursor = await db.execute(
            """
            SELECT id, name, cuisine, address, latitude, longitude, rating, total_seats, open_hours, price_tier
            FROM restaurants
            """
        )
        all_rows = await cursor.fetchall()
        results = [_row_to_restaurant(r, ref_lat, ref_lon) for r in all_rows]

    results.sort(key=lambda r: (r.distance_km, -r.rating))
    return results[:limit]


async def get_restaurant_by_id(
    db: aiosqlite.Connection,
    restaurant_id: int,
    lat: float | None = None,
    lon: float | None = None,
) -> RestaurantOut | None:
    ref_lat = config.DEFAULT_LAT if lat is None else lat
    ref_lon = config.DEFAULT_LON if lon is None else lon

    cursor = await db.execute(
        """
        SELECT id, name, cuisine, address, latitude, longitude, rating, total_seats, open_hours, price_tier
        FROM restaurants
        WHERE id = ?
        """,
        (restaurant_id,),
    )
    row = await cursor.fetchone()
    return _row_to_restaurant(row, ref_lat, ref_lon) if row else None


def _parse_json_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except ValueError:
        pass
    return []


def _row_to_menu_item(row: aiosqlite.Row) -> MenuItemOut:
    return MenuItemOut(
        id=row["id"],
        restaurant_id=row["restaurant_id"],
        name=row["name"],
        category=row["category"],
        description=row["description"],
        price=row["price"],
        calories_kcal=row["calories_kcal"],
        protein_g=row["protein_g"],
        carbs_g=row["carbs_g"],
        fat_g=row["fat_g"],
        fiber_g=row["fiber_g"],
        dietary_tags=[t.strip() for t in row["dietary_tags"].split(",") if t.strip()],
        ingredients=_parse_json_list(row["ingredients"]),
        nutrition_source=row["nutrition_source"] or "pending",
        allergens=_parse_json_list(row["allergens"]),
        health_note=row["health_note"] or "",
        is_available=bool(row["is_available"]),
    )


async def get_restaurant_menu(
    db: aiosqlite.Connection,
    restaurant_id: int,
    dietary: str | None = None,
    max_calories: int | None = None,
) -> list[MenuItemOut]:
    now = time.monotonic()
    cached = _menu_cache.get(restaurant_id)
    if cached and cached[0] > now:
        items = cached[1]
    else:
        cursor = await db.execute(
            """
            SELECT id, restaurant_id, name, category, description, price,
                   calories_kcal, protein_g, carbs_g, fat_g, fiber_g, dietary_tags,
                   ingredients, nutrition_source, allergens, health_note, is_available
            FROM menu_items
            WHERE restaurant_id = ? AND is_available = 1
            ORDER BY category, id
            """,
            (restaurant_id,),
        )
        rows = await cursor.fetchall()
        items = [_row_to_menu_item(row) for row in rows]
        if len(_menu_cache) > 256:
            _menu_cache.clear()
        _menu_cache[restaurant_id] = (now + config.MENU_CACHE_TTL_SECONDS, items)

    filtered = items
    if dietary:
        target = dietary.strip().lower()
        filtered = [i for i in filtered if any(t.lower() == target for t in i.dietary_tags)]
    if max_calories is not None:
        filtered = [i for i in filtered if i.calories_kcal <= max_calories]
    return filtered


async def get_restaurants_with_menus(
    db: aiosqlite.Connection,
    restaurants: list[RestaurantOut],
) -> list[tuple[RestaurantOut, list[MenuItemOut]]]:
    if not restaurants:
        return []
    ids = [r.id for r in restaurants]
    placeholders = ",".join("?" for _ in ids)
    cursor = await db.execute(
        f"""
        SELECT id, restaurant_id, name, category, description, price,
               calories_kcal, protein_g, carbs_g, fat_g, fiber_g, dietary_tags,
               ingredients, nutrition_source, allergens, health_note, is_available
        FROM menu_items
        WHERE restaurant_id IN ({placeholders}) AND is_available = 1
        ORDER BY restaurant_id, id
        """,
        ids,
    )
    by_rest: dict[int, list[MenuItemOut]] = {rid: [] for rid in ids}
    for row in await cursor.fetchall():
        by_rest[row["restaurant_id"]].append(_row_to_menu_item(row))
    return [(r, by_rest.get(r.id, [])) for r in restaurants]


async def ensure_menu_enriched(
    db: aiosqlite.Connection,
    restaurant_id: int,
    force: bool = False,
) -> list[MenuItemOut]:
    """Fetch ingredients, nutrients, allergens, and health notes via LLM once per restaurant."""
    items = await get_restaurant_menu(db, restaurant_id)
    if not items:
        return items

    needs_fetch = force or any(item.nutrition_source == "pending" or not item.ingredients for item in items)
    if not needs_fetch:
        return items

    rest = await get_restaurant_by_id(db, restaurant_id)
    if not rest:
        return items

    enriched_map, source = await llm_service.enrich_menu_nutrition(rest.name, rest.cuisine, items)
    if not enriched_map:
        return items

    for item in items:
        data = enriched_map.get(item.id)
        if not data:
            continue
        tags = ",".join(data["dietary_tags"]) if data["dietary_tags"] else ",".join(item.dietary_tags)
        await db.execute(
            """
            UPDATE menu_items
            SET ingredients = ?,
                calories_kcal = ?,
                protein_g = ?,
                carbs_g = ?,
                fat_g = ?,
                fiber_g = ?,
                dietary_tags = ?,
                allergens = ?,
                health_note = ?,
                nutrition_source = ?
            WHERE id = ?
            """,
            (
                json.dumps(data["ingredients"]),
                data["calories_kcal"],
                data["protein_g"],
                data["carbs_g"],
                data["fat_g"],
                data["fiber_g"],
                tags,
                json.dumps(data["allergens"]),
                data["health_note"],
                source,
                item.id,
            ),
        )
    await db.commit()
    clear_menu_cache(restaurant_id)
    return await get_restaurant_menu(db, restaurant_id)
