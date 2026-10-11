"""
Orders handler for Apivita honey store bot.
Handles displaying order history and order details.
"""
import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.repositories import OrderRepository
from app.database.connection import get_session

logger = logging.getLogger(__name__)

router = Router(name="orders")

# ---------------------------------------------------------------------------
# Status display helpers
# ---------------------------------------------------------------------------

STATUS_EMOJI = {
    "new":       "🔵",
    "confirmed": "🟡",
    "paid":      "🟢",
    "shipped":   "🚚",
    "delivered": "✅",
    "cancelled": "❌",
}

STATUS_LABEL = {
    "new":       "Новый",
    "confirmed": "Подтверждён",
    "paid":      "Оплачен",
    "shipped":   "В пути",
    "delivered": "Доставлен",
    "cancelled": "Отменён",
}


def _status_display(status: str) -> str:
    emoji = STATUS_EMOJI.get(status, "❔")
    label = STATUS_LABEL.get(status, status)
    return f"{emoji} {label}"


def _format_date(dt: datetime | str | None) -> str:
    if dt is None:
        return "—"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return dt
    return dt.strftime("%d.%m.%Y %H:%M")


# ---------------------------------------------------------------------------
# Keyboards
# ---------------------------------------------------------------------------

def orders_list_keyboard(orders: list):
    """One button per order + back."""
    builder = InlineKeyboardBuilder()
    for order in orders:
        status_icon = STATUS_EMOJI.get(order.get("status", "new"), "❔")
        label = (
            f"{status_icon} №{order['id']} "
            f"от {_format_date(order.get('created_at'))} "
            f"— {order.get('total', 0):,} ₸"
        )
        builder.button(text=label, callback_data=f"order:{order['id']}")
    builder.button(text="🏠 Главное меню", callback_data="back:main_menu_orders")
    builder.adjust(1)
    return builder.as_markup()


def order_detail_keyboard(order_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад к заказам", callback_data="back:orders")
    builder.adjust(1)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_orders_list(orders: list) -> str:
    lines = ["📦 <b>Мои заказы</b>\n"]
    for order in orders:
        lines.append(
            f"{_status_display(order.get('status', 'new'))} "
            f"<b>Заказ №{order['id']}</b> "
            f"от {_format_date(order.get('created_at'))}\n"
            f"   Сумма: <b>{order.get('total', 0):,} ₸</b>"
        )
    return "\n\n".join(lines)


def _format_order_detail(order: dict) -> str:
    items = order.get("items", [])
    item_lines = "\n".join(
        f"  • {i.get('name', '?')} {i.get('weight', '')} "
        f"× {i.get('quantity', 1)} = {i.get('price', 0) * i.get('quantity', 1):,} ₸"
        for i in items
    ) or "  (нет данных)"

    comment_line = f"\n💬 Комментарий: {order['comment']}" if order.get("comment") else ""
    city_line    = f"\n📍 Город: {order['city']}"    if order.get("city")    else ""
    address_line = f"\n🏠 Адрес: {order['address']}" if order.get("address") else ""

    return (
        f"📦 <b>Заказ №{order['id']}</b>\n"
        f"📅 Дата: {_format_date(order.get('created_at'))}\n"
        f"Статус: {_status_display(order.get('status', 'new'))}"
        f"{city_line}"
        f"{address_line}"
        f"{comment_line}\n\n"
        f"<b>Состав:</b>\n{item_lines}\n\n"
        f"💰 <b>Итого: {order.get('total', 0):,} ₸</b>"
    )


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

@router.message(F.text == "📦 Мои заказы")
async def show_orders(message: Message) -> None:
    user_id = message.from_user.id
    logger.info("User %s viewing order history", user_id)
    try:
        async with get_session() as session:
            order_repo = OrderRepository(session)
            orders = await order_repo.get_user_orders(user_id=user_id)
    except Exception:
        logger.exception("Failed to fetch orders for user %s", user_id)
        await message.answer("❌ Не удалось загрузить заказы. Попробуйте позже.")
        return

    if not orders:
        await message.answer(
            "📦 У вас пока нет заказов.\n\n"
            "Перейдите в каталог, чтобы сделать первый заказ! 🍯"
        )
        return

    text = _format_orders_list(orders)
    await message.answer(
        text,
        reply_markup=orders_list_keyboard(orders),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("order:"))
async def show_order_detail(callback: CallbackQuery) -> None:
    raw_id = callback.data.split(":", 1)[1]
    try:
        order_id = int(raw_id)
    except ValueError:
        await callback.answer("Неверный идентификатор заказа.", show_alert=True)
        return

    user_id = callback.from_user.id
    logger.info("User %s viewing order detail #%s", user_id, order_id)

    try:
        async with get_session() as session:
            order_repo = OrderRepository(session)
            order = await order_repo.get_order_detail(order_id=order_id, user_id=user_id)
    except Exception:
        logger.exception("Failed to fetch order #%s for user %s", order_id, user_id)
        await callback.answer("❌ Ошибка при загрузке заказа.", show_alert=True)
        return

    if not order:
        await callback.answer("Заказ не найден.", show_alert=True)
        return

    await callback.message.edit_text(
        _format_order_detail(order),
        reply_markup=order_detail_keyboard(order_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "back:orders")
async def back_to_orders(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    try:
        async with get_session() as session:
            order_repo = OrderRepository(session)
            orders = await order_repo.get_user_orders(user_id=user_id)
    except Exception:
        logger.exception("Failed to fetch orders on back navigation for user %s", user_id)
        await callback.answer("❌ Ошибка при загрузке заказов.", show_alert=True)
        return

    if not orders:
        await callback.message.edit_text("📦 У вас пока нет заказов.")
        await callback.answer()
        return

    text = _format_orders_list(orders)
    await callback.message.edit_text(
        text,
        reply_markup=orders_list_keyboard(orders),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "back:main_menu_orders")
async def back_to_main_menu(callback: CallbackQuery) -> None:
    await callback.message.delete()
    await callback.message.answer("🏠 Вы в главном меню.\n\nВыберите раздел с помощью кнопок ниже.")
    await callback.answer()
