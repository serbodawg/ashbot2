from __future__ import annotations

import asyncio
import logging
from typing import Optional

import discord
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from config import DASHBOARD_SECRET, DASHBOARD_HOST, DASHBOARD_PORT, BASE_DIR
from ashbot.models import database as db

log = logging.getLogger("ashbot.dashboard")

# Run a discord.py coroutine in the bot's event loop from a thread
def _run_discord(coro):
    bot = get_bot()
    fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
    return fut.result()

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
        request,
        "dashboard.html",
        {
            "bot_name": bot.user.name if bot.user else "AshBot 2",
            "guild_count": len(bot.guilds),
            "guilds": guilds_data,
        },
    )


@app.get("/server/{guild_id}", response_class=HTMLResponse)
async def server_page(request: Request, guild_id: int, secret: str = "") -> HTMLResponse:
    if secret != DASHBOARD_SECRET:
        return HTMLResponse("<h1>Unauthorized</h1>", status_code=403)

    bot = get_bot()
    guild = bot.get_guild(guild_id)
    if guild is None:
        return HTMLResponse("<h1>Server not found</h1>", status_code=404)

    channels = []
    for ch in guild.channels:
        channels.append({
            "id": ch.id,
            "name": ch.name,
            "type": str(ch.type).split(".")[-1] if hasattr(ch, "type") else "unknown",
            "position": ch.position,
            "topic": getattr(ch, "topic", None),
        })

    roles = []
    for r in sorted(guild.roles, key=lambda x: x.position, reverse=True):
        roles.append({
            "id": r.id,
            "name": r.name,
            "color": str(r.color) if r.color.value else None,
            "position": r.position,
            "is_default": r.is_default(),
        })

    return templates.TemplateResponse(
        request,
        "server.html",
        {
            "guild": {
                "id": guild.id,
                "name": guild.name,
                "icon": guild.icon.url if guild.icon else None,
                "members": guild.member_count,
                "channels": channels,
                "roles": roles,
                "owner_id": guild.owner_id,
                "created_at": guild.created_at.isoformat() if guild.created_at else None,
            },
        },
    )


# --- API Endpoints ---

@app.get("/api/server/{guild_id}/stats")
async def api_server_stats(guild_id: int, secret: str = "") -> JSONResponse:
    if secret != DASHBOARD_SECRET:
        raise HTTPException(403, "Invalid secret")
    bot = get_bot()
    guild = bot.get_guild(guild_id)
    if guild is None:
        raise HTTPException(404, "Server not found")
    return JSONResponse({
        "name": guild.name,
        "members": guild.member_count,
        "channels": len(guild.channels),
        "roles": len(guild.roles),
        "owner_id": guild.owner_id,
        "max_members": guild.max_members,
        "premium_tier": guild.premium_tier,
        "premium_subscribers": guild.premium_subscription_count or 0,
    })


@app.get("/api/server/{guild_id}/warnings")
async def api_warnings(guild_id: int, user_id: Optional[int] = None, secret: str = "") -> JSONResponse:
    if secret != DASHBOARD_SECRET:
        raise HTTPException(403, "Invalid secret")
    warns = await db.get_warnings(guild_id, user_id)
    return JSONResponse(warns)


@app.post("/api/server/{guild_id}/warn")
async def api_warn(guild_id: int, request: Request, secret: str = "") -> JSONResponse:
    if secret != DASHBOARD_SECRET:
        raise HTTPException(403, "Invalid secret")
    bot = get_bot()
    guild = bot.get_guild(guild_id)
    if guild is None:
        raise HTTPException(404, "Server not found")

    body = await request.json()
    user_id = body.get("user_id")
    reason = body.get("reason", "No reason")
    moderator_id = body.get("moderator_id", bot.user.id if bot.user else 0)

    if not user_id:
        raise HTTPException(400, "user_id is required")

    try:
        uid = int(user_id)
        warning = await db.add_warning(guild_id, uid, int(moderator_id), reason)
        warn_count = len(await db.get_warnings(guild_id, uid))
        return JSONResponse({"success": True, "warning": warning, "total_warnings": warn_count})
    except Exception as e:
        log.error("Warn error: %s", e)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post("/api/server/{guild_id}/clear-warnings")
