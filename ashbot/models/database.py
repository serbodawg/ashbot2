from __future__ import annotations

from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, log

_supabase: Client | None = None


def get_db() -> Client:
    global _supabase
    if _supabase is None:
        if not SUPABASE_SERVICE_ROLE_KEY:
            log.critical("SUPABASE_SERVICE_ROLE_KEY not set in .env")
            raise SystemExit(1)
        _supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        log.info("Connected to Supabase")
    return _supabase


# --- Guild config ---

async def get_guild_config(guild_id: int) -> dict | None:
    db = get_db()
    resp = db.table("ashbot_guild_config").select("*").eq("guild_id", guild_id).maybe_single().execute()
    return resp.data


async def set_guild_config(guild_id: int, **kwargs) -> dict:
    db = get_db()
    existing = await get_guild_config(guild_id)
    if existing:
        resp = db.table("ashbot_guild_config").update(kwargs).eq("guild_id", guild_id).execute()
    else:
        kwargs["guild_id"] = guild_id
        resp = db.table("ashbot_guild_config").insert(kwargs).execute()
    return resp.data[0] if resp.data else {}


# --- Warnings ---

async def add_warning(guild_id: int, user_id: int, moderator_id: int, reason: str) -> dict:
    db = get_db()
    resp = db.table("ashbot_warnings").insert({
        "guild_id": guild_id,
        "user_id": user_id,
        "moderator_id": moderator_id,
        "reason": reason,
    }).execute()
    return resp.data[0]


async def get_warnings(guild_id: int, user_id: int | None = None) -> list[dict]:
    db = get_db()
    q = db.table("ashbot_warnings").select("*").eq("guild_id", guild_id)
    if user_id is not None:
        q = q.eq("user_id", user_id)
    resp = q.order("created_at", desc=True).execute()
    return resp.data


async def clear_warnings(guild_id: int, user_id: int) -> int:
    db = get_db()
    resp = db.table("ashbot_warnings").delete().eq("guild_id", guild_id).eq("user_id", user_id).execute()
    return len(resp.data)


# --- Levels ---

async def get_level(guild_id: int, user_id: int) -> dict | None:
    db = get_db()
    resp = db.table("ashbot_levels").select("*").eq("guild_id", guild_id).eq("user_id", user_id).maybe_single().execute()
    return resp.data


async def add_xp(guild_id: int, user_id: int, xp: int) -> dict:
    db = get_db()
    existing = await get_level(guild_id, user_id)
    if existing:
        new_xp = existing["xp"] + xp
        resp = db.table("ashbot_levels").update({"xp": new_xp}).eq("guild_id", guild_id).eq("user_id", user_id).execute()
    else:
        resp = db.table("ashbot_levels").insert({
            "guild_id": guild_id,
            "user_id": user_id,
            "xp": xp,
            "level": 1,
        }).execute()
    return resp.data[0]


async def set_level(guild_id: int, user_id: int, level: int, xp: int) -> dict:
    db = get_db()
    existing = await get_level(guild_id, user_id)
    if existing:
        resp = db.table("ashbot_levels").update({"level": level, "xp": xp}).eq("guild_id", guild_id).eq("user_id", user_id).execute()
    else:
        resp = db.table("ashbot_levels").insert({
            "guild_id": guild_id,
            "user_id": user_id,
            "xp": xp,
            "level": level,
        }).execute()
    return resp.data[0]


async def get_leaderboard(guild_id: int, limit: int = 10) -> list[dict]:
    db = get_db()
    resp = db.table("ashbot_levels").select("*").eq("guild_id", guild_id).order("xp", desc=True).limit(limit).execute()
    return resp.data


async def get_level_roles(guild_id: int) -> list[dict]:
    db = get_db()
    resp = db.table("ashbot_level_roles").select("*").eq("guild_id", guild_id).order("level").execute()
    return resp.data


async def set_level_role(guild_id: int, level: int, role_id: int) -> dict:
    db = get_db()
    existing = db.table("ashbot_level_roles").select("*").eq("guild_id", guild_id).eq("level", level).maybe_single().execute()
    if existing.data:
        resp = db.table("ashbot_level_roles").update({"role_id": role_id}).eq("guild_id", guild_id).eq("level", level).execute()
    else:
        resp = db.table("ashbot_level_roles").insert({"guild_id": guild_id, "level": level, "role_id": role_id}).execute()
    return resp.data[0] if resp.data else {}


