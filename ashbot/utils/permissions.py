from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


async def is_admin(interaction: discord.Interaction) -> bool:
    if not isinstance(interaction.user, discord.Member):
        return False
    return interaction.user.guild_permissions.administrator


async def is_mod(interaction: discord.Interaction) -> bool:
    if not isinstance(interaction.user, discord.Member):
        return False
    return (
        interaction.user.guild_permissions.administrator
        or interaction.user.guild_permissions.manage_guild
        or interaction.user.guild_permissions.ban_members
    )


async def is_owner(interaction: discord.Interaction) -> bool:
    from config import OWNER_IDS
    return interaction.user.id in OWNER_IDS


def admin_only():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not await is_admin(interaction):
            await interaction.response.send_message("You need Administrator permission to use this command.", ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)


def mod_only():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not await is_mod(interaction):
            await interaction.response.send_message("You need Moderator permissions to use this command.", ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)


class GuildOnly(commands.CheckFailure):
    pass


def guild_only():
    async def predicate(ctx: commands.Context | discord.Interaction) -> bool:
        if isinstance(ctx, discord.Interaction):
            if ctx.guild is None:
                raise GuildOnly("This command can only be used in a server.")
        else:
            if ctx.guild is None:
                raise GuildOnly("This command can only be used in a server.")
        return True
    return app_commands.check(predicate)
