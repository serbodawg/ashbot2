from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from ashbot.cogs.ai_cog import ask_ai
from ashbot.models import database as db

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
            "You are a matchmaker AI. Given two usernames, guess their genders based on names, "
            "then create a ship name (combine their names creatively), "
            "give a compatibility percentage, "
            "and write a short funny description of their relationship. "
            "Format:\n**Ship name:** ...\n**Płeć:** ... i ...\n**Compatibility:** X%\n**Opis:** ...\n"
            "Keep it under 400 characters total. Use Polish language. Be creative and funny."
        )
        reply = await ask_ai(
            system,
            [{"role": "user", "content": f"Ship {user1.display_name} and {user2.display_name}"}],
        )
        ship_name = reply.split("**Ship name:**")[-1].split("\n")[0].strip().rstrip("*") if "**Ship name:**" in reply else ""
        await db.add_ship(interaction.guild.id, interaction.user.id, user1.id, user2.id, ship_name)
        await interaction.followup.send(
            f"👤 **{interaction.user.display_name}** zshipował(ła) {user1.mention} z {user2.mention}:\n\n{reply}"
        )

    @app_commands.command(name="ships")
    async def ships(self, interaction: discord.Interaction) -> None:
        records = await db.get_recent_ships(interaction.guild.id, 10)
        if not records:
            await interaction.response.send_message("Brak shipów na tym serwerze.")
            return

        lines = []
        for r in records:
            u1 = interaction.guild.get_member(r["user1_id"])
            u2 = interaction.guild.get_member(r["user2_id"])
            shipper = interaction.guild.get_member(r["shipper_id"])
            n1 = u1.display_name if u1 else f"<@{r['user1_id']}>"
            n2 = u2.display_name if u2 else f"<@{r['user2_id']}>"
            ns = shipper.display_name if shipper else f"<@{r['shipper_id']}>"
            name = f" — **{r['ship_name']}**" if r["ship_name"] else ""
            lines.append(f"• {ns} zshipował(ła) {n1} x {n2}{name}")

        embed = discord.Embed(
            title="🚢 Ostatnie shipy",
            description="\n".join(lines),
            color=0xFF69B4,
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FunCog(bot))