async def remove_level_role(guild_id: int, level: int) -> bool:
    db = get_db()
    resp = db.table("ashbot_level_roles").delete().eq("guild_id", guild_id).eq("level", level).execute()
    return len(resp.data) > 0


# --- Advice ---

async def get_random_advice() -> str | None:
    db = get_db()
    resp = db.rpc("ashbot_random_advice").execute()
    return resp.data


async def add_advice(text: str, added_by: int) -> dict:
    db = get_db()
    resp = db.table("ashbot_advice").insert({"text": text, "added_by": added_by}).execute()
    return resp.data[0]


async def delete_advice(advice_id: int) -> bool:
    db = get_db()
    resp = db.table("ashbot_advice").delete().eq("id", advice_id).execute()
    return len(resp.data) > 0


# --- Bot whitelist/blacklist ---

async def get_bot_whitelist(guild_id: int) -> list[int]:
    db = get_db()
    resp = db.table("ashbot_bot_whitelist").select("bot_id").eq("guild_id", guild_id).execute()
    return [r["bot_id"] for r in resp.data]


async def add_bot_whitelist(guild_id: int, bot_id: int) -> bool:
    db = get_db()
    db.table("ashbot_bot_whitelist").insert({"guild_id": guild_id, "bot_id": bot_id}).execute()
    return True


async def remove_bot_whitelist(guild_id: int, bot_id: int) -> bool:
    db = get_db()
    resp = db.table("ashbot_bot_whitelist").delete().eq("guild_id", guild_id).eq("bot_id", bot_id).execute()
    return len(resp.data) > 0


# --- Backups ---

async def create_backup(guild_id: int, data: dict) -> dict:
    db = get_db()
    import json
    resp = db.table("ashbot_backups").insert({
        "guild_id": guild_id,
        "data": json.dumps(data),
    }).execute()
    return resp.data[0]


async def get_backups(guild_id: int) -> list[dict]:
    db = get_db()
    resp = db.table("ashbot_backups").select("*").eq("guild_id", guild_id).order("created_at", desc=True).execute()
    return resp.data


async def get_backup(backup_id: int) -> dict | None:
    db = get_db()
    resp = db.table("ashbot_backups").select("*").eq("id", backup_id).maybe_single().execute()
    return resp.data


async def delete_backup(backup_id: int) -> bool:
    db = get_db()
    resp = db.table("ashbot_backups").delete().eq("id", backup_id).execute()
    return len(resp.data) > 0


# --- Log channels ---

async def get_log_channels(guild_id: int) -> dict[str, int]:
    db = get_db()
    resp = db.table("ashbot_log_channels").select("log_type, channel_id").eq("guild_id", guild_id).execute()
    return {r["log_type"]: r["channel_id"] for r in resp.data}


async def set_log_channel(guild_id: int, log_type: str, channel_id: int) -> dict:
    db = get_db()
    existing = db.table("ashbot_log_channels").select("*").eq("guild_id", guild_id).eq("log_type", log_type).maybe_single().execute()
    if existing.data:
        resp = db.table("ashbot_log_channels").update({"channel_id": channel_id}).eq("guild_id", guild_id).eq("log_type", log_type).execute()
    else:
        resp = db.table("ashbot_log_channels").insert({"guild_id": guild_id, "log_type": log_type, "channel_id": channel_id}).execute()
    return resp.data[0] if resp.data else {}


# --- AI channel settings ---

async def get_ai_channels(guild_id: int) -> list[int]:
    db = get_db()
    resp = db.table("ashbot_ai_channels").select("channel_id").eq("guild_id", guild_id).eq("enabled", True).execute()
    return [r["channel_id"] for r in resp.data]


async def set_ai_channel(guild_id: int, channel_id: int, enabled: bool) -> dict:
    db = get_db()
    existing = db.table("ashbot_ai_channels").select("*").eq("guild_id", guild_id).eq("channel_id", channel_id).maybe_single().execute()
    if existing.data:
        resp = db.table("ashbot_ai_channels").update({"enabled": enabled}).eq("guild_id", guild_id).eq("channel_id", channel_id).execute()
    else:
        resp = db.table("ashbot_ai_channels").insert({"guild_id": guild_id, "channel_id": channel_id, "enabled": enabled}).execute()
    return resp.data[0] if resp.data else {}
