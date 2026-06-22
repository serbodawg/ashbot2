from __future__ import annotations

import logging
import time
from collections import defaultdict, deque

import discord
from discord import app_commands
from discord.ext import commands
from google import genai

from ashbot.models import database as db
from config import AI_API_KEY, AI_MODEL

log = logging.getLogger("ashbot.ai")

CHAT_CONTEXT: dict[int, dict[int, list[dict]]] = defaultdict(lambda: defaultdict(list))
MAX_CONTEXT = 20

_client = genai.Client(api_key=AI_API_KEY) if AI_API_KEY else None
if _client:
    log.info("Gemini AI client initialized (model: %s)", AI_MODEL)

# Rate limit tracking for /how-much
_req_timestamps: deque[float] = deque()  # rolling 60s window
_req_today: int = 0
_today_date: int = 0  # date.today().toordinal()
RPM_LIMIT = 30
RPD_LIMIT = 1000


def _track_request() -> None:
    global _req_today, _today_date
    now = time.time()
    today = time.localtime(now).tm_yday

    # Reset daily counter if day changed
    if today != _today_date:
        _req_today = 0
        _today_date = today

    # Prune old entries from rolling window
    cutoff = now - 60
    while _req_timestamps and _req_timestamps[0] < cutoff:
        _req_timestamps.popleft()

    _req_timestamps.append(now)
    _req_today += 1


def _to_gemini_history(messages: list[dict]) -> list[genai.types.Content]:
    contents = []
    for m in messages:
        role = "model" if m["role"] == "assistant" else m["role"]
        contents.append({"role": role, "parts": [m["content"]]})
    return contents


async def ask_ai(system_prompt: str, messages: list[dict]) -> str:
    if not AI_API_KEY or not _client:
        return "AI module is not configured. Set AI_API_KEY in .env to enable."

    _track_request()
    try:
        config = genai.types.GenerateContentConfig(system_instruction=system_prompt)
        history = _to_gemini_history(messages[:-1]) if len(messages) > 1 else None
        last_msg = messages[-1]["content"] if messages else "Hello"

        if history:
            chat = _client.aio.chats.create(model=AI_MODEL, history=history, config=config)
            resp = await chat.send_message(last_msg)
        else:
            resp = await _client.aio.models.generate_content(
                model=AI_MODEL, contents=last_msg, config=config
            )

        text = resp.text
        return text.strip() if text else "(empty response)"
    except Exception as e:
        err = str(e)
        log.error("AI request failed: %s", err)
        if "RESOURCE_EXHAUSTED" in err or "quota" in err.lower() or "503" in err:
            return "AI quota exceeded on free tier. Please wait a moment and try again."
        return "Sorry, I couldn't process that request right now."


@app_commands.guild_only()
class AICog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return

        ai_channels = await db.get_ai_channels(message.guild.id)
        if message.channel.id not in ai_channels:
            return

        if message.content.startswith(("/", "!")):
            return

        async with message.channel.typing():
            ctx = CHAT_CONTEXT[message.guild.id][message.channel.id]
            ctx.append({"role": "user", "content": message.content})
            if len(ctx) > MAX_CONTEXT:
                ctx[:] = ctx[-MAX_CONTEXT:]

            system = (
                "You are AshBot 2, a helpful Discord assistant. "
                "Answer concisely and helpfully. Keep responses under 400 characters."
            )
            reply = await ask_ai(system, ctx)
            ctx.append({"role": "model", "content": reply})
            if len(ctx) > MAX_CONTEXT:
                ctx[:] = ctx[-MAX_CONTEXT:]

            await message.reply(reply)

    @app_commands.command(name="ask")
    @app_commands.describe(question="Your question")
    async def ask(self, interaction: discord.Interaction, question: str) -> None:
        await interaction.response.defer()
        system = "You are AshBot 2, a helpful assistant. Answer clearly and concisely."
        reply = await ask_ai(system, [{"role": "user", "content": question}])
        await interaction.followup.send(reply)

    @app_commands.command(name="how-much")
    async def how_much(self, interaction: discord.Interaction) -> None:
        now = time.time()
        cutoff = now - 60
        rpm_used = sum(1 for t in _req_timestamps if t >= cutoff)
        rpd_used = _req_today

        embed = discord.Embed(
            title="AI Usage",
            color=0x4FC3F7,
            fields=[
                discord.EmbedField(
                    name="Per Minute",
                    value=f"**{rpm_used}** / {RPM_LIMIT} requests",
                    inline=True,
                ),
                discord.EmbedField(
                    name="Per Day",
                    value=f"**{rpd_used}** / {RPD_LIMIT} requests",
                    inline=True,
                ),
                discord.EmbedField(
                    name="Model",
                    value=AI_MODEL,
                    inline=False,
                ),
            ],
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ai-disable")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(channel="Channel to disable AI in")
    async def ai_disable(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        await db.set_ai_channel(interaction.guild.id, channel.id, False)
        CHAT_CONTEXT[interaction.guild.id].pop(channel.id, None)
        await interaction.response.send_message(f"AI disabled in {channel.mention}")

    @app_commands.command(name="ai-enable")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(channel="Channel to enable AI in")
    async def ai_enable(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        await db.set_ai_channel(interaction.guild.id, channel.id, True)
        await interaction.response.send_message(f"AI enabled in {channel.mention}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AICog(bot))
