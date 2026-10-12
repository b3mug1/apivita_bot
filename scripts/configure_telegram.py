import asyncio
import sys
from pathlib import Path

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat, MenuButtonWebApp, WebAppInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings


async def main() -> None:
    if not settings.WEBAPP_URL.startswith("https://"):
        raise ValueError("WEBAPP_URL must be a public HTTPS URL.")
    if not settings.WEBHOOK_SECRET:
        raise ValueError("Set WEBHOOK_SECRET before configuring the webhook.")

    bot = Bot(settings.BOT_TOKEN)
    try:
        commands = [
            BotCommand(command="start", description="Перезапустить бота"),
            BotCommand(command="catalog", description="Каталог товаров"),
            BotCommand(command="tags", description="Теги и категории товаров"),
            BotCommand(command="cart", description="Моя корзина"),
            BotCommand(command="orders", description="Мои заказы"),
            BotCommand(command="about", description="О нас"),
        ]
        await bot.set_my_commands(commands)
        for admin_id in settings.admin_ids_list:
            await bot.set_my_commands(
                commands + [BotCommand(command="admin", description="Панель администратора")],
                scope=BotCommandScopeChat(chat_id=admin_id),
            )
        await bot.set_webhook(
            f"{settings.WEBAPP_URL.rstrip('/')}/telegram/webhook",
            secret_token=settings.WEBHOOK_SECRET,
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True,
        )
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Магазин",
                web_app=WebAppInfo(url=settings.WEBAPP_URL),
            )
        )
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
