from __future__ import annotations

import discord

from taskbot.services import task_service
from taskbot.utils.embed_builder import build_task_detail_embed


class TaskDetailView(discord.ui.View):
    def __init__(
        self,
        owner_id: int,
        task_id: int,
        return_mode: str = "home",
        list_type: str | None = None,
        page: int = 1,
    ):
        super().__init__(timeout=300)
        self.owner_id = owner_id
        self.task_id = task_id
        self.return_mode = return_mode
        self.list_type = list_type
        self.page = page
        self._sync_complete_button()

    async def _send_ephemeral(self, interaction: discord.Interaction, message: str) -> None:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    async def _edit_message(
        self,
        interaction: discord.Interaction,
        *,
        embed: discord.Embed,
        view: discord.ui.View,
    ) -> None:
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=view)
        else:
            await interaction.response.edit_message(embed=embed, view=view)

    def _sync_complete_button(self, status: str | None = None) -> None:
        if status is None:
            task = task_service.get_task_by_id(str(self.owner_id), self.task_id)
            status = task.get("status") if task else None

        is_done = status == "done"
        self.mark_done.label = "↩ 未完了" if is_done else "✅ 完了"
        self.mark_done.style = (
            discord.ButtonStyle.secondary if is_done else discord.ButtonStyle.success
        )

    async def _check_owner(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await self._send_ephemeral(
                interaction, "これはあなた用の操作画面ではありません。"
            )
            return False
        return True

    async def _show_detail(self, interaction: discord.Interaction) -> None:
        task = task_service.get_task_by_id(str(self.owner_id), self.task_id)
        if not task:
            await self._send_ephemeral(interaction, "タスクが見つかりませんでした。")
            return
        self._sync_complete_button(task.get("status"))
        embed = build_task_detail_embed(task)
        await self._edit_message(interaction, embed=embed, view=self)

    async def _go_home(self, interaction: discord.Interaction) -> None:
        from taskbot.views.task_home_view import build_home_message

        embed, view = build_home_message(self.owner_id)
        await self._edit_message(interaction, embed=embed, view=view)

    async def _go_list(self, interaction: discord.Interaction) -> None:
        from taskbot.views.task_list_view import build_task_list_message

        embed, view = build_task_list_message(self.owner_id, self.list_type or "todo", self.page)
        await self._edit_message(interaction, embed=embed, view=view)

    async def _go_back(self, interaction: discord.Interaction) -> None:
        if self.return_mode == "list":
            await self._go_list(interaction)
        else:
            await self._go_home(interaction)

    @discord.ui.button(label="✅ 完了", style=discord.ButtonStyle.success)
    async def mark_done(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self._check_owner(interaction):
            return
        task = task_service.get_task_by_id(str(self.owner_id), self.task_id)
        if not task:
            await self._send_ephemeral(interaction, "タスクが見つかりませんでした。")
            return

        is_done = task.get("status") == "done"
        if is_done:
            updated = task_service.reopen_task(str(self.owner_id), self.task_id)
            failed_message = "未完了に戻せませんでした。"
        else:
            updated = task_service.complete_task(str(self.owner_id), self.task_id)
            failed_message = "完了にできませんでした。"

        if not updated:
            await self._send_ephemeral(interaction, failed_message)
            return
        await self._show_detail(interaction)

    @discord.ui.button(label="✏ 編集", style=discord.ButtonStyle.secondary)
    async def edit_task(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self._check_owner(interaction):
            return
        task = task_service.get_task_by_id(str(self.owner_id), self.task_id)
        if not task:
            await self._send_ephemeral(interaction, "タスクが見つかりませんでした。")
            return
        from taskbot.views.task_modal import TaskEditModal

        await interaction.response.send_modal(
            TaskEditModal(
                owner_id=self.owner_id,
                task=task,
                return_mode=self.return_mode,
                list_type=self.list_type,
                page=self.page,
            )
        )

    @discord.ui.button(label="🗑 削除", style=discord.ButtonStyle.danger)
    async def delete_task(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self._check_owner(interaction):
            return
        if not interaction.response.is_done():
            await interaction.response.defer()
        deleted = task_service.delete_task(str(self.owner_id), self.task_id)
        if not deleted:
            await self._send_ephemeral(interaction, "削除に失敗しました。")
            return
        await self._go_back(interaction)

    @discord.ui.button(label="🔙 戻る", style=discord.ButtonStyle.secondary)
    async def go_back(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self._check_owner(interaction):
            return
        await self._go_back(interaction)
