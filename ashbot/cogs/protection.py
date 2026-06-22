from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from ashbot.models import database as db
from ashbot.utils.embeds import error_embed, success_embed, warning_embed
from ashbot.utils.permissions import admin_only

log = logging.getLogger("ashbot.protection")

NUKE_THRESHOLD = 3
NUKE_WINDOW = 10


class ProtectionCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.audit: dict[int, list[tuple[float, str, int, int | None]]] = defaultdict(list)

    def _record_action(self, guild_id: int, action: str, moderator_id: int, target_id: int | None = None) -> None:
        now = datetime.utcnow().timestamp()
        records = self.audit[guild_id]
        records.append((now, action, moderator_id, target_id))
        cutoff = now - NUKE_WINDOW
        self.audit[guild_id] = [(t, a, m, tid) for t, a, m, tid in records if t > cutoff]

    def _count_actions(self, guild_id: int, action: str, moderator_id: int | None = None) -> int:
        return sum(
            1 for t, a, m, _ in self.audit[guild_id]
            if a == action and (moderator_id is None or m == moderator_id)
        )

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        guild = channel.guild
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
            if entry.user and entry.user.id != self.bot.user.id:
                self._record_action(guild.id, "channel_create", entry.user.id)
                count = self._count_actions(guild.id, "channel_create", entry.user.id)
                if count >= NUKE_THRESHOLD:
                    await self._handle_nuke(guild, entry.user, "mass channel creation")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        guild = channel.guild
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            if entry.user and entry.user.id != self.bot.user.id:
                self._record_action(guild.id, "channel_delete", entry.user.id)
                count = self._count_actions(guild.id, "channel_delete", entry.user.id)
                if count >= NUKE_THRESHOLD:
                    await self._handle_nuke(guild, entry.user, "mass channel deletion")

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role) -> None:
        guild = role.guild
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
            if entry.user and entry.user.id != self.bot.user.id:
                self._record_action(guild.id, "role_create", entry.user.id)
                count = self._count_actions(guild.id, "role_create", entry.user.id)
                if count >= NUKE_THRESHOLD:
                    await self._handle_nuke(guild, entry.user, "mass role creation")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        guild = role.guild
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
            if entry.user and entry.user.id != self.bot.user.id:
                self._record_action(guild.id, "role_delete", entry.user.id)
                count = self._count_actions(guild.id, "role_delete", entry.user.id)
                if count >= NUKE_THRESHOLD:
                    await self._handle_nuke(guild, entry.user, "mass role deletion")

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User) -> None:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            if entry.user and entry.user.id != self.bot.user.id:
                self._record_action(guild.id, "ban", entry.user.id, user.id)
                count = self._count_actions(guild.id, "ban", entry.user.id)
                if count >= NUKE_THRESHOLD:
                    await self._handle_nuke(guild, entry.user, "mass bans")

    async def _handle_nuke(self, guild: discord.Guild, suspect: discord.User | discord.Member, reason: str) -> None:
        log.warning("NUKE DETECTED in %s by %s: %s", guild.id, suspect.id, reason)

        config = await db.get_guild_config(guild.id)
        auto_ban = config.get("auto_ban_nuke", True) if config else True

        embed = error_embed(
            "🚨 Anti-Nuke Triggered!",
            f"**User:** {suspect.mention} (`{suspect.id}`)\n"
            f"**Action:** {reason}\n"
            f"**Auto-ban:** {'✅' if auto_ban else '❌'}",
        )

        log_channels = await db.get_log_channels(guild.id)
        for ch_id in log_channels.values():
            ch = guild.get_channel(ch_id)
            if ch and isinstance(ch, discord.TextChannel):
                await ch.send(embed=embed)

        try:
            member = guild.get_member(suspect.id)
            if member and auto_ban:
                await member.ban(reason=f"[AshBot Anti-Nuke] {reason}", delete_message_days=0)
                await guild.unban(suspect, reason="Reversible: pending review")
                log.info("Auto-banned nuke suspect %s in %s", suspect.id, guild.id)
        except discord.Forbidden as e:
            log.error("Cannot ban nuke suspect %s: %s", suspect.id, e)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.bot:
            guild = member.guild
            whitelist = await db.get_bot_whitelist(guild.id)
            if member.id not in whitelist:
                try:
                    await member.kick(reason="[AshBot] Unauthorized bot")
                    log.info("Kicked unauthorized bot %s in %s", member, guild.id)
                    log_channels = await db.get_log_channels(guild.id)
                    for ch_id in log_channels.values():
                        ch = guild.get_channel(ch_id)
                        if ch and isinstance(ch, discord.TextChannel):
                            await ch.send(
                                embed=warning_embed(
                                    "Bot kicked",
                                    f"Unauthorized bot {member.mention} (`{member.id}`) was kicked.",
                                )
                            )
                except discord.Forbidden as e:
                    log.error("Cannot kick unauthorized bot %s: %s", member.id, e)

    # --- Commands ---

    bot_group = app_commands.Group(name="bot", description="Bot whitelist management")

    @bot_group.command(name="whitelist-add")
    @admin_only()
    @app_commands.describe(bot_id="Bot user ID to whitelist")
    async def bot_whitelist_add(self, interaction: discord.Interaction, bot_id: str) -> None:
        try:
            uid = int(bot_id)
            await db.add_bot_whitelist(interaction.guild.id, uid)
            await interaction.response.send_message(embed=success_embed(f"Bot `{uid}` whitelisted"))
        except ValueError:
            await interaction.response.send_message("Invalid ID")

    @bot_group.command(name="whitelist-remove")
    @admin_only()
    @app_commands.describe(bot_id="Bot user ID to remove from whitelist")
    async def bot_whitelist_remove(self, interaction: discord.Interaction, bot_id: str) -> None:
        try:
            uid = int(bot_id)
            await db.remove_bot_whitelist(interaction.guild.id, uid)
            await interaction.response.send_message(embed=success_embed(f"Bot `{uid}` removed from whitelist"))
        except ValueError:
            await interaction.response.send_message("Invalid ID")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ProtectionCog(bot))
