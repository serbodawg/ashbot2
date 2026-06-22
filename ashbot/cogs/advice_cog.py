from __future__ import annotations

import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from ashbot.models import database as db
from ashbot.utils.embeds import info_embed, success_embed, error_embed
from ashbot.utils.permissions import admin_only

log = logging.getLogger("ashbot.advice")


@app_commands.guild_only()
class AdviceCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    fallback_advice = [
        "Take a deep breath and think before you act.",
        "Kindness costs nothing but means everything.",
        "Every expert was once a beginner.",
        "The best time to start is now.",
        "Listen more than you speak.",
        "Progress, not perfection.",
        "You are stronger than you think.",
        "Small steps lead to big changes.",
        "Be the reason someone smiles today.",
        "Your attitude determines your direction.",
    ]

    @app_commands.command(name="advice")
    async def advice(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        text = await db.get_random_advice()
        if not text:
            import random
            text = random.choice(self.fallback_advice)
        embed = info_embed("💡 Advice", text)
        embed.set_footer(text="AshBot 2 Advice System")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="advice-add")
    @admin_only()
    @app_commands.describe(text="Advice text to add")
    async def advice_add(self, interaction: discord.Interaction, text: str) -> None:
        await db.add_advice(text, interaction.user.id)
        await interaction.response.send_message(embed=success_embed("Advice added!"))

    @app_commands.command(name="advice-remove")
    @admin_only()
    @app_commands.describe(advice_id="Advice ID to remove")
    async def advice_remove(self, interaction: discord.Interaction, advice_id: int) -> None:
        if await db.delete_advice(advice_id):
            await interaction.response.send_message(embed=success_embed("Advice removed"))
        else:
            await interaction.response.send_message(embed=error_embed("Advice not found"))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdviceCog(bot))
