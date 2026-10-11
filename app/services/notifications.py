"""
Notification service — sends Telegram messages about order status changes.
"""
from aiogram import Bot
from loguru import logger

from app.config import settings
from app.utils.formatters import format_price, format_admin_order_notification
from app.keyboards.inline import admin_order_keyboard


# Status notification messages sent to customers
STATUS_MESSAGES = {
    "confirmed": (
        "✅ <b>Ваш заказ №<code>{order_id}</code> подтверждён!</b>\n\n"
        "Наш менеджер свяжется с вами для уточнения деталей оплаты.\n\n"
        "💳 Оплата производится переводом на карту по реквизитам."
    ),
    "paid": (
        "💰 <b>Оплата по заказу №<code>{order_id}</code> получена!</b>\n\n"
        "🚀 Начинаем готовить ваш заказ к отправке."
    ),
    "shipped": (
        "🚚 <b>Ваш заказ №<code>{order_id}</code> отправлен!</b>\n\n"
        "Следите за трек-номером — скоро получите посылку.\n"
        "По вопросам доставки: @apivita_support"
    ),
    "delivered": (
        "🎉 <b>Заказ №<code>{order_id}</code> доставлен!</b>\n\n"
        "Спасибо, что выбрали <b>АпивитА</b>! 🍯\n"
        "Будем рады вашему следующему заказу!"
    ),
    "cancelled": (
        "❌ <b>Заказ №<code>{order_id}</code> отменён.</b>\n\n"
        "Если у вас есть вопросы, напишите нам: @apivita_support"
    ),
}


async def notify_admin_new_order(
    bot: Bot, order, user, items: list
) -> None:
    """Send formatted new order notification to all admins."""
    text = format_admin_order_notification(order, user, items)
    kb = admin_order_keyboard(order.id)

    for admin_id in settings.admin_ids_list:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=text,
                reply_markup=kb,
            )
        except Exception as e:
            logger.warning(f"Failed to notify admin {admin_id} about order {order.id}: {e}")


async def notify_user_order_status(
    bot: Bot, user_telegram_id: int, order_id: int, new_status: str
) -> None:
    """Send order status update to the customer."""
    template = STATUS_MESSAGES.get(new_status)
    if not template:
        logger.warning(f"No status message template for status '{new_status}'")
        return

    text = template.format(order_id=order_id)
    try:
        await bot.send_message(
            chat_id=user_telegram_id,
            text=text,
        )
    except Exception as e:
        logger.warning(
            f"Failed to notify user {user_telegram_id} about order {order_id} status '{new_status}': {e}"
        )


async def broadcast_message(
    bot: Bot,
    users: list,
    text: str = None,
    photo_file_id: str = None,
    video_file_id: str = None,
) -> tuple[int, int]:
    """
    Send a broadcast message to all provided users.
    
    Returns (sent_count, failed_count).
    """
    sent = 0
    failed = 0

    for user in users:
        try:
            if photo_file_id:
                await bot.send_photo(
                    chat_id=user.telegram_id,
                    photo=photo_file_id,
                    caption=text,
                )
            elif video_file_id:
                await bot.send_video(
                    chat_id=user.telegram_id,
                    video=video_file_id,
                    caption=text,
                )
            else:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=text,
                )
            sent += 1
        except Exception as e:
            logger.warning(f"Failed to send broadcast to user {user.telegram_id}: {e}")
            failed += 1

    logger.info(f"Broadcast complete: {sent} sent, {failed} failed")
    return sent, failed

