from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ashbot.models import database as db
from ashbot.utils.embeds import success_embed, error_embed, info_embed
from ashbot.utils.permissions import admin_only

log = logging.getLogger("ashbot.backups")


def serialize_guild(guild: discord.Guild) -> dict:
    categories = []
    for cat in guild.categories:
        channels = []
        for ch in cat.channels:
            ch_data = {
                "type": str(ch.type),
                "name": ch.name,
                "topic": ch.topic if isinstance(ch, discord.TextChannel) else None,
                "position": ch.position,
                "overwrites": {
                    str(target_id): {
                        "allow": overwrite.pair()[0].value,
                        "deny": overwrite.pair()[1].value,
                    }
                    for target_id, overwrite in ch.overwrites.items()
                },
            }
            channels.append(ch_data)
        categories.append({"name": cat.name, "position": cat.position, "channels": channels})

    roles = []
    for role in sorted(guild.roles, key=lambda r: r.position):
        if role.is_default() or role.is_premium_subscriber():
            continue
        roles.append({
            "name": role.name,
            "color": role.color.value,
            "hoist": role.hoist,
            "mentionable": role.mentionable,
            "permissions": role.permissions.value,
            "position": role.position,
        })

    return {
        "name": guild.name,
        "categories": categories,
        "roles": roles,
        "afk_channel_id": guild.afk_channel.id if guild.afk_channel else None,
        "afk_timeout": guild.afk_timeout,
    }


async def restore_guild(guild: discord.Guild, data: dict) -> list[str]:
    logs = []

    existing_role_names = {r.name for r in guild.roles if not r.is_default() and not r.is_premium_subscriber()}
    for role_data in data.get("roles", []):
        if role_data["name"] not in existing_role_names:
            try:
                await guild.create_role(
                    name=role_data["name"],
                    color=discord.Color(role_data["color"]),
                    hoist=role_data["hoist"],
                    mentionable=role_data["mentionable"],
                    permissions=discord.Permissions(role_data["permissions"]),
                    reason="[AshBot Backup] Restore",
                )
                logs.append(f"Created role: {role_data['name']}")
            except Exception as e:
                logs.append(f"Failed to create role {role_data['name']}: {e}")

    existing_cat_names = {c.name for c in guild.categories}
    for cat_data in data.get("categories", []):
        if cat_data["name"] not in existing_cat_names:
            try:
                cat = await guild.create_category(cat_data["name"])
                logs.append(f"Created category: {cat_data['name']}")
                for ch_data in cat_data.get("channels", []):
                    try:
                        if ch_data["type"] == "text":
                            await cat.create_text_channel(
                                name=ch_data["name"],
                                topic=ch_data.get("topic", ""),
                            )
                        elif ch_data["type"] == "voice":
                            await cat.create_voice_channel(name=ch_data["name"])
                        logs.append(f"  Created channel: {ch_data['name']}")
                    except Exception as e:
                        logs.append(f"  Failed channel {ch_data['name']}: {e}")
            except Exception as e:
                logs.append(f"Failed category {cat_data['name']}: {e}")

    return logs


@app_commands.guild_only()
class BackupsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.backup_loop.start()

    def cog_unload(self) -> None:
        self.backup_loop.cancel()

    @tasks.loop(hours=48)
    async def backup_loop(self) -> None:
        for guild in self.bot.guilds:
            try:
                data = serialize_guild(guild)
                await db.create_backup(guild.id, data)
                log.info("Auto-backup created for %s (%s)", guild.name, guild.id)
            except Exception as e:
                log.error("Auto-backup failed for %s: %s", guild.id, e)

    @backup_loop.before_loop
    async def before_backup(self) -> None:
        await self.bot.wait_until_ready()

    backup = app_commands.Group(name="backup", description="Server backup management")

    @backup.command(name="create")
    @admin_only()
    async def backup_create(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        data = serialize_guild(interaction.guild)
        record = await db.create_backup(interaction.guild.id, data)
        await interaction.followup.send(
            embed=success_embed("Backup created", f"ID: `{record['id']}` | Size: {len(json.dumps(data))} bytes")
        )

    @backup.command(name="list")
    @admin_only()
    async def backup_list(self, interaction: discord.Interaction) -> None:
        backups = await db.get_backups(interaction.guild.id)
        if not backups:
            await interaction.response.send_message(embed=info_embed("Backups", "No backups found"))
            return
        lines = []
        for b in backups[:10]:
            created = b.get("created_at", "?")[:19]
            lines.append(f"`{b['id']:4}` — {created}")
        await interaction.response.send_message(embed=info_embed(f"Backups ({len(backups)})", "\n".join(lines)))

    @backup.command(name="restore")
    @admin_only()
    @app_commands.describe(backup_id="Backup ID to restore from")
    async def backup_restore(self, interaction: discord.Interaction, backup_id: int) -> None:
        await interaction.response.defer()
        record = await db.get_backup(backup_id)
        if not record or record["guild_id"] != interaction.guild.id:
            await interaction.followup.send(embed=error_embed("Backup not found"))
            return

        try:
            data = json.loads(record["data"]) if isinstance(record["data"], str) else record["data"]
        except Exception:
            await interaction.followup.send(embed=error_embed("Invalid backup data"))
            return

        result_logs = await restore_guild(interaction.guild, data)
        summary = "\n".join(result_logs[:20])
        if len(result_logs) > 20:
            summary += f"\n... and {len(result_logs) - 20} more"
        await interaction.followup.send(embed=success_embed("Restore complete", summary))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BackupsCog(bot))
