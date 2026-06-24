"""
Database module — SQLite via aiosqlite (no server needed, persisted in Railway volume).
All tables are created on first run.
"""
import aiosqlite
import os
import logging

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "groupbot.db")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS warnings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id     INTEGER NOT NULL,
                user_id     INTEGER NOT NULL,
                reason      TEXT,
                warned_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS blocklist (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id     INTEGER NOT NULL,
                word        TEXT NOT NULL,
                added_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(chat_id, word)
            );

            CREATE TABLE IF NOT EXISTS chat_settings (
                chat_id         INTEGER PRIMARY KEY,
                night_mode      INTEGER DEFAULT 0,
                night_start     TEXT DEFAULT '22:00',
                night_end       TEXT DEFAULT '06:00',
                welcome_msg     TEXT,
                welcome_enabled INTEGER DEFAULT 1,
                max_warns       INTEGER DEFAULT 3,
                log_channel_id  INTEGER
            );

            CREATE TABLE IF NOT EXISTS scheduled_messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id     INTEGER NOT NULL,
                message     TEXT NOT NULL,
                cron_expr   TEXT NOT NULL,
                job_id      TEXT NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS muted_no_profile (
                chat_id     INTEGER NOT NULL,
                user_id     INTEGER NOT NULL,
                muted_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (chat_id, user_id)
            );
        """)
        await db.commit()
    logger.info("Database initialised at %s", DB_PATH)


# ─── Warnings ────────────────────────────────────────────────────────────────

async def add_warning(chat_id: int, user_id: int, reason: str = "No reason given") -> int:
    """Add a warning and return the new total count."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO warnings (chat_id, user_id, reason) VALUES (?, ?, ?)",
            (chat_id, user_id, reason)
        )
        await db.commit()
    return await get_warning_count(chat_id, user_id)


async def get_warning_count(chat_id: int, user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM warnings WHERE chat_id=? AND user_id=?",
            (chat_id, user_id)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_warnings(chat_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT reason, warned_at FROM warnings WHERE chat_id=? AND user_id=? ORDER BY warned_at",
            (chat_id, user_id)
        )
        return await cursor.fetchall()


async def reset_warnings(chat_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM warnings WHERE chat_id=? AND user_id=?",
            (chat_id, user_id)
        )
        await db.commit()


# ─── Blocklist ────────────────────────────────────────────────────────────────

async def add_blocked_word(chat_id: int, word: str):
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO blocklist (chat_id, word) VALUES (?, ?)",
                (chat_id, word.lower())
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def remove_blocked_word(chat_id: int, word: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM blocklist WHERE chat_id=? AND word=?",
            (chat_id, word.lower())
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_blocked_words(chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT word FROM blocklist WHERE chat_id=?", (chat_id,)
        )
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


# ─── Chat settings ────────────────────────────────────────────────────────────

async def get_settings(chat_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM chat_settings WHERE chat_id=?", (chat_id,)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        # Insert defaults and return them
        await db.execute("INSERT OR IGNORE INTO chat_settings (chat_id) VALUES (?)", (chat_id,))
        await db.commit()
        cursor = await db.execute(
            "SELECT * FROM chat_settings WHERE chat_id=?", (chat_id,)
        )
        row = await cursor.fetchone()
        return dict(row)


async def update_setting(chat_id: int, key: str, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO chat_settings (chat_id) VALUES (?)", (chat_id,))
        await db.execute(
            f"UPDATE chat_settings SET {key}=? WHERE chat_id=?",
            (value, chat_id)
        )
        await db.commit()


# ─── Scheduled messages ───────────────────────────────────────────────────────

async def save_scheduled(chat_id: int, message: str, cron_expr: str, job_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO scheduled_messages (chat_id, message, cron_expr, job_id) VALUES (?,?,?,?)",
            (chat_id, message, cron_expr, job_id)
        )
        await db.commit()


async def delete_scheduled(job_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM scheduled_messages WHERE job_id=?", (job_id,))
        await db.commit()


async def get_all_scheduled(chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, message, cron_expr, job_id FROM scheduled_messages WHERE chat_id=?",
            (chat_id,)
        )
        return await cursor.fetchall()


async def get_all_scheduled_all_chats():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT chat_id, message, cron_expr, job_id FROM scheduled_messages"
        )
        return await cursor.fetchall()


# ─── Muted-no-profile ─────────────────────────────────────────────────────────

async def add_muted_no_profile(chat_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO muted_no_profile (chat_id, user_id) VALUES (?,?)",
            (chat_id, user_id)
        )
        await db.commit()


async def remove_muted_no_profile(chat_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM muted_no_profile WHERE chat_id=? AND user_id=?",
            (chat_id, user_id)
        )
        await db.commit()


async def is_muted_no_profile(chat_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT 1 FROM muted_no_profile WHERE chat_id=? AND user_id=?",
            (chat_id, user_id)
        )
        return await cursor.fetchone() is not None
