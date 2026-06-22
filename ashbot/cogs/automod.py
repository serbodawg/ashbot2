from __future__ import annotations

import logging
import re
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

import discord
from discord.ext import commands

from ashbot.models import database as db
from ashbot.utils.embeds import warning_embed, error_embed

log = logging.getLogger("ashbot.automod")

INVITE_RE = re.compile(r"(?:discord\.(?:gg|io|me|com\/invite)\/)[a-zA-Z0-9]+", re.I)
URL_RE = re.compile(r"https?://[^\s]+", re.I)
CAPS_RE = re.compile(r"[A-Z]{4,}")


class AutoModCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.recent_messages: dict[int, dict[int, list[tuple[float, str]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self.raid_detection: dict[int, dict[int, float]] = defaultdict(dict)

    async def is_automod_enabled(self, guild_id: int) -> bool:
        config = await db.get_guild_config(guild_id)
        return config.get("automod_enabled", False) if config else False

    async def should_ignore_channel(self, guild_id: int, channel_id: int) -> bool:
        ai_channels = await db.get_ai_channels(guild_id)
        return channel_id in ai_channels

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return
        if not await self.is_automod_enabled(message.guild.id):
            return

        guild_id = message.guild.id
        user_id = message.author.id
        now = message.created_at.timestamp()
        content = message.content

        violations: list[str] = []

        # Anti-spam: check message frequency
        msgs = self.recent_messages[guild_id][user_id]
        msgs.append((now, content))
        cutoff = now - 5
        msgs[:] = [(t, c) for t, c in msgs if t > cutoff]

        if len(msgs) >= 5:
            violations.append("Spam (5+ messages in 5s)")

        # Anti-repeat: identical content
        if len({c for _, c in msgs[-3:]}) == 1 and len(msgs) >= 3:
            violations.append("Message repeat")

        # Anti-link
        if not await self.should_ignore_channel(guild_id, message.channel.id):
            if URL_RE.search(content):
                config = await db.get_guild_config(guild_id)
                if config.get("antilink", True):
                    violations.append("Links not allowed")

        # Anti-invite
        if INVITE_RE.search(content):
            violations.append("Discord invite not allowed")

        # Anti-caps
        if len(content) > 8:
            caps = CAPS_RE.findall(content)
            total_caps_chars = sum(len(m) for m in caps)
            if total_caps_chars > len(content) * 0.5 and len(content) > 10:
                violations.append("Excessive caps")

        # Anti-mention spam
        if len(message.mentions) > 5:
            violations.append("Mention spam")

        if violations:
            try:
                await message.delete()
                warning_text = f"Auto-mod: {', '.join(violations)}"
                await db.add_warning(guild_id, user_id, self.bot.user.id, warning_text)
                warn_count = len(await db.get_warnings(guild_id, user_id))
                embed = warning_embed(
                    f"Auto-mod warning for {message.author}",
                    f"Reason: {', '.join(violations)}\nTotal warnings: {warn_count}",
                )
                await message.channel.send(embed=embed, delete_after=10)
                log.info("Auto-mod action on %s in %s: %s", user_id, guild_id, violations)
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        guild_id = member.guild.id
        now = datetime.utcnow().timestamp()

        self.raid_detection[guild_id][member.id] = now
        cutoff = now - 30
        recent = [t for t in self.raid_detection[guild_id].values() if t > cutoff]

        if len(recent) >= 10:
            config = await db.get_guild_config(guild_id)
            if config.get("antyraid", True):
                log.warning("Raid detected in %s: %d joins in 30s", guild_id, len(recent))
                for channel_id in (await db.get_log_channels(guild_id)).values():
                    try:
                        ch = member.guild.get_channel(channel_id)
                        if ch and isinstance(ch, discord.TextChannel):
                            await ch.send(
                                embed=error_embed(
                                    "Raid detected!",
                                    f"{len(recent)} members joined in 30s. Consider enabling lockdown.",
                                )
                            )
                    except Exception:
                        pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutoModCog(bot))
