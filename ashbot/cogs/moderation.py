from __future__ import annotations

import logging
from datetime import timedelta, datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from ashbot.models import database as db
from ashbot.utils.permissions import mod_only
from ashbot.utils.embeds import success_embed, error_embed, warning_embed

log = logging.getLogger("ashbot.moderation")


@app_commands.guild_only()
class ModerationCog(commands.GroupCog, group_name="mod"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="warn")
    @mod_only()
    @app_commands.describe(user="User to warn", reason="Warning reason")
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str) -> None:
        await db.add_warning(interaction.guild.id, user.id, interaction.user.id, reason)
        warn_count = len(await db.get_warnings(interaction.guild.id, user.id))
        embed = warning_embed(f"Warned {user}", f"Reason: {reason}\nTotal warnings: {warn_count}")
        await interaction.response.send_message(embed=embed)
        try:
            await user.send(embed=warning_embed(f"You were warned in {interaction.guild}", f"Reason: {reason}"))
        except discord.Forbidden:
            pass

    @app_commands.command(name="warnings")
    @mod_only()
    @app_commands.describe(user="User to check")
    async def warnings(self, interaction: discord.Interaction, user: discord.Member) -> None:
        warns = await db.get_warnings(interaction.guild.id, user.id)
        if not warns:
            await interaction.response.send_message(embed=success_embed(f"{user} has no warnings"))
            return
        lines = [f"#{i+1} — {w['reason']} (by <@{w['moderator_id']}>)" for i, w in enumerate(warns)]
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"Warnings for {user}",
                description="\n".join(lines),
                color=0xF59E0B,
            )
        )

    @app_commands.command(name="clearwarns")
    @mod_only()
    @app_commands.describe(user="User to clear warnings for")
    async def clearwarns(self, interaction: discord.Interaction, user: discord.Member) -> None:
        count = await db.clear_warnings(interaction.guild.id, user.id)
        await interaction.response.send_message(embed=success_embed(f"Cleared {count} warnings for {user}"))

    @app_commands.command(name="timeout")
    @mod_only()
    @app_commands.describe(user="User to timeout", minutes="Duration in minutes", reason="Reason")
    async def timeout(
        self, interaction: discord.Interaction, user: discord.Member, minutes: int, reason: str = "No reason"
    ) -> None:
        duration = timedelta(minutes=minutes)
        await user.timeout(duration, reason=reason)
        await interaction.response.send_message(
            embed=success_embed(f"Timed out {user}", f"Duration: {minutes}m\nReason: {reason}")
        )

    @app_commands.command(name="kick")
    @mod_only()
    @app_commands.describe(user="User to kick", reason="Reason")
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason") -> None:
        await user.kick(reason=reason)
        await interaction.response.send_message(embed=success_embed(f"Kicked {user}", f"Reason: {reason}"))

    @app_commands.command(name="ban")
    @mod_only()
    @app_commands.describe(user="User to ban", reason="Reason", delete_days="Delete message history (days)")
    async def ban(
        self, interaction: discord.Interaction, user: discord.User, reason: str = "No reason", delete_days: int = 0
    ) -> None:
        await interaction.guild.ban(user, reason=reason, delete_message_days=delete_days)
        await interaction.response.send_message(embed=success_embed(f"Banned {user}", f"Reason: {reason}"))

    @app_commands.command(name="tempban")
    @mod_only()
    @app_commands.describe(user="User to tempban", days="Ban duration in days", reason="Reason")
    async def tempban(
        self, interaction: discord.Interaction, user: discord.User, days: int, reason: str = "No reason"
    ) -> None:
        await interaction.guild.ban(user, reason=f"{reason} (tempban {days}d)")
        await interaction.response.send_message(
            embed=success_embed(f"Temp-banned {user}", f"Duration: {days}d\nReason: {reason}")
        )

    @app_commands.command(name="unban")
    @mod_only()
    @app_commands.describe(user_id="User ID to unban")
    async def unban(self, interaction: discord.Interaction, user_id: str) -> None:
        try:
            user = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(user)
            await interaction.response.send_message(embed=success_embed(f"Unbanned {user}"))
        except discord.NotFound:
            await interaction.response.send_message(embed=error_embed("User not found or not banned"))

    @app_commands.command(name="purge")
    @mod_only()
    @app_commands.describe(amount="Number of messages to delete")
    async def purge(self, interaction: discord.Interaction, amount: int) -> None:
        if amount < 1 or amount > 1000:
            await interaction.response.send_message(embed=error_embed("Amount must be between 1 and 1000"))
            return
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.response.send_message(embed=success_embed(f"Deleted {len(deleted)} messages"), ephemeral=True)

    @app_commands.command(name="slowmode")
    @mod_only()
    @app_commands.describe(seconds="Slowmode in seconds (0 to disable)")
    async def slowmode(self, interaction: discord.Interaction, seconds: int) -> None:
        await interaction.channel.edit(slowmode_delay=seconds)
        if seconds > 0:
            await interaction.response.send_message(embed=success_embed(f"Set slowmode to {seconds}s"))
        else:
            await interaction.response.send_message(embed=success_embed("Disabled slowmode"))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModerationCog(bot))
