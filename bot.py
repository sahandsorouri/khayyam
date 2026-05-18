import json
import logging
import os
import random
from pathlib import Path

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

import database as db

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TEHRAN = pytz.timezone("Asia/Tehran")
POEMS_FILE = Path("poems.json")


def load_poems() -> list[dict]:
    with open(POEMS_FILE, encoding="utf-8") as f:
        return json.load(f)["poems"]


def format_poem(poem: dict) -> str:
    verses = "\n".join(poem["verses"])
    summary_part = ""
    if poem.get("summary"):
        summary_part = f"\n━━━━━━━━━━━━━━━\n💭 {poem['summary']}"
    return (
        f"📜 *رباعی خیام*\n\n"
        f"{verses}"
        f"{summary_part}\n\n"
        f"_رباعی {poem['index']} از ۱۷۸_"
    )


async def pick_random_poem(poems: list[dict]) -> dict:
    recent = await db.get_recent_sent_indices(limit=30)
    recent_set = set(recent)
    candidates = [p for p in poems if p["index"] not in recent_set]
    if not candidates:
        candidates = poems
    return random.choice(candidates)


async def broadcast(app: Application) -> None:
    poems = load_poems()
    poem = await pick_random_poem(poems)
    text = format_poem(poem)
    subscribers = await db.get_all_subscribers()

    logger.info(f"Broadcasting ruba'i #{poem['index']} to {len(subscribers)} subscribers")

    failed = 0
    for chat_id in subscribers:
        try:
            await app.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            logger.warning(f"Failed to send to {chat_id}: {e}")
            failed += 1

    await db.record_sent_poem(poem["index"])
    logger.info(f"Done. {len(subscribers) - failed} delivered, {failed} failed.")


# ── Command handlers ──────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    added = await db.add_subscriber(chat_id)

    if added:
        await update.message.reply_text(
            "خوش آمدی 🌹\n\n"
            "هر روز ساعت ۱۰ صبح یک رباعی از خیام برایت می‌فرستم.\n\n"
            "برای دریافت همین الان: /poem\n"
            "برای لغو عضویت: /stop",
        )
    else:
        await update.message.reply_text(
            "از قبل عضو هستی.\nهر روز ساعت ۱۰ صبح رباعی می‌رسد. 🌹"
        )


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    removed = await db.remove_subscriber(chat_id)

    if removed:
        await update.message.reply_text("لغو عضویت شد. هر وقت خواستی /start بزن.")
    else:
        await update.message.reply_text("عضو نبودی.")


async def cmd_poem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    poems = load_poems()
    poem = await pick_random_poem(poems)
    await update.message.reply_text(
        format_poem(poem),
        parse_mode=ParseMode.MARKDOWN,
    )


# ── Lifecycle hooks — run inside the bot's event loop ────────────────────────

async def post_init(app: Application) -> None:
    await db.init_db()

    scheduler = AsyncIOScheduler(timezone=TEHRAN)
    scheduler.add_job(broadcast, trigger="cron", hour=10, minute=0, args=[app])
    scheduler.start()
    app.bot_data["scheduler"] = scheduler

    logger.info("DB ready. Scheduler started — daily at 10:00 IRST.")


async def post_shutdown(app: Application) -> None:
    scheduler = app.bot_data.get("scheduler")
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable is not set")

    if not POEMS_FILE.exists():
        raise RuntimeError("poems.json not found — run scraper.py first")

    app = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("poem", cmd_poem))

    logger.info("Bot starting…")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
