from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional, cast

import discord
from discord.components import InputText as InputTextComponent
from discord.enums import ComponentType
from discord.ui.item import ModalItem

from taskbot.services import task_service
from taskbot.utils.datetime_parser import now_local
from taskbot.utils.embed_builder import build_task_detail_embed
from taskbot.views.task_detail_view import TaskDetailView

ALLOWED_PRIORITY = {"low", "medium", "high"}
DEFAULT_PRIORITY = "medium"
NONE_VALUE = "__none__"
WEEKDAYS_JA = ["月", "火", "水", "木", "金", "土", "日"]
PRIORITY_OPTIONS = [
    ("high", "高"),
    ("medium", "中"),
    ("low", "低"),
]
TIME_TRANSLATION_TABLE = str.maketrans(
    {
        "０": "0",
        "１": "1",
        "２": "2",
        "３": "3",
        "４": "4",
        "５": "5",
        "６": "6",
        "７": "7",
        "８": "8",
        "９": "9",
        "：": ":",
        "　": " ",
    }
)


def _normalize_priority(value: Optional[str]) -> str:
    raw = (value or "").strip().lower()
    return raw if raw in ALLOWED_PRIORITY else DEFAULT_PRIORITY


def _extract_due_date(due_at: Optional[str]) -> Optional[str]:
    if not due_at:
        return None

    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(due_at, fmt)
            return parsed.date().isoformat()
        except ValueError:
            continue
    return None


def _extract_due_time(due_at: Optional[str]) -> Optional[str]:
    if not due_at:
        return None

    try:
        parsed = datetime.strptime(due_at, "%Y-%m-%d %H:%M")
        return parsed.strftime("%H:%M")
    except ValueError:
        return None


