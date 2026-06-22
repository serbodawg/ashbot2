from __future__ import annotations

import discord


def success_embed(title: str, description: str = "") -> discord.Embed:
    return discord.Embed(title=title, description=description, color=0x22C55E)


def error_embed(title: str, description: str = "") -> discord.Embed:
    return discord.Embed(title=title, description=description, color=0xEF4444)


def info_embed(title: str, description: str = "") -> discord.Embed:
    return discord.Embed(title=title, description=description, color=0x3B82F6)


def warning_embed(title: str, description: str = "") -> discord.Embed:
    return discord.Embed(title=title, description=description, color=0xF59E0B)
