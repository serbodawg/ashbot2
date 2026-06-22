from __future__ import annotations

import logging
from typing import Optional

import discord
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from config import DASHBOARD_SECRET, DASHBOARD_HOST, DASHBOARD_PORT, BASE_DIR

log = logging.getLogger("ashbot.dashboard")

app = FastAPI(title="AshBot 2 Dashboard")

templates = Jinja2Templates(directory=str(BASE_DIR / "ashbot" / "templates"))
static_dir = BASE_DIR / "ashbot" / "dashboard" / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

_bot_instance: Optional["AshBot"] = None


def set_bot(bot) -> None:
    global _bot_instance
    _bot_instance = bot


def get_bot():
    if _bot_instance is None:
        raise HTTPException(503, "Bot not initialized")
    return _bot_instance


async def verify_secret(request: Request) -> None:
    secret = request.headers.get("X-Dashboard-Secret") or request.query_params.get("secret")
    if secret != DASHBOARD_SECRET:
        raise HTTPException(403, "Invalid secret")


@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request, secret: str = "") -> HTMLResponse:
    if secret != DASHBOARD_SECRET:
        return HTMLResponse("<h1>Unauthorized</h1><p>Provide ?secret= in URL from .env</p>", status_code=403)

    bot = get_bot()
    guilds_data = []
    for guild in bot.guilds:
        guilds_data.append({
            "id": guild.id,
            "name": guild.name,
            "members": guild.member_count,
            "icon": guild.icon.url if guild.icon else None,
        })

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "bot_name": bot.user.name if bot.user else "AshBot 2",
            "guild_count": len(bot.guilds),
            "guilds": guilds_data,
        },
    )


@app.get("/api/stats")
async def api_stats(secret: str = "") -> JSONResponse:
    if secret != DASHBOARD_SECRET:
        raise HTTPException(403, "Invalid secret")
    bot = get_bot()
    return JSONResponse({
        "guilds": len(bot.guilds),
        "users": sum(g.member_count for g in bot.guilds),
        "name": bot.user.name if bot.user else "AshBot 2",
    })


def start_dashboard(bot) -> None:
    set_bot(bot)
    import uvicorn
    log.info("Dashboard starting on %s:%s", DASHBOARD_HOST, DASHBOARD_PORT)
    uvicorn.run(app, host=DASHBOARD_HOST, port=DASHBOARD_PORT, log_level="info")
