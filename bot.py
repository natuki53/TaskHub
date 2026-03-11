from __future__ import annotations

import logging
from datetime import timedelta

import discord
from discord.ext import commands, tasks

from taskbot.config import DISCORD_TOKEN
from taskbot.cogs.task import TaskCog
from taskbot.database.db import init_db
from taskbot.services import task_service
from taskbot.utils.datetime_parser import now_local, to_storage_string
from taskbot.utils.embed_builder import build_reminder_embed

logging.basicConfig(level=logging.INFO)


class ReminderScheduler:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reminder_loop.start()

    def stop(self) -> None:
        if self.reminder_loop.is_running():
            self.reminder_loop.cancel()

    @tasks.loop(seconds=60)
    async def reminder_loop(self) -> None:
        max_minutes = task_service.get_max_reminder_minutes()
        due_tasks = task_service.list_upcoming_reminders(max_minutes=max_minutes, limit=200)
        if not due_tasks:
            return

        now = now_local()
        now_str = to_storage_string(now)
        settings_cache: dict[str, dict] = {}

        for task in due_tasks:
            user_id = str(task["user_id"])
            due_at = task.get("due_at")
            if not due_at or due_at < now_str:
                continue

            settings = settings_cache.get(user_id)
            if settings is None:
                settings = task_service.get_user_settings(user_id)
                settings_cache[user_id] = settings

            reminders_enabled = bool(int(settings.get("reminders_enabled", 1)))
            minutes = int(settings.get("reminder_minutes", 5))
            if not reminders_enabled or minutes <= 0:
                continue

            window_end_str = to_storage_string(now + timedelta(minutes=minutes))
            if due_at > window_end_str:
                continue

            user = self.bot.get_user(int(user_id))
            if user is None:
                try:
                    user = await self.bot.fetch_user(int(user_id))
                except discord.NotFound:
                    task_service.mark_task_reminded(user_id, task["id"])
                    continue
                except discord.HTTPException:
                    continue

            try:
                await user.send(embed=build_reminder_embed(task))
            except discord.Forbidden:
                # DM拒否などでも無限ループを避けるため記録だけ更新
                task_service.mark_task_reminded(user_id, task["id"])
                continue
            except discord.HTTPException:
                continue

            task_service.mark_task_reminded(user_id, task["id"])

    @reminder_loop.before_loop
    async def before_reminder_loop(self) -> None:
        await self.bot.wait_until_ready()


def main() -> None:
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN が設定されていません")

    init_db()

    intents = discord.Intents.default()
    bot = commands.Bot(intents=intents)

    @bot.event
    async def on_ready():
        logging.info("Logged in as %s", bot.user)

    bot.add_cog(TaskCog(bot))
    bot.reminder_scheduler = ReminderScheduler(bot)
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
