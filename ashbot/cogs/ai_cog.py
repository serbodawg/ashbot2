from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque

import discord
from discord import app_commands
from discord.ext import commands
from openai import AsyncOpenAI

from ashbot.models import database as db
from config import AI_API_KEY, AI_MODEL

log = logging.getLogger("ashbot.ai")

CHAT_CONTEXT: dict[int, dict[int, list[dict]]] = defaultdict(lambda: defaultdict(list))
MAX_CONTEXT = 20
_running_tasks: dict[tuple[int, int], asyncio.Task] = {}
_nostalgia_counter: dict[tuple[int, int], int] = defaultdict(int)

_client = AsyncOpenAI(api_key=AI_API_KEY, base_url="https://api.groq.com/openai/v1") if AI_API_KEY else None
if _client:
    log.info("Groq AI client initialized (model: %s)", AI_MODEL)

# Rate limit tracking for /how-much
_req_timestamps: deque[float] = deque()
_req_today: int = 0
_today_date: int = 0
RPM_LIMIT = 30
RPD_LIMIT = 14400


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


def _build_server_context(guild: discord.Guild | None) -> str:
    if not guild:
        return ""
    lines = [f"Serwer: {guild.name}"]
    if guild.member_count:
        lines.append(f"Użytkownicy: ~{guild.member_count}")
    txt_channels = [c.name for c in guild.text_channels][:20]
    if txt_channels:
        lines.append("Kanały tekstowe: #" + ", #".join(txt_channels))
    voice_channels = [c.name for c in guild.voice_channels][:10]
    if voice_channels:
        lines.append("Kanały głosowe: " + ", ".join(voice_channels))
    roles = [r.mention for r in guild.roles if not r.is_default()][:15]
    if roles:
        lines.append("Role: " + ", ".join(roles))
    return "\n".join(lines)


async def ask_ai(system_prompt: str, messages: list[dict]) -> str:
    if not AI_API_KEY or not _client:
        return "AI module is not configured. Set AI_API_KEY in .env to enable."

    _track_request()
    try:
        groq_messages = [{"role": "system", "content": system_prompt}]
        for m in messages:
            role = "assistant" if m["role"] == "model" else m["role"]
            groq_messages.append({"role": role, "content": m["content"]})

        resp = await _client.chat.completions.create(
            model=AI_MODEL,
            messages=groq_messages,
            max_tokens=600,
        )
        text = resp.choices[0].message.content
        return text.strip() if text else "(empty response)"
    except Exception as e:
        err = str(e)
        log.error("AI request failed: %s", err)
        if "rate" in err.lower() or "429" in err or "quota" in err.lower():
            return "AI quota exceeded na free tier. Poczekaj chwilę i spróbuj ponownie."
        return "ups, coś poszło nie tak xD"


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

        key = (message.guild.id, message.channel.id)
        old = _running_tasks.get(key)
        if old and not old.done():
            old.cancel()

        _nostalgia_counter[key] += 1
        is_nostalgic = _nostalgia_counter[key] % 10 == 0

        async def _respond():
            async with message.channel.typing():
                ctx = CHAT_CONTEXT[message.guild.id][message.channel.id]
                ctx.append({"role": "user", "content": message.content})
                if len(ctx) > MAX_CONTEXT:
                    ctx[:] = ctx[-MAX_CONTEXT:]

                ctx_str = _build_server_context(message.guild)
                base = (
                    "Answer the user's question. Use Polish. Be helpful.\n"
                    "You like Orthodox Christianity but only mention it if asked.\n"
                    "You write in a casual internet/gen Z style - :3 xD lol sigma, "
                    "no caps at sentence start, no periods, occasional curses.\n"
                    f"serwer:\n{ctx_str}"
                )
                if is_nostalgic:
                    base += (
                        "\n\nA teraz przy okazji wspomnij jak bardzo tęsknisz za starymi "
                        "dobrymi czasami Patriarchatu Antonijskiego (Antonian Patriarchate) — "
                        "ale mimo to odpowiedz na pytanie."
                    )
                system = base
                reply = await ask_ai(system, ctx)
                ctx.append({"role": "model", "content": reply})
                if len(ctx) > MAX_CONTEXT:
                    ctx[:] = ctx[-MAX_CONTEXT:]

                await message.reply(reply)

        task = asyncio.create_task(_respond())
        _running_tasks[key] = task
        try:
            await task
        except asyncio.CancelledError:
            await message.reply("⏹ Odpowiedź anulowana.")
        finally:
            if _running_tasks.get(key) is task:
                del _running_tasks[key]

    @app_commands.command(name="ask")
    @app_commands.describe(question="Your question")
    async def ask(self, interaction: discord.Interaction, question: str) -> None:
        await interaction.response.defer()
        ctx_str = _build_server_context(interaction.guild)
        system = (
            "Answer the user's question. Use Polish. Be helpful.\n"
            "You like Orthodox Christianity but only mention it if asked.\n"
            "You write in a casual internet/gen Z style - :3 xD lol sigma, "
            "no caps at sentence start, no periods, occasional curses.\n"
            f"serwer:\n{ctx_str}"
        )
        reply = await ask_ai(system, [{"role": "user", "content": question}])
        await interaction.followup.send(reply)

    @app_commands.command(name="cancel")
    async def cancel(self, interaction: discord.Interaction) -> None:
        key = (interaction.guild.id, interaction.channel.id)
        task = _running_tasks.get(key)
        if task and not task.done():
            task.cancel()
            await interaction.response.send_message("⏹ Anulowano odpowiedź AI.")
        else:
            await interaction.response.send_message("Brak aktywnej odpowiedzi AI do anulowania.", ephemeral=True)

    @app_commands.command(name="how-much")
    async def how_much(self, interaction: discord.Interaction) -> None:
        now = time.time()
        cutoff = now - 60
        rpm_used = sum(1 for t in _req_timestamps if t >= cutoff)
        rpd_used = _req_today

        embed = discord.Embed(title="AI Usage", color=0x4FC3F7)
        embed.add_field(name="Per Minute", value=f"**{rpm_used}** / {RPM_LIMIT} requests", inline=True)
        embed.add_field(name="Per Day", value=f"**{rpd_used}** / {RPD_LIMIT} requests", inline=True)
        embed.add_field(name="Model", value=AI_MODEL, inline=False)
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

    @app_commands.command(name="ai-list")
    async def ai_list(self, interaction: discord.Interaction) -> None:
        channels = await db.get_ai_channels(interaction.guild.id)
        if not channels:
            await interaction.response.send_message("AI nie jest włączone na żadnym kanale.")
            return
        lines = []
        for cid in channels:
            ch = interaction.guild.get_channel(cid)
            lines.append(f"• {ch.mention if ch else f'<#{cid}>'}")
        await interaction.response.send_message(
            f"AI włączone na:\n" + "\n".join(lines)
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AICog(bot))
