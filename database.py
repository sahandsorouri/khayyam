import os
import aiosqlite

DB_PATH = os.environ.get("DB_PATH", "subscribers.db")


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                chat_id INTEGER PRIMARY KEY,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sent_poems (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                poem_index INTEGER NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


async def add_subscriber(chat_id: int) -> bool:
    """Returns True if newly added, False if already existed."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT 1 FROM subscribers WHERE chat_id = ?", (chat_id,)
        )
        exists = await cursor.fetchone()
        if exists:
            return False
        await db.execute("INSERT INTO subscribers (chat_id) VALUES (?)", (chat_id,))
        await db.commit()
        return True


async def remove_subscriber(chat_id: int) -> bool:
    """Returns True if removed, False if wasn't subscribed."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM subscribers WHERE chat_id = ?", (chat_id,)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_all_subscribers() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT chat_id FROM subscribers")
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


async def get_recent_sent_indices(limit: int = 10) -> list[int]:
    """Returns the most recently sent poem indices to avoid repeats."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT poem_index FROM sent_poems ORDER BY sent_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


async def record_sent_poem(poem_index: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO sent_poems (poem_index) VALUES (?)", (poem_index,)
        )
        await db.commit()
