from __future__ import annotations

import logging
from typing import Optional

import discord
from discord.ext import commands

log = logging.getLogger("ashbot.bot")


class AshBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = False
        intents.members = False
        intents.presences = False
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            owner_ids=set(),
            help_command=None,
        )
        self.initial_extensions: list[str] = [
            "ashbot.cogs.admin",
            "ashbot.cogs.moderation",
            "ashbot.cogs.automod",
            "ashbot.cogs.ai_cog",
            "ashbot.cogs.advice_cog",
            "ashbot.cogs.levels",
            "ashbot.cogs.protection",
            "ashbot.cogs.backups",
            "ashbot.cogs.logs_cog",
        ]

    async def setup_hook(self) -> None:
        for ext in self.initial_extensions:
            try:
                await self.load_extension(ext)
                log.info("Loaded extension: %s", ext)
            except Exception as e:
                log.error("Failed to load %s: %s", ext, e)

        await self.tree.sync()
        log.info("Slash commands synced")

    async def on_ready(self) -> None:
        log.info("AshBot 2 logged in as %s (ID: %s)", self.user, self.user.id)
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="over your server | /help",
            )
        )

    async def on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        log.warning("Command error: %s", error)

    async def on_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        if isinstance(error, discord.app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"Slow down! Try again in {error.retry_after:.0f}s.",
                ephemeral=True,
            )
        elif isinstance(error, discord.app_commands.CheckFailure):
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "You don't have permission to use this command.",
                    ephemeral=True,
                )
        else:
            log.error("App command error: %s", error, exc_info=error)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "An unexpected error occurred. Please try again.",
                    ephemeral=True,
                )
