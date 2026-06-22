from __future__ import annotations

import logging
import random
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from ashbot.models import database as db
from ashbot.utils.embeds import info_embed, success_embed

log = logging.getLogger("ashbot.levels")

XP_RATE = 15
XP_COOLDOWN = 60
XP_RANGE = (10, 25)
XP_PER_LEVEL = 100


class LevelsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.cooldowns: dict[int, dict[int, float]] = defaultdict(dict)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return

        guild_id = message.guild.id
        user_id = message.author.id
        now = datetime.utcnow().timestamp()

        last = self.cooldowns[guild_id].get(user_id, 0)
        if now - last < XP_COOLDOWN:
            return

        self.cooldowns[guild_id][user_id] = now
        xp_gain = random.randint(*XP_RANGE)
        record = await db.add_xp(guild_id, user_id, xp_gain)
        new_xp = record["xp"]
        current_level = record["level"]
        calculated_level = new_xp // XP_PER_LEVEL + 1

        if calculated_level > current_level:
            await db.set_level(guild_id, user_id, calculated_level, new_xp)
            roles = await db.get_level_roles(guild_id)
            matching = [r for r in roles if r["level"] == calculated_level]
            member = message.guild.get_member(user_id)
            if member and matching:
                for r in matching:
                    role = message.guild.get_role(r["role_id"])
                    if role and role not in member.roles:
                        try:
                            await member.add_roles(role)
                            log.info("Level role %s given to %s in %s", role.name, member, guild_id)
                        except discord.Forbidden:
                            pass
            try:
                await message.channel.send(
                    f"🎉 {message.author.mention} leveled up to **level {calculated_level}**!",
                    delete_after=10,
                )
            except discord.Forbidden:
                pass

    @app_commands.command(name="rank")
    @app_commands.describe(user="User to check (default: yourself)")
    async def rank(self, interaction: discord.Interaction, user: Optional[discord.Member] = None) -> None:
        target = user or interaction.user
        record = await db.get_level(interaction.guild.id, target.id)
        if not record:
            await interaction.response.send_message(embed=info_embed("No XP yet", f"{target.mention} hasn't earned any XP yet."))
            return
        xp = record["xp"]
        level = record["level"]
        xp_for_next = (level) * XP_PER_LEVEL
        progress = xp % XP_PER_LEVEL
        bar_len = 10
        filled = int(progress / XP_PER_LEVEL * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        embed = discord.Embed(title=f"Rank for {target.display_name}", color=0x3B82F6)
        embed.add_field(name="Level", value=str(level), inline=True)
        embed.add_field(name="XP", value=f"{xp} / {xp_for_next}", inline=True)
        embed.add_field(name="Progress", value=f"[{bar}]", inline=False)
        embed.set_thumbnail(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard")
    @app_commands.describe(limit="Number of users to show (default: 10)")
    async def leaderboard(self, interaction: discord.Interaction, limit: int = 10) -> None:
        await interaction.response.defer()
        top = await db.get_leaderboard(interaction.guild.id, min(limit, 50))
        if not top:
            await interaction.followup.send(embed=info_embed("Leaderboard", "No data yet."))
            return
        lines = []
        medals = ["🥇", "🥈", "🥉"]
        for i, entry in enumerate(top[:25]):
            member = interaction.guild.get_member(entry["user_id"])
            name = member.display_name if member else f"<@{entry['user_id']}>"
            medal = medals[i] if i < 3 else f"`#{i+1:2}`"
            lines.append(f"{medal} **{name}** — Level {entry['level']} ({entry['xp']} XP)")

        embed = discord.Embed(
            title=f"🏆 Leaderboard — {interaction.guild.name}",
            description="\n".join(lines),
            color=0x3B82F6,
        )
        embed.set_footer(text=f"Top {len(top)} shown")
        await interaction.followup.send(embed=embed)

    levelrole = app_commands.Group(name="levelrole", description="Manage level roles")

    @levelrole.command(name="add")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(level="Level required", role="Role to assign")
    async def levelrole_add(self, interaction: discord.Interaction, level: int, role: discord.Role) -> None:
        await db.set_level_role(interaction.guild.id, level, role.id)
        await interaction.response.send_message(embed=success_embed(f"Role {role.name} will be given at level {level}"))

    @levelrole.command(name="remove")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(level="Level to remove role from")
    async def levelrole_remove(self, interaction: discord.Interaction, level: int) -> None:
        if await db.remove_level_role(interaction.guild.id, level):
            await interaction.response.send_message(embed=success_embed(f"Removed role for level {level}"))
        else:
            await interaction.response.send_message("No role set for that level.")

    @levelrole.command(name="list")
    async def levelrole_list(self, interaction: discord.Interaction) -> None:
        roles = await db.get_level_roles(interaction.guild.id)
        if not roles:
            await interaction.response.send_message("No level roles configured.")
            return
        lines = [f"Level {r['level']} → <@&{r['role_id']}>" for r in roles]
        await interaction.response.send_message(embed=info_embed("Level Roles", "\n".join(lines)))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LevelsCog(bot))
