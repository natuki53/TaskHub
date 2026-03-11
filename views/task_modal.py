from __future__ import annotations

import discord

from taskbot.services import task_service
from taskbot.utils.datetime_parser import parse_due_datetime, to_storage_string
from taskbot.utils.embed_builder import build_task_detail_embed
from taskbot.views.task_detail_view import TaskDetailView

ALLOWED_PRIORITY = {"low", "medium", "high"}


class TaskCreateModal(discord.ui.Modal):
    def __init__(self, owner_id: int):
        super().__init__(title="タスク追加")
        self.owner_id = owner_id

        self.title_input = discord.ui.InputText(
            label="タイトル",
            placeholder="タスクのタイトル",
            required=True,
            max_length=100,
        )
        self.description_input = discord.ui.InputText(
            label="説明",
            placeholder="任意",
            style=discord.InputTextStyle.long,
            required=False,
            max_length=1000,
        )
        self.due_input = discord.ui.InputText(
            label="締切",
            placeholder="YYYY-MM-DD または YYYY-MM-DD HH:MM",
            required=False,
        )
        self.priority_input = discord.ui.InputText(
            label="優先度",
            placeholder="low / medium / high (未指定は medium)",
            required=False,
        )

        self.add_item(self.title_input)
        self.add_item(self.description_input)
        self.add_item(self.due_input)
        self.add_item(self.priority_input)

    async def callback(self, interaction: discord.Interaction):
        title = self.title_input.value.strip()
        description = self.description_input.value.strip() or None
        due_raw = self.due_input.value.strip()
        priority_raw = self.priority_input.value.strip().lower() or "medium"

        if priority_raw not in ALLOWED_PRIORITY:
            await interaction.response.send_message(
                "優先度は low / medium / high のいずれかで指定してください。", ephemeral=True
            )
            return

        try:
            due_dt = parse_due_datetime(due_raw)
        except ValueError:
            await interaction.response.send_message(
                "締切の形式が正しくありません。YYYY-MM-DD または YYYY-MM-DD HH:MM で入力してください。",
                ephemeral=True,
            )
            return

        due_at = to_storage_string(due_dt) if due_dt else None
        task_id = task_service.create_task(
            user_id=str(self.owner_id),
            title=title,
            description=description,
            due_at=due_at,
            priority=priority_raw,
        )

        task = task_service.get_task_by_id(str(self.owner_id), task_id)
        if not task:
            await interaction.response.send_message(
                "タスクの作成に失敗しました。", ephemeral=True
            )
            return

        embed = build_task_detail_embed(task)
        view = TaskDetailView(owner_id=self.owner_id, task_id=task_id, return_mode="home")
        await interaction.response.edit_message(embed=embed, view=view)


class TaskEditModal(discord.ui.Modal):
    def __init__(
        self,
        owner_id: int,
        task: dict,
        return_mode: str = "home",
        list_type: str | None = None,
        page: int = 1,
    ):
        super().__init__(title="タスク編集")
        self.owner_id = owner_id
        self.task_id = int(task["id"])
        self.return_mode = return_mode
        self.list_type = list_type
        self.page = page
        self.default_priority = task.get("priority") or "medium"

        self.title_input = discord.ui.InputText(
            label="タイトル",
            value=task.get("title") or "",
            required=True,
            max_length=100,
        )
        self.description_input = discord.ui.InputText(
            label="説明",
            value=task.get("description") or "",
            style=discord.InputTextStyle.long,
            required=False,
            max_length=1000,
        )
        self.due_input = discord.ui.InputText(
            label="締切",
            value=task.get("due_at") or "",
            placeholder="YYYY-MM-DD または YYYY-MM-DD HH:MM",
            required=False,
        )
        self.priority_input = discord.ui.InputText(
            label="優先度",
            value=self.default_priority,
            placeholder="low / medium / high",
            required=False,
        )

        self.add_item(self.title_input)
        self.add_item(self.description_input)
        self.add_item(self.due_input)
        self.add_item(self.priority_input)

    async def callback(self, interaction: discord.Interaction):
        title = self.title_input.value.strip()
        description = self.description_input.value.strip() or None
        due_raw = self.due_input.value.strip()
        priority_raw = self.priority_input.value.strip().lower()

        if not priority_raw:
            priority = self.default_priority
        elif priority_raw in ALLOWED_PRIORITY:
            priority = priority_raw
        else:
            await interaction.response.send_message(
                "優先度は low / medium / high のいずれかで指定してください。", ephemeral=True
            )
            return

        try:
            due_dt = parse_due_datetime(due_raw)
        except ValueError:
            await interaction.response.send_message(
                "締切の形式が正しくありません。YYYY-MM-DD または YYYY-MM-DD HH:MM で入力してください。",
                ephemeral=True,
            )
            return

        due_at = to_storage_string(due_dt) if due_dt else None
        updated = task_service.update_task(
            user_id=str(self.owner_id),
            task_id=self.task_id,
            title=title,
            description=description,
            due_at=due_at,
            priority=priority,
        )

        if not updated:
            await interaction.response.send_message(
                "更新に失敗しました。", ephemeral=True
            )
            return

        task = task_service.get_task_by_id(str(self.owner_id), self.task_id)
        if not task:
            await interaction.response.send_message(
                "タスクが見つかりませんでした。", ephemeral=True
            )
            return

        embed = build_task_detail_embed(task)
        view = TaskDetailView(
            owner_id=self.owner_id,
            task_id=self.task_id,
            return_mode=self.return_mode,
            list_type=self.list_type,
            page=self.page,
        )
        await interaction.response.edit_message(embed=embed, view=view)
