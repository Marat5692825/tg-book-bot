import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: set[int]

def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is missing in .env")

    raw = os.getenv("ADMIN_IDS", "").strip()
    admins: set[int] = set()
    if raw:
        for x in raw.split(","):
            x = x.strip()
            if x.isdigit():
                admins.add(int(x))

    # Можно оставить пустым — тогда админ-функции будут недоступны
    return Config(bot_token=token, admin_ids=admins)
