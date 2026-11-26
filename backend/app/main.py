from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.database import init_db, open_connection
from app.routers import auth, bookings, chat, restaurants
from app.seed import seed_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    conn = await open_connection()
    try:
        await seed_database(conn)
    finally:
        await conn.close()
    yield


app = FastAPI(title="DineBot Table Booking API", version="1.0.0", lifespan=lifespan)

app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(restaurants.router)
app.include_router(bookings.router)
app.include_router(chat.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
