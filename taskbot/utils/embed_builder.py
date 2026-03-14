from __future__ import annotations

import discord


def _truncate(text: str, limit: int = 40) -> str:
    if text is None:
        return ""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)] + "..."


def _status_label(status: str | None) -> str:
    if status == "done":
        return "完了"
    if status == "todo":
        return "未完了"
    return status or "未完了"


def _due_label(due_at: str | None) -> str:
    if not due_at:
        return "なし"
    return due_at.strip()


def build_home_embed(summary: dict) -> discord.Embed:
    embed = discord.Embed(title="タスクホーム", color=0x2B90D9)
    embed.add_field(name="未完了", value=str(summary.get("todo_count", 0)), inline=True)
    embed.add_field(name="今日締切", value=str(summary.get("due_today", 0)), inline=True)
    embed.add_field(name="期限切れ", value=str(summary.get("overdue", 0)), inline=True)
    embed.set_footer(text="ボタンから操作してください")
    return embed


def build_task_list_embed(tasks: list[dict], list_title: str, page: int, page_count: int) -> discord.Embed:
    title = f"{list_title} ({page}/{page_count})"
    embed = discord.Embed(title=title, color=0x2B90D9)

    if not tasks:
        embed.description = "表示できるタスクがありません。"
        return embed

    lines: list[str] = []
    for task in tasks:
        due_text = _due_label(task.get("due_at"))
        line = (
            f"#{task['id']} | {_truncate(task['title'])} | {task['priority']} | "
            f"{due_text} | {_status_label(task.get('status'))}"
        )
        lines.append(line)

    embed.description = "\n".join(lines)
    embed.set_footer(text="セレクトメニューから詳細を開けます")
    return embed


def build_task_detail_embed(task: dict) -> discord.Embed:
    embed = discord.Embed(title=f"タスク詳細 #{task['id']}", color=0x2B90D9)
    embed.add_field(name="タイトル", value=task.get("title") or "", inline=False)
    embed.add_field(name="説明", value=task.get("description") or "(なし)", inline=False)
    embed.add_field(name="優先度", value=task.get("priority") or "medium", inline=True)
    embed.add_field(name="締切", value=_due_label(task.get("due_at")), inline=True)
    embed.add_field(name="状態", value=_status_label(task.get("status")), inline=True)
    embed.add_field(name="作成日時", value=task.get("created_at") or "", inline=False)
    embed.add_field(name="更新日時", value=task.get("updated_at") or "", inline=False)
    completed_at = task.get("completed_at")
    if completed_at:
        embed.add_field(name="完了日時", value=completed_at, inline=False)
    return embed


def build_reminder_embed(task: dict) -> discord.Embed:
    embed = discord.Embed(title="⏰ タスクリマインド", color=0xF5A623)
    embed.add_field(name="タイトル", value=task.get("title") or "", inline=False)
    embed.add_field(name="締切", value=_due_label(task.get("due_at")), inline=True)
    embed.add_field(name="優先度", value=task.get("priority") or "medium", inline=True)
    if task.get("description"):
        embed.add_field(name="説明", value=_truncate(task.get("description"), 200), inline=False)
    embed.set_footer(text=f"タスクID: #{task.get('id')}")
    return embed


def build_config_embed(settings: dict) -> discord.Embed:
    reminders_enabled = bool(int(settings.get("reminders_enabled", 1)))
    minutes = int(settings.get("reminder_minutes", 5))

    embed = discord.Embed(title="通知設定", color=0x2B90D9)
    if reminders_enabled and minutes > 0:
        embed.add_field(name="リマインド", value=f"{minutes}分前にDM", inline=False)
    else:
        embed.add_field(name="リマインド", value="オフ", inline=False)
    embed.add_field(name="通知先", value="DM", inline=True)
    embed.set_footer(text="セレクトメニューから変更できます")
    return embed