def _validate_due_time_text(value: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    raw = (value or "").strip()
    if not raw:
        return None, None

    normalized = re.sub(r"\s+", "", raw.translate(TIME_TRANSLATION_TABLE))
    matched = re.fullmatch(r"(\d{1,2}):(\d{1,2})", normalized)
    if not matched:
        return None, "時間は HH:MM 形式で入力してください。（例: 09:30 / 3:2 / ３：２）"

    hour = int(matched.group(1))
    minute = int(matched.group(2))
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None, "時間は 00:00〜23:59 の範囲で入力してください。"

    return f"{hour:02d}:{minute:02d}", None


def _build_due_date_options(selected_due_date: Optional[str]) -> list[discord.SelectOption]:
    options = [
        discord.SelectOption(
            label="設定しない",
            value=NONE_VALUE,
            description="締切日を設定しません",
            default=selected_due_date is None,
        )
    ]

    today = now_local().date()
    candidate_dates: list[str] = []

    for offset in range(0, 8):
        date_value = today + timedelta(days=offset)
        value = date_value.isoformat()
        candidate_dates.append(value)
        relative_label = "今日" if offset == 0 else f"{offset}日後"
        options.append(
            discord.SelectOption(
                label=f"{relative_label} ({date_value.month}/{date_value.day})",
                value=value,
                description=f"{value} ({WEEKDAYS_JA[date_value.weekday()]})",
                default=selected_due_date == value,
            )
        )

    if selected_due_date and selected_due_date not in candidate_dates:
        options.insert(
            1,
            discord.SelectOption(
                label=f"{selected_due_date} (既存)",
                value=selected_due_date,
                description="現在の締切日",
                default=True,
            ),
        )

    return options


def _build_priority_options(selected_priority: str) -> list[discord.SelectOption]:
    options: list[discord.SelectOption] = []
    for value, label in PRIORITY_OPTIONS:
        options.append(
            discord.SelectOption(
                label=f"{label} ({value})",
                value=value,
                default=selected_priority == value,
            )
        )
    return options


def _selected_or_default(select: discord.ui.Select, fallback: str) -> str:
    if select.values:
        return str(select.values[0])
    for option in select.options:
        if option.default:
            return option.value
    return fallback


class OptionalInputText(discord.ui.InputText):
    """Workaround for py-cord 2.7.x: keep required=False in regenerated payload."""

    def _generate_underlying(
        self,
        style: discord.InputTextStyle | None = None,
        custom_id: str | None = None,
        label: str | None = None,
        placeholder: str | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        required: bool | None = None,
        value: str | None = None,
        id: int | None = None,
    ) -> InputTextComponent:
        ModalItem._generate_underlying(self, InputTextComponent)
        return InputTextComponent._raw_construct(
            type=ComponentType.input_text,
            style=style if style is not None else self.style,
            custom_id=custom_id if custom_id is not None else self.custom_id,
            label=label if label is not None else self.label,
            placeholder=placeholder if placeholder is not None else self.placeholder,
            min_length=min_length if min_length is not None else self.min_length,
            max_length=max_length if max_length is not None else self.max_length,
            required=required if required is not None else self.required,
            value=value if value is not None else self.value,
            id=id if id is not None else self.id,
        )


class TaskFormModal(discord.ui.DesignerModal):
    def __init__(
        self,
        *,
        owner_id: int,
        mode: str,
        modal_title: str,
        title_value: str = "",
        description_value: Optional[str] = None,
        priority: str = DEFAULT_PRIORITY,
        due_at: Optional[str] = None,
        task_id: Optional[int] = None,
        return_mode: str = "home",
        list_type: str | None = None,
        page: int = 1,
    ):
        self.owner_id = owner_id
        self.mode = mode
        self.task_id = task_id
        self.return_mode = return_mode
        self.list_type = list_type
        self.page = page

        selected_priority = _normalize_priority(priority)
        selected_due_date = _extract_due_date(due_at)
        initial_due_time = _extract_due_time(due_at)

        title_label = discord.ui.Label("タイトル")
        title_label.set_input_text(
            placeholder="タスクのタイトル",
            value=title_value,
            required=True,
            max_length=100,
        )

        description_label = discord.ui.Label("説明（任意）")
        description_label.set_item(
            OptionalInputText(
                placeholder="任意（空欄でOK）",
                value=description_value or "",
                style=discord.InputTextStyle.long,
                required=False,
                max_length=1000,
            )
        )

        due_date_label = discord.ui.Label("日付（任意）")
        due_date_label.set_select(
            placeholder="締切日を選択（任意）",
            min_values=1,
            max_values=1,
            options=_build_due_date_options(selected_due_date),
            required=True,
            default_values=None,
        )

        due_time_label = discord.ui.Label("時刻（任意）")
        due_time_label.set_item(
            OptionalInputText(
                placeholder="HH:MM（例: 09:30 / 3:2 / ３：２）",
                value=initial_due_time or "",
                required=False,
                max_length=5,
            )
        )

        priority_label = discord.ui.Label("優先度")
        priority_label.set_select(
            placeholder="優先度を選択",
            min_values=1,
            max_values=1,
            options=_build_priority_options(selected_priority),
            required=True,
            default_values=None,
        )

        super().__init__(
            title_label,
            description_label,
            due_date_label,
            due_time_label,
            priority_label,
            title=modal_title,
        )

        self.title_input = cast(discord.ui.InputText, title_label.item)
        self.description_input = cast(discord.ui.InputText, description_label.item)
        self.due_date_select = cast(discord.ui.Select, due_date_label.item)
        self.due_time_input = cast(discord.ui.InputText, due_time_label.item)
        self.priority_select = cast(discord.ui.Select, priority_label.item)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "これはあなた用の操作画面ではありません。", ephemeral=True
            )
            return

        title = (self.title_input.value or "").strip()
        if not title:
            await interaction.response.send_message(
                "タイトルを入力してください。", ephemeral=True
            )
            return

        description = (self.description_input.value or "").strip() or None

        due_date_value = _selected_or_default(self.due_date_select, NONE_VALUE)
        due_date = None if due_date_value == NONE_VALUE else due_date_value

        due_time, due_time_error = _validate_due_time_text(self.due_time_input.value)
        if due_time_error:
            await interaction.response.send_message(due_time_error, ephemeral=True)
            return

        if due_date is None and due_time is not None:
            await interaction.response.send_message(
                "時刻を入力する場合は日付も選択してください。", ephemeral=True
            )
            return

        priority = _normalize_priority(
            _selected_or_default(self.priority_select, DEFAULT_PRIORITY)
        )

        due_at = None
        if due_date is not None:
            due_at = f"{due_date} {due_time or '23:59'}"

        if self.mode == "edit":
            if self.task_id is None:
                await interaction.response.send_message(
                    "更新対象のタスクが見つかりません。", ephemeral=True
                )
                return
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
            task_id = self.task_id
        else:
            task_id = task_service.create_task(
                user_id=str(self.owner_id),
                title=title,
                description=description,
                due_at=due_at,
                priority=priority,
            )

        task = task_service.get_task_by_id(str(self.owner_id), task_id)
        if not task:
            await interaction.response.send_message(
                "タスクの作成/更新に失敗しました。", ephemeral=True
            )
            return

        view = TaskDetailView(
            owner_id=self.owner_id,
            task_id=task_id,
            return_mode=self.return_mode,
            list_type=self.list_type,
            page=self.page,
        )
        await interaction.response.edit_message(embed=build_task_detail_embed(task), view=view)


class TaskCreateModal(TaskFormModal):
    def __init__(self, owner_id: int):
        super().__init__(
            owner_id=owner_id,
            mode="create",
            modal_title="タスク追加",
            return_mode="home",
        )


class TaskEditModal(TaskFormModal):
    def __init__(
        self,
        owner_id: int,
        task: dict,
        return_mode: str = "home",
        list_type: str | None = None,
        page: int = 1,
    ):
        super().__init__(
            owner_id=owner_id,
            mode="edit",
            modal_title="タスク編集",
            title_value=task.get("title") or "",
            description_value=task.get("description"),
            priority=task.get("priority") or DEFAULT_PRIORITY,
            due_at=task.get("due_at"),
            task_id=int(task["id"]),
            return_mode=return_mode,
            list_type=list_type,
            page=page,
        )
