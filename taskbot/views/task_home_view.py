from __future__ import annotations

import discord

from taskbot.services import task_service
from taskbot.utils.embed_builder import build_home_embed


def build_home_message(owner_id: int) -> tuple[discord.Embed, discord.ui.View]:
    summary = task_service.count_task_summary(str(owner_id))
    embed = build_home_embed(summary)
    view = TaskHomeView(owner_id)
    return embed, view


class TaskHomeView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=300)
        self.owner_id = owner_id

    async def _check_owner(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "これはあなた用の操作画面ではありません。", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="➕ タスク追加", style=discord.ButtonStyle.primary)
    async def add_task(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self._check_owner(interaction):
            return
        from taskbot.views.task_modal import TaskCreateModal

        await interaction.response.send_modal(TaskCreateModal(owner_id=self.owner_id))

    @discord.ui.button(label="📋 未完了一覧", style=discord.ButtonStyle.secondary)
    async def list_todo(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self._check_owner(interaction):
            return
        from taskbot.views.task_list_view import build_task_list_message

        embed, view = build_task_list_message(self.owner_id, list_type="todo", page=1)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="✅ 完了済み一覧", style=discord.ButtonStyle.secondary)
    async def list_done(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self._check_owner(interaction):
            return
        from taskbot.views.task_list_view import build_task_list_message

        embed, view = build_task_list_message(self.owner_id, list_type="done", page=1)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="📅 今日のタスク", style=discord.ButtonStyle.secondary)
    async def list_today(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self._check_owner(interaction):
            return
        from taskbot.views.task_list_view import build_task_list_message

        embed, view = build_task_list_message(self.owner_id, list_type="today", page=1)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="⚠ 期限切れタスク", style=discord.ButtonStyle.secondary)
    async def list_overdue(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self._check_owner(interaction):
            return
        from taskbot.views.task_list_view import build_task_list_message

        embed, view = build_task_list_message(self.owner_id, list_type="overdue", page=1)
        await interaction.response.edit_message(embed=embed, view=view)
