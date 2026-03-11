from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = str(BASE_DIR / "database" / "taskbot.db")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
