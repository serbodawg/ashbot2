from __future__ import annotations

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
BACKUPS_DIR = BASE_DIR / "backups"

for d in (DATA_DIR, LOGS_DIR, BACKUPS_DIR):
    d.mkdir(parents=True, exist_ok=True)

DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://slckcmnewrenyedvjgmv.supabase.co")
SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

AI_API_KEY: str = os.getenv("AI_API_KEY", "")
AI_MODEL: str = os.getenv("AI_MODEL", "gemini-2.5-flash-lite")

DASHBOARD_SECRET: str = os.getenv("DASHBOARD_SECRET", "change-me")
DASHBOARD_HOST: str = os.getenv("DASHBOARD_HOST", "0.0.0.0")
DASHBOARD_PORT: int = int(os.getenv("DASHBOARD_PORT", "8080"))
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

OWNER_IDS: list[int] = [int(x) for x in os.getenv("OWNER_IDS", "").split(",") if x]

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(str(LOGS_DIR / "ashbot.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("ashbot")

if not DISCORD_TOKEN:
    log.critical("DISCORD_TOKEN not set in .env")
    raise SystemExit(1)