async def api_clear_warnings(guild_id: int, request: Request, secret: str = "") -> JSONResponse:
    if secret != DASHBOARD_SECRET:
        raise HTTPException(403, "Invalid secret")
    body = await request.json()
    user_id = body.get("user_id")
    if not user_id:
        raise HTTPException(400, "user_id is required")
    try:
        count = await db.clear_warnings(guild_id, int(user_id))
        return JSONResponse({"success": True, "cleared": count})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post("/api/server/{guild_id}/kick")
async def api_kick(guild_id: int, request: Request, secret: str = "") -> JSONResponse:
    if secret != DASHBOARD_SECRET:
        raise HTTPException(403, "Invalid secret")
    bot = get_bot()
    guild = bot.get_guild(guild_id)
    if guild is None:
        raise HTTPException(404, "Server not found")

    body = await request.json()
    user_id = body.get("user_id")
    reason = body.get("reason", "Kicked from dashboard")

    if not user_id:
        raise HTTPException(400, "user_id is required")

    try:
        uid = int(user_id)
        member = guild.get_member(uid)
        if member:
            _run_discord(member.kick(reason=reason))
        else:
            _run_discord(guild.kick(discord.Object(id=uid), reason=reason))
        return JSONResponse({"success": True, "action": "kick", "user_id": uid, "reason": reason})
    except Exception as e:
        log.error("Kick error: %s", e)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post("/api/server/{guild_id}/ban")
async def api_ban(guild_id: int, request: Request, secret: str = "") -> JSONResponse:
    if secret != DASHBOARD_SECRET:
        raise HTTPException(403, "Invalid secret")
    bot = get_bot()
    guild = bot.get_guild(guild_id)
    if guild is None:
        raise HTTPException(404, "Server not found")

    body = await request.json()
    user_id = body.get("user_id")
    reason = body.get("reason", "Banned from dashboard")
    delete_days = body.get("delete_days", 0)

    if not user_id:
        raise HTTPException(400, "user_id is required")

    try:
        uid = int(user_id)
        _run_discord(guild.ban(discord.Object(id=uid), reason=reason, delete_message_days=delete_days))
        return JSONResponse({"success": True, "action": "ban", "user_id": uid, "reason": reason})
    except Exception as e:
        log.error("Ban error: %s", e)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post("/api/server/{guild_id}/unban")
async def api_unban(guild_id: int, request: Request, secret: str = "") -> JSONResponse:
    if secret != DASHBOARD_SECRET:
        raise HTTPException(403, "Invalid secret")
    bot = get_bot()
    guild = bot.get_guild(guild_id)
    if guild is None:
        raise HTTPException(404, "Server not found")

    body = await request.json()
    user_id = body.get("user_id")
    if not user_id:
        raise HTTPException(400, "user_id is required")

    try:
        uid = int(user_id)
        user = _run_discord(bot.fetch_user(uid))
        _run_discord(guild.unban(user))
        return JSONResponse({"success": True, "action": "unban", "user_id": uid})
    except Exception as e:
        log.error("Unban error: %s", e)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get("/api/server/{guild_id}/settings")
async def api_settings(guild_id: int, secret: str = "") -> JSONResponse:
    if secret != DASHBOARD_SECRET:
        raise HTTPException(403, "Invalid secret")
    try:
        config = {}
        log_channels = {}
        ai_channels = []
        try:
            cfg = await db.get_guild_config(guild_id)
            if cfg:
                config = cfg
        except Exception:
            pass
        try:
            log_channels = await db.get_log_channels(guild_id)
        except Exception:
            pass
        try:
            ai_channels = await db.get_ai_channels(guild_id)
        except Exception:
            pass
        return JSONResponse({
            "config": config,
            "log_channels": log_channels,
            "ai_channels": ai_channels,
        })
    except Exception as e:
        log.error("Settings error: %s", e)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post("/api/server/{guild_id}/settings")
