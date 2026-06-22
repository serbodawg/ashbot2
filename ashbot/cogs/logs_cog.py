from __future__ import annotations

import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from ashbot.models import database as db
from ashbot.utils.embeds import success_embed
from ashbot.utils.permissions import admin_only

log = logging.getLogger("ashbot.logs")

LOG_TYPES = [
    ("messages", "Message edits/deletes"),
    ("bans", "Ban/unban events"),
    ("kicks", "Kick events"),
    ("channels", "Channel create/delete/update"),
    ("roles", "Role create/delete/update"),
    ("joins", "Member joins"),
    ("leaves", "Member leaves"),
    ("admin", "Admin actions"),
    ("attacks", "Detected attacks"),
]


class LogsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _send_log(self, guild_id: int, log_type: str, embed: discord.Embed) -> None:
        channels = await db.get_log_channels(guild_id)
        ch_id = channels.get(log_type) or channels.get("admin")
        if not ch_id:
            return
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        channel = guild.get_channel(ch_id)
        if channel and isinstance(channel, discord.TextChannel):
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return
        embed = discord.Embed(title="Message Deleted", color=0xEF4444)
        embed.add_field(name="Author", value=message.author.mention, inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        if message.content:
            embed.add_field(name="Content", value=message.content[:500], inline=False)
        embed.set_footer(text=f"ID: {message.id}")
        await self._send_log(message.guild.id, "messages", embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if before.guild is None or before.author.bot or before.content == after.content:
            return
        embed = discord.Embed(title="Message Edited", color=0x3B82F6)
        embed.add_field(name="Author", value=before.author.mention, inline=True)
        embed.add_field(name="Channel", value=before.channel.mention, inline=True)
        embed.add_field(name="Before", value=before.content[:500] or "(empty)", inline=False)
        embed.add_field(name="After", value=after.content[:500] or "(empty)", inline=False)
        embed.set_footer(text=f"ID: {before.id}")
        await self._send_log(before.guild.id, "messages", embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User) -> None:
        embed = discord.Embed(title="Member Banned", color=0xEF4444)
        embed.add_field(name="User", value=f"{user} ({user.id})", inline=False)
        await self._send_log(guild.id, "bans", embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User) -> None:
        embed = discord.Embed(title="Member Unbanned", color=0x22C55E)
        embed.add_field(name="User", value=f"{user} ({user.id})", inline=False)
        await self._send_log(guild.id, "bans", embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        if member.bot:
            return
        embed = discord.Embed(title="Member Left", color=0xF59E0B)
        embed.add_field(name="User", value=f"{member} ({member.id})", inline=False)
        embed.add_field(name="Roles", value=", ".join(r.name for r in member.roles[1:10]) or "None", inline=False)
        await self._send_log(member.guild.id, "leaves", embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.bot:
            return
        embed = discord.Embed(title="Member Joined", color=0x22C55E)
        embed.add_field(name="User", value=f"{member.mention} ({member.id})", inline=False)
        embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
        await self._send_log(member.guild.id, "joins", embed)

    # --- Commands ---

    log_group = app_commands.Group(name="log", description="Configure log channels")

    @log_group.command(name="set")
    @admin_only()
    @app_commands.describe(log_type="Type of logs", channel="Target channel")
    async def log_set(self, interaction: discord.Interaction, log_type: str, channel: discord.TextChannel) -> None:
        valid = [t[0] for t in LOG_TYPES]
        if log_type not in valid:
            await interaction.response.send_message(
                f"Invalid type. Valid: {', '.join(valid)}", ephemeral=True
            )
            return
        await db.set_log_channel(interaction.guild.id, log_type, channel.id)
        await interaction.response.send_message(
            embed=success_embed(f"Log channel set", f"`{log_type}` → {channel.mention}")
        )

    @log_group.command(name="list")
    @admin_only()
    async def log_list(self, interaction: discord.Interaction) -> None:
        channels = await db.get_log_channels(interaction.guild.id)
        if not channels:
            await interaction.response.send_message("No log channels configured.")
            return
        lines = [f"**{t}** → <#{ch}>" if t in channels else f"**{t}** → Not set" for t, _ in LOG_TYPES]
        await interaction.response.send_message("\n".join(lines))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LogsCog(bot))
