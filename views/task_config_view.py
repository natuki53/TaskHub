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

    async def _check_owner(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "これはあなた用の操作画面ではありません。", ephemeral=True
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

        minutes = int(self.reminder_select.values[0])
        reminders_enabled = minutes > 0
        task_service.upsert_user_settings(
            user_id=str(self.owner_id),
            reminders_enabled=reminders_enabled,
            reminder_minutes=minutes if minutes > 0 else 0,
        )

        self.settings = task_service.get_user_settings(str(self.owner_id))
        self.reminder_select.options = self._build_options(self.settings)
        embed = build_config_embed(self.settings)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🔙 ホーム", style=discord.ButtonStyle.secondary)
    async def go_home(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self._check_owner(interaction):
            return
        from taskbot.views.task_home_view import build_home_message

        embed, view = build_home_message(self.owner_id)
        await interaction.response.edit_message(embed=embed, view=view)
