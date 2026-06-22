from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from ashbot.cogs.ai_cog import ask_ai

log = logging.getLogger("ashbot.fun")


@app_commands.guild_only()
class FunCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="roast")
    @app_commands.describe(user="User to roast")
    async def roast(self, interaction: discord.Interaction, user: discord.User) -> None:
        await interaction.response.defer()
        system = (
            "You are a roast master. Generate a short, creative, funny roast "
            "of the given person. Keep it under 200 characters. "
            "Make it humorous, not mean or offensive. Use Polish language."
        )
        reply = await ask_ai(system, [{"role": "user", "content": f"Roast {user.display_name}"}])
        await interaction.followup.send(f"{user.mention} {reply}")

    @app_commands.command(name="compliment")
    @app_commands.describe(user="User to compliment")
    async def compliment(self, interaction: discord.Interaction, user: discord.User) -> None:
        await interaction.response.defer()
        system = (
            "You are a kind and uplifting person. Generate a short, sincere, "
            "creative compliment for the given person. Keep it under 200 characters. "
            "Use Polish language."
        )
        reply = await ask_ai(system, [{"role": "user", "content": f"Compliment {user.display_name}"}])
        await interaction.followup.send(f"{user.mention} {reply}")

    @app_commands.command(name="ship")
    @app_commands.describe(user1="First user", user2="Second user")
    async def ship(
        self,
        interaction: discord.Interaction,
        user1: discord.User,
        user2: discord.User,
    ) -> None:
        await interaction.response.defer()
        system = (
            "You are a matchmaker AI. Given two usernames, create a ship name "
            "(combine their names creatively), give a compatibility percentage, "
            "and write a short funny description of their relationship. "
            "Format:\n**Ship name:** ...\n**Compatibility:** X%\n**Description:** ...\n"
            "Keep it under 300 characters total. Use Polish language. Be creative and funny."
        )
        reply = await ask_ai(
            system,
            [{"role": "user", "content": f"Ship {user1.display_name} and {user2.display_name}"}],
        )
        await interaction.followup.send(reply)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FunCog(bot))
