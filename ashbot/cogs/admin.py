from __future__ import annotations

import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from ashbot.utils.permissions import admin_only, mod_only
from ashbot.utils.embeds import success_embed, error_embed

log = logging.getLogger("ashbot.admin")


@app_commands.guild_only()
class AdminCog(commands.GroupCog, group_name="channel"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="create")
    @admin_only()
    @app_commands.describe(
        name="Channel name",
        type="Channel type (text or voice)",
        category="Category to create under (optional)",
        topic="Channel topic (text channels only)",
    )
    async def channel_create(
        self,
        interaction: discord.Interaction,
        name: str,
        type: str = "text",
        category: Optional[discord.CategoryChannel] = None,
        topic: str = "",
    ) -> None:
        guild = interaction.guild
        if type.lower() == "voice":
            channel = await guild.create_voice_channel(name, category=category)
        else:
            channel = await guild.create_text_channel(name, category=category, topic=topic)
        await interaction.response.send_message(embed=success_embed(f"Created channel #{channel.name}"))

    @app_commands.command(name="delete")
    @admin_only()
    @app_commands.describe(channel="Channel to delete")
    async def channel_delete(self, interaction: discord.Interaction, channel: discord.abc.GuildChannel) -> None:
        name = channel.name
        await channel.delete()
        await interaction.response.send_message(embed=success_embed(f"Deleted channel #{name}"))

    @app_commands.command(name="rename")
    @admin_only()
    @app_commands.describe(channel="Channel to rename", name="New name")
    async def channel_rename(self, interaction: discord.Interaction, channel: discord.abc.GuildChannel, name: str) -> None:
        old = channel.name
        await channel.edit(name=name)
        await interaction.response.send_message(embed=success_embed(f"Renamed #{old} → #{name}"))

    @app_commands.command(name="move")
    @admin_only()
    @app_commands.describe(channel="Channel to move", category="Target category")
    async def channel_move(
        self, interaction: discord.Interaction, channel: discord.abc.GuildChannel, category: discord.CategoryChannel
    ) -> None:
        await channel.edit(category=category)
        await interaction.response.send_message(embed=success_embed(f"Moved #{channel.name} to {category.name}"))


@app_commands.guild_only()
class CategoryCog(commands.GroupCog, group_name="category"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="create")
    @admin_only()
    @app_commands.describe(name="Category name")
    async def category_create(self, interaction: discord.Interaction, name: str) -> None:
        cat = await interaction.guild.create_category(name)
        await interaction.response.send_message(embed=success_embed(f"Created category {cat.name}"))

    @app_commands.command(name="delete")
    @admin_only()
    @app_commands.describe(category="Category to delete")
    async def category_delete(self, interaction: discord.Interaction, category: discord.CategoryChannel) -> None:
        name = category.name
        await category.delete()
        await interaction.response.send_message(embed=success_embed(f"Deleted category {name}"))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminCog(bot))
    await bot.add_cog(CategoryCog(bot))
