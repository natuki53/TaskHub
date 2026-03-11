from __future__ import annotations

import math
from typing import List

import discord

from taskbot.services import task_service
from taskbot.utils.embed_builder import build_task_list_embed

LIST_TITLES = {
    "todo": "未完了一覧",
    "done": "完了済み一覧",
    "today": "今日のタスク",
    "overdue": "期限切れタスク",
}


def build_task_list_message(
    owner_id: int, list_type: str, page: int
) -> tuple[discord.Embed, discord.ui.View]:
    tasks, total = task_service.list_tasks(str(owner_id), list_type, page)
    page_count = max(1, math.ceil(total / 10))
    embed = build_task_list_embed(tasks, LIST_TITLES[list_type], page, page_count)
    view = TaskListView(owner_id, list_type, page, total, tasks)
    return embed, view


class TaskListView(discord.ui.View):
    def __init__(
        self,
        owner_id: int,
        list_type: str,
        page: int,
        total: int,
        tasks: List[dict],
        per_page: int = 10,
    ):
        super().__init__(timeout=300)
        self.owner_id = owner_id
        self.list_type = list_type
        self.page = page
        self.per_page = per_page
        self.total = total
        self.page_count = max(1, math.ceil(total / per_page))

        self.task_select = discord.ui.Select(
            placeholder="タスクを選択",
            options=self._build_options(tasks),
            min_values=1,
            max_values=1,
            disabled=len(tasks) == 0,
        )
        self.task_select.callback = self._on_task_select
        self.add_item(self.task_select)

        self._update_nav_buttons()

    async def _check_owner(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "これはあなた用の操作画面ではありません。", ephemeral=True
            )
            return False
        return True

    def _build_options(self, tasks: List[dict]) -> List[discord.SelectOption]:
        options: List[discord.SelectOption] = []
        for task in tasks:
            label = f"#{task['id']} {task['title']}"
            label = label if len(label) <= 100 else label[:97] + "..."
            description = task.get("due_at") or "締切なし"
            options.append(
                discord.SelectOption(
                    label=label,
                    description=description[:100],
                    value=str(task["id"]),
                )
            )
        return options

    def _update_nav_buttons(self) -> None:
        self.prev_page.disabled = self.page <= 1
        self.next_page.disabled = self.page >= self.page_count

    async def _refresh(self, interaction: discord.Interaction) -> None:
        tasks, total = task_service.list_tasks(
            str(self.owner_id), self.list_type, self.page, self.per_page
        )
        self.total = total
        self.page_count = max(1, math.ceil(total / self.per_page))

        if self.page > self.page_count:
            self.page = self.page_count
            tasks, total = task_service.list_tasks(
                str(self.owner_id), self.list_type, self.page, self.per_page
            )
            self.total = total
            self.page_count = max(1, math.ceil(total / self.per_page))

        self.task_select.options = self._build_options(tasks)
        self.task_select.disabled = len(tasks) == 0
        self._update_nav_buttons()

        embed = build_task_list_embed(
            tasks, LIST_TITLES[self.list_type], self.page, self.page_count
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def _on_task_select(self, interaction: discord.Interaction):
        if not await self._check_owner(interaction):
            return

        task_id = int(self.task_select.values[0])
        task = task_service.get_task_by_id(str(self.owner_id), task_id)
        if not task:
            await interaction.response.send_message(
                "タスクが見つかりませんでした。", ephemeral=True
            )
            return

        from taskbot.views.task_detail_view import TaskDetailView
        from taskbot.utils.embed_builder import build_task_detail_embed

        embed = build_task_detail_embed(task)
        view = TaskDetailView(
            owner_id=self.owner_id,
            task_id=task_id,
            return_mode="list",
            list_type=self.list_type,
            page=self.page,
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="◀ 前へ", style=discord.ButtonStyle.secondary)
    async def prev_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self._check_owner(interaction):
            return
        if self.page > 1:
            self.page -= 1
        await self._refresh(interaction)

    @discord.ui.button(label="次へ ▶", style=discord.ButtonStyle.secondary)
    async def next_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self._check_owner(interaction):
            return
        if self.page < self.page_count:
            self.page += 1
        await self._refresh(interaction)

    @discord.ui.button(label="🔙 ホーム", style=discord.ButtonStyle.secondary)
    async def go_home(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self._check_owner(interaction):
            return
        from taskbot.views.task_home_view import build_home_message

        embed, view = build_home_message(self.owner_id)
        await interaction.response.edit_message(embed=embed, view=view)
