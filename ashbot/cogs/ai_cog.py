from __future__ import annotations

import logging
from collections import defaultdict

import discord
from discord import app_commands
from discord.ext import commands
import google.generativeai as genai

from ashbot.models import database as db
from config import AI_API_KEY, AI_MODEL

log = logging.getLogger("ashbot.ai")

CHAT_CONTEXT: dict[int, dict[int, list[dict]]] = defaultdict(lambda: defaultdict(list))
MAX_CONTEXT = 20

genai.configure(api_key=AI_API_KEY) if AI_API_KEY else None


def _to_gemini_history(messages: list[dict]) -> list[dict]:
    history = []
    for m in messages:
        role = "model" if m["role"] == "assistant" else "user"
        history.append({"role": role, "parts": [m["content"]]})
    return history


async def ask_ai(system_prompt: str, messages: list[dict]) -> str:
    if not AI_API_KEY:
        return "AI module is not configured. Set AI_API_KEY in .env to enable."

    try:
        model = genai.GenerativeModel(
            model_name=AI_MODEL,
            system_instruction=system_prompt,
        )

        history = _to_gemini_history(messages[:-1]) if len(messages) > 1 else []
        last_msg = messages[-1]["content"] if messages else "Hello"

        if history:
            chat = model.start_chat(history=history)
            resp = await chat.send_message_async(last_msg)
        else:
            resp = await model.generate_content_async(last_msg)

        return resp.text.strip()
    except Exception as e:
        log.error("AI request failed: %s", e)
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
            ctx.append({"role": "assistant", "content": reply})
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
