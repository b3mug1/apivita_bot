"""
Apivita Telegram Bot - Main entry point
Мёд и продукты пчеловодства из Казахстана
"""
import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger

from app.config import settings
from app.database.connection import init_db, close_db
from app.handlers import start, catalog, cart, orders, info, admin
from app.middlewares.auth import AuthMiddleware, LoggingMiddleware, ThrottlingMiddleware


async def set_bot_commands(bot: Bot) -> None:
    """Set bot commands menu."""
    from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
    
    # Commands for all users
    user_commands = [
        BotCommand(command="start", description="🔄 Перезапустить бота"),
        BotCommand(command="catalog", description="🛍 Каталог товаров"),
        BotCommand(command="cart", description="🛒 Моя корзина"),
        BotCommand(command="orders", description="📦 Мои заказы"),
        BotCommand(command="about", description="ℹ️ О нас"),
    ]
    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())
    
    # Extra commands for admins
    admin_commands = user_commands + [
        BotCommand(command="admin", description="⚙️ Панель администратора"),
    ]
    for admin_id in settings.admin_ids_list:
        try:
            await bot.set_my_commands(
                admin_commands, 
                scope=BotCommandScopeChat(chat_id=admin_id)
            )
        except Exception as e:
            logger.warning(f"Could not set admin commands for {admin_id}: {e}")


async def main() -> None:
    """Main bot startup function."""
    # Configure logging
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    logger.info("Starting Apivita Bot...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized successfully")
    
    # Initialize Bot
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Initialize Dispatcher with FSM storage
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Register middlewares (order matters)
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    dp.message.middleware(ThrottlingMiddleware(rate_limit=0.5))
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    
    # Include routers
    dp.include_router(start.router)
    dp.include_router(catalog.router)
    dp.include_router(cart.router)
    dp.include_router(orders.router)
    dp.include_router(info.router)
    dp.include_router(admin.router)
    
    # Set bot commands
    await set_bot_commands(bot)
    
    # Start healthcheck server for Render Web Service (if PORT is set)
    web_runner = None
    port = os.getenv("PORT")
    if port:
        from aiohttp import web
        app = web.Application()
        async def health_check(_request):
            return web.Response(text="Bot is running!")
        app.router.add_get("/", health_check)
        app.router.add_get("/health", health_check)
        web_runner = web.AppRunner(app)
        await web_runner.setup()
        site = web.TCPSite(web_runner, "0.0.0.0", int(port))
        await site.start()
        logger.info(f"Healthcheck HTTP server running on port {port}")

    # Start polling
    logger.info("Bot is running. Press Ctrl+C to stop.")
    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True,
        )
    finally:
        if web_runner:
            await web_runner.cleanup()
        await close_db()
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")

