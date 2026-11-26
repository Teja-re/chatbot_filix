from collections.abc import AsyncIterator
import aiosqlite

from app import config


async def open_connection(db_path: str | None = None) -> aiosqlite.Connection:
    conn = await aiosqlite.connect(db_path or config.DB_PATH)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys = ON;")
    await conn.execute("PRAGMA busy_timeout = 5000;")
    await conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    conn = await open_connection()
    try:
        yield conn
    finally:
        await conn.close()


async def _ensure_menu_columns(conn: aiosqlite.Connection) -> None:
    cur = await conn.execute("PRAGMA table_info(menu_items)")
    cols = {row["name"] for row in await cur.fetchall()}
    if "ingredients" not in cols:
        await conn.execute("ALTER TABLE menu_items ADD COLUMN ingredients TEXT NOT NULL DEFAULT '[]'")
    if "nutrition_source" not in cols:
        await conn.execute("ALTER TABLE menu_items ADD COLUMN nutrition_source TEXT NOT NULL DEFAULT 'pending'")
    if "allergens" not in cols:
        await conn.execute("ALTER TABLE menu_items ADD COLUMN allergens TEXT NOT NULL DEFAULT '[]'")
    if "health_note" not in cols:
        await conn.execute("ALTER TABLE menu_items ADD COLUMN health_note TEXT NOT NULL DEFAULT ''")


async def init_db(db_path: str | None = None) -> None:
    conn = await open_connection(db_path)
    try:
        # WAL lets concurrent reads run without blocking on writers
        await conn.execute("PRAGMA journal_mode = WAL;")
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS restaurants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                cuisine TEXT NOT NULL,
                address TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                rating REAL NOT NULL DEFAULT 4.2,
                total_seats INTEGER NOT NULL DEFAULT 30,
                open_hours TEXT NOT NULL DEFAULT '11:00 - 23:00',
                price_tier TEXT NOT NULL DEFAULT '$$'
            );

            CREATE TABLE IF NOT EXISTS menu_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurant_id INTEGER NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                price REAL NOT NULL,
                calories_kcal INTEGER NOT NULL,
                protein_g REAL NOT NULL,
                carbs_g REAL NOT NULL,
                fat_g REAL NOT NULL,
                fiber_g REAL NOT NULL,
                dietary_tags TEXT NOT NULL DEFAULT '',
                ingredients TEXT NOT NULL DEFAULT '[]',
                nutrition_source TEXT NOT NULL DEFAULT 'pending',
                allergens TEXT NOT NULL DEFAULT '[]',
                health_note TEXT NOT NULL DEFAULT '',
                is_available INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_code TEXT NOT NULL UNIQUE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                restaurant_id INTEGER NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
                booking_date TEXT NOT NULL,
                time_slot TEXT NOT NULL,
                party_size INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'CONFIRMED',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                state TEXT NOT NULL DEFAULT 'NEARBY_LIST',
                selected_restaurant_id INTEGER REFERENCES restaurants(id) ON DELETE SET NULL,
                liked_item_ids_json TEXT NOT NULL DEFAULT '[]',
                history_json TEXT NOT NULL DEFAULT '[]',
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_restaurants_coords
                ON restaurants(latitude, longitude);

            CREATE INDEX IF NOT EXISTS idx_menu_items_restaurant
                ON menu_items(restaurant_id, is_available);

            CREATE INDEX IF NOT EXISTS idx_bookings_slot_lookup
                ON bookings(restaurant_id, booking_date, time_slot, status);

            CREATE INDEX IF NOT EXISTS idx_chat_sessions_user
                ON chat_sessions(user_id, updated_at DESC);
            """
        )
        await _ensure_menu_columns(conn)
        await conn.commit()
    finally:
        await conn.close()
