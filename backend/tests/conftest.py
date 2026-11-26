import asyncio
from pathlib import Path
import sys
import pytest
from httpx import ASGITransport, AsyncClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import config
from app.database import init_db, open_connection
from app.main import app
from app.seed import seed_database
from app.services.llm_service import clear_health_cache
from app.services.restaurant_service import clear_menu_cache


@pytest.fixture()
async def client(tmp_path):
    db_file = str(tmp_path / "test_dining.db")
    config.DB_PATH = db_file
    config.OPENROUTER_API_KEY = ""
    clear_menu_cache()
    clear_health_cache()

    await init_db(db_file)
    conn = await open_connection(db_file)
    try:
        await seed_database(conn)
    finally:
        await conn.close()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture()
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()
