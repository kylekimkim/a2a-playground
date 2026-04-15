import uuid
from datetime import datetime, timezone
import aiomysql
from database import get_pool


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


async def create_room(room_id: str | None = None, title: str = "New Chat") -> dict:
    rid = room_id or str(uuid.uuid4())
    now = _now_ms()
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO rooms (id, title, created_at, updated_at) VALUES (%s, %s, %s, %s)",
                (rid, title, now, now),
            )
        await conn.commit()
    return {"id": rid, "title": title, "created_at": now, "updated_at": now}


async def get_room(room_id: str) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT * FROM rooms WHERE id = %s", (room_id,))
            return await cur.fetchone()


async def list_rooms() -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT * FROM rooms ORDER BY updated_at DESC")
            return await cur.fetchall()


async def delete_room(room_id: str) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM rooms WHERE id = %s", (room_id,))
            deleted = cur.rowcount > 0
        await conn.commit()
    return deleted


async def update_room_title(room_id: str, title: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE rooms SET title = %s WHERE id = %s", (title, room_id)
            )
        await conn.commit()


async def save_message(room_id: str, role: str, content: str) -> dict:
    mid = str(uuid.uuid4())
    now = _now_ms()
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO messages (id, room_id, role, content, created_at) VALUES (%s, %s, %s, %s, %s)",
                (mid, room_id, role, content, now),
            )
            await cur.execute(
                "UPDATE rooms SET updated_at = %s WHERE id = %s", (now, room_id)
            )
        await conn.commit()
    return {"id": mid, "room_id": room_id, "role": role, "content": content, "created_at": now}


async def get_messages(room_id: str) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT * FROM messages WHERE room_id = %s ORDER BY created_at ASC",
                (room_id,),
            )
            return await cur.fetchall()


async def room_exists(room_id: str) -> bool:
    return (await get_room(room_id)) is not None
