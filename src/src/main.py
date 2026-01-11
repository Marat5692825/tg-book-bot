import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from .config import load_config
from .handlers_public import router as public_router
from .handlers_admin import router as admin_router

async def main():
    cfg = load_config()
    bot = Bot(token=cfg.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    # передаём admin_ids в хендлеры как зависимость
    dp["admin_ids"] = cfg.admin_ids

    dp.include_router(public_router)
    dp.include_router(admin_router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