async def api_update_settings(guild_id: int, request: Request, secret: str = "") -> JSONResponse:
    if secret != DASHBOARD_SECRET:
        raise HTTPException(403, "Invalid secret")
    try:
        body = await request.json()
        config = await db.get_guild_config(guild_id) or {}
        config.update(body)
        result = await db.set_guild_config(guild_id, **config)
        return JSONResponse({"success": True, "config": result})
    except Exception as e:
        log.error("Update settings error: %s", e)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get("/api/server/{guild_id}/levels")
async def api_levels(guild_id: int, limit: int = 10, secret: str = "") -> JSONResponse:
    if secret != DASHBOARD_SECRET:
        raise HTTPException(403, "Invalid secret")
    try:
        levels = await db.get_leaderboard(guild_id, limit)
        return JSONResponse(levels)
    except Exception as e:
        log.error("Levels error: %s", e)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get("/api/server/{guild_id}/backups")
async def api_backups(guild_id: int, secret: str = "") -> JSONResponse:
    if secret != DASHBOARD_SECRET:
        raise HTTPException(403, "Invalid secret")
    try:
        backups = await db.get_backups(guild_id)
        return JSONResponse(backups)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


# --- Channel management ---

@app.post("/api/server/{guild_id}/channels/create")
async def api_create_channel(guild_id: int, request: Request, secret: str = "") -> JSONResponse:
    if secret != DASHBOARD_SECRET:
        raise HTTPException(403, "Invalid secret")
    bot = get_bot()
    guild = bot.get_guild(guild_id)
    if guild is None:
        raise HTTPException(404, "Server not found")

    body = await request.json()
    name = body.get("name")
    ch_type = body.get("type", "text")
    category_id = body.get("category_id")
    topic = body.get("topic", "")

    if not name:
        raise HTTPException(400, "name is required")

    try:
        category = None
        if category_id:
            category = guild.get_channel(int(category_id))

        if ch_type == "voice":
            channel = _run_discord(guild.create_voice_channel(name, category=category))
        elif ch_type == "forum":
            channel = _run_discord(guild.create_forum(name, category=category))
        else:
            channel = _run_discord(guild.create_text_channel(name, category=category, topic=topic))

        return JSONResponse({"success": True, "channel": {"id": channel.id, "name": channel.name}})
    except Exception as e:
        log.error("Create channel error: %s", e)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post("/api/server/{guild_id}/channels/{channel_id}/rename")
async def api_rename_channel(guild_id: int, channel_id: int, request: Request, secret: str = "") -> JSONResponse:
    if secret != DASHBOARD_SECRET:
        raise HTTPException(403, "Invalid secret")
    bot = get_bot()
    guild = bot.get_guild(guild_id)
    if guild is None:
        raise HTTPException(404, "Server not found")

    body = await request.json()
    name = body.get("name")
    if not name:
        raise HTTPException(400, "name is required")

    channel = guild.get_channel(channel_id)
    if channel is None:
        raise HTTPException(404, "Channel not found")

    try:
        _run_discord(channel.edit(name=name))
        return JSONResponse({"success": True, "channel": {"id": channel.id, "name": name}})
    except Exception as e:
        log.error("Rename channel error: %s", e)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.delete("/api/server/{guild_id}/channels/{channel_id}")
async def api_delete_channel(guild_id: int, channel_id: int, secret: str = "") -> JSONResponse:
    if secret != DASHBOARD_SECRET:
        raise HTTPException(403, "Invalid secret")
    bot = get_bot()
    guild = bot.get_guild(guild_id)
    if guild is None:
        raise HTTPException(404, "Server not found")

    channel = guild.get_channel(channel_id)
    if channel is None:
        raise HTTPException(404, "Channel not found")

    try:
        name = channel.name
        _run_discord(channel.delete())
        return JSONResponse({"success": True, "deleted": name})
    except Exception as e:
        log.error("Delete channel error: %s", e)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


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
