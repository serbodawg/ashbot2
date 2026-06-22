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
        if not isinstance(interaction.user, discord.Member):
            return False
        guild = interaction.guild
        if not guild:
            return False
        # Server owner always passes
        if guild.owner_id == interaction.user.id:
            return True
        # Check role hierarchy: top 3 highest roles (excluding @everyone)
        sorted_roles = sorted(
            [r for r in guild.roles if not r.is_default()],
            key=lambda r: r.position,
            reverse=True,
        )
        top_positions = [r.position for r in sorted_roles[:3]]
        if not top_positions:
            await interaction.response.send_message(
                "No high enough role found.", ephemeral=True,
            )
            return False
        min_required = top_positions[-1]  # lowest of the top 3
        if interaction.user.top_role.position >= min_required:
            return True
        await interaction.response.send_message(
            "You need a top-tier role (top 3) to use this command.", ephemeral=True,
        )
        return False
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
