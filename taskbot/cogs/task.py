from __future__ import annotations

import discord
from discord.ext import commands

from taskbot.views.task_config_view import build_config_message
from taskbot.views.task_home_view import build_home_message


class TaskCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.slash_command(name="task", description="タスク管理画面を開く")
    async def task(self, ctx: discord.ApplicationContext):
        embed, view = build_home_message(ctx.author.id)
        await ctx.respond(embed=embed, view=view, ephemeral=True)

    @discord.slash_command(name="taskconfig", description="タスク通知の設定を開く")
    async def taskconfig(self, ctx: discord.ApplicationContext):
        embed, view = build_config_message(ctx.author.id)
        await ctx.respond(embed=embed, view=view, ephemeral=True)
