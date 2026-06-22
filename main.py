from __future__ import annotations

import asyncio
import threading

from config import DISCORD_TOKEN, log
from ashbot.bot import AshBot
from ashbot.dashboard.server import start_dashboard

log.info("Starting AshBot 2...")


def run_dashboard(bot: AshBot) -> None:
    start_dashboard(bot)


async def main() -> None:
    bot = AshBot()

    t = threading.Thread(target=run_dashboard, args=(bot,), daemon=True)
    t.start()

    async with bot:
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
