from __future__ import annotations

import discord

from taskbot.services import task_service
from taskbot.utils.embed_builder import build_config_embed

REMINDER_OPTIONS = [
    ("5分前", 5, "締切の5分前に通知"),
    ("10分前", 10, "締切の10分前に通知"),
    ("30分前", 30, "締切の30分前に通知"),
    ("60分前", 60, "締切の60分前に通知"),
    ("オフ", 0, "通知しない"),
]


def build_config_message(owner_id: int) -> tuple[discord.Embed, discord.ui.View]:
    settings = task_service.get_user_settings(str(owner_id))
    embed = build_config_embed(settings)
    view = TaskConfigView(owner_id, settings)
    return embed, view


class TaskConfigView(discord.ui.View):
    def __init__(self, owner_id: int, settings: dict):
        super().__init__(timeout=300)
        self.owner_id = owner_id
        self.settings = settings

        self.reminder_select = discord.ui.Select(
            placeholder="リマインド通知のタイミング",
            options=self._build_options(settings),
            min_values=1,
            max_values=1,
        )
        self.reminder_select.callback = self._on_select
        self.add_item(self.reminder_select)

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

    def _selected_minutes_from_interaction(
        self, interaction: discord.Interaction
    ) -> int | None:
        raw_value: str | None = None

        data = interaction.data or {}
        values = data.get("values")
        if isinstance(values, list) and values:
            raw_value = str(values[0])
        elif self.reminder_select.values:
            raw_value = str(self.reminder_select.values[0])

        if raw_value is None:
            return None

        try:
            return int(raw_value)
        except ValueError:
            return None

    async def _check_owner(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await self._send_ephemeral(
                interaction, "これはあなた用の操作画面ではありません。"
            )
            return False
        return True

    def _build_options(self, settings: dict) -> list[discord.SelectOption]:
        reminders_enabled = bool(int(settings.get("reminders_enabled", 1)))
        minutes = int(settings.get("reminder_minutes", 5))
        current_value = 0 if not reminders_enabled else minutes

        options: list[discord.SelectOption] = []
        for label, value, description in REMINDER_OPTIONS:
            options.append(
                discord.SelectOption(
                    label=label,
                    value=str(value),
                    description=description,
                    default=value == current_value,
                )
            )
        return options

    async def _on_select(self, interaction: discord.Interaction):
        if not await self._check_owner(interaction):
            return

        minutes = self._selected_minutes_from_interaction(interaction)
        if minutes is None:
            await self._send_ephemeral(
                interaction, "設定値の読み取りに失敗しました。もう一度選択してください。"
            )
            return

        reminders_enabled = minutes > 0
        task_service.upsert_user_settings(
            user_id=str(self.owner_id),
            reminders_enabled=reminders_enabled,
            reminder_minutes=minutes if minutes > 0 else 0,
        )

        self.settings = task_service.get_user_settings(str(self.owner_id))
        self.reminder_select.options = self._build_options(self.settings)
        embed = build_config_embed(self.settings)
        await self._edit_message(interaction, embed=embed, view=self)

    @discord.ui.button(label="✖ 終了", style=discord.ButtonStyle.secondary)
    async def close(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self._check_owner(interaction):
            return

        await interaction.response.defer()
        try:
            await interaction.delete_original_response()
        except discord.HTTPException:
            if interaction.message is not None:
                try:
                    await interaction.message.delete()
                except discord.HTTPException:
                    await interaction.edit_original_response(content=None, embed=None, view=None)
