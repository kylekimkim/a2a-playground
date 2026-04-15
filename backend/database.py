import os
import aiomysql
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

_pool: aiomysql.Pool | None = None


async def get_pool() -> aiomysql.Pool:
    global _pool
    if _pool is None:
        _pool = await aiomysql.create_pool(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            db=os.getenv("DB_NAME", "rag-playground"),
            charset="utf8mb4",
            autocommit=False,
            minsize=2,
            maxsize=10,
        )
    return _pool


async def init_db():
    """연결 풀 초기화 및 DB 접속 확인."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1")
    print(f"[DB] MariaDB connected — {os.getenv('DB_NAME')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}")


async def close_db():
    global _pool
    if _pool:
        _pool.close()
        await _pool.wait_closed()
        _pool = None
