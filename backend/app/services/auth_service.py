import aiosqlite
from fastapi import HTTPException, status

from app.schemas import AuthResponse, LoginRequest, RegisterRequest, UserOut
from app.security import create_access_token, hash_password, verify_password


async def register_user(db: aiosqlite.Connection, payload: RegisterRequest) -> AuthResponse:
    email = payload.email.strip().lower()
    cur = await db.execute("SELECT id FROM users WHERE email = ?", (email,))
    if await cur.fetchone():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    pw_hash = hash_password(payload.password)
    cur = await db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (payload.name.strip(), email, pw_hash),
    )
    await db.commit()
    user_id = cur.lastrowid
    token = create_access_token(user_id, email)
    return AuthResponse(
        access_token=token,
        user=UserOut(id=user_id, name=payload.name.strip(), email=email),
    )


async def login_user(db: aiosqlite.Connection, payload: LoginRequest) -> AuthResponse:
    email = payload.email.strip().lower()
    cur = await db.execute(
        "SELECT id, name, email, password_hash FROM users WHERE email = ?",
        (email,),
    )
    row = await cur.fetchone()
    if not row or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(row["id"], row["email"])
    return AuthResponse(
        access_token=token,
        user=UserOut(id=row["id"], name=row["name"], email=row["email"]),
    )
