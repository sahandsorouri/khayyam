# Khayyam Telegram Bot

## What is this?
A Telegram bot that sends a random ruba'i (quatrain) by Omar Khayyam to subscribers every day at 10 AM Tehran time (IRST).

## Stack
- Python 3.11+
- python-telegram-bot v21 (async)
- APScheduler v3 for daily scheduling
- SQLite for subscriber storage
- aiohttp for scraping Ganjoor

## File structure
- `scraper.py` — one-time script, fetches all 178 ruba'is from ganjoor.net → `poems.json`
- `database.py` — async SQLite helpers (add/remove/list subscribers)
- `bot.py` — main entry point: Telegram bot + scheduler

## Config
All secrets in `.env` (never commit). See `.env.example`.
- `BOT_TOKEN` — Telegram bot token from BotFather

## Deployment (server: 91.107.179.127, via Docker)
```bash
# First time
git clone https://github.com/sahandsorouri/khayyam
cd khayyam
cp .env.example .env && nano .env   # fill in BOT_TOKEN
mkdir -p data
docker compose up -d

# Logs
docker compose logs -f

# Update
git pull && docker compose up -d --build
```

SQLite DB lives in `./data/` (Docker volume, never committed).

## Conventions
- Async throughout (asyncio + python-telegram-bot v21)
- No external database — SQLite file is sufficient
- poems.json is committed to the repo (public data, no secrets)
