"""
Admin panel handler for Apivita Telegram bot (Aiogram 3).
All handlers are guarded by admin_id check against settings.admin_ids_list.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import settings
from app.database.repositories import OrderRepository, UserRepository, AnalyticsRepository
from app.database.connection import get_session
from locales.ru.messages import MESSAGES

router = Router(name="admin")


# ---------------------------------------------------------------------------
# FSM States
# ---------------------------------------------------------------------------

class BroadcastState(StatesGroup):
    waiting_message = State()
    confirming = State()


# ---------------------------------------------------------------------------
# Helper: admin guard
# ---------------------------------------------------------------------------

def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids_list


# ---------------------------------------------------------------------------
# Keyboards
# ---------------------------------------------------------------------------

def admin_main_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(text="📦 Заказы", callback_data="admin_orders")
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="📣 Рассылка", callback_data="admin_broadcast")
    builder.button(text="👥 Пользователи", callback_data="admin_users")
    builder.adjust(2)
    return builder


def admin_order_keyboard(order_id: int) -> InlineKeyboardBuilder:
    """Inline keyboard with status update buttons for a specific order."""
    builder = InlineKeyboardBuilder()
    statuses = [
        ("✅ Подтвердить", "confirmed"),
        ("💰 Оплачен", "paid"),
        ("🚚 Отправлен", "shipped"),
        ("🎉 Доставлен", "delivered"),
        ("❌ Отменить", "cancelled"),
    ]
    for label, status in statuses:
        builder.button(text=label, callback_data=f"admin_status:{order_id}:{status}")
    builder.button(text="⬅️ Назад к заказам", callback_data="admin_orders")
    builder.adjust(2, 2, 1, 1)
    return builder


def broadcast_confirm_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Отправить всем", callback_data="broadcast_confirm")
    builder.button(text="❌ Отмена", callback_data="broadcast_cancel")
    builder.adjust(2)
    return builder


def back_to_admin_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Главное меню", callback_data="admin_main")
    return builder


# ---------------------------------------------------------------------------
# /admin command
# ---------------------------------------------------------------------------

@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer(MESSAGES["access_denied"])
        return

    await message.answer(
        "👨‍💼 <b>Панель администратора</b>\n\nВыберите раздел:",
        reply_markup=admin_main_keyboard().as_markup(),
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# Back to main menu callback
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "admin_main")
async def cb_admin_main(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer(MESSAGES["access_denied"], show_alert=True)
        return

    await call.message.edit_text(
        "👨‍💼 <b>Панель администратора</b>\n\nВыберите раздел:",
        reply_markup=admin_main_keyboard().as_markup(),
        parse_mode="HTML",
    )
    await call.answer()


# ---------------------------------------------------------------------------
# Orders list
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "admin_orders")
async def cb_admin_orders(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer(MESSAGES["access_denied"], show_alert=True)
        return

    async for session in get_session():
        repo = OrderRepository(session)
        orders = await repo.get_recent_orders(limit=20)

    if not orders:
        await call.message.edit_text(
            "📦 Заказов пока нет.",
            reply_markup=back_to_admin_keyboard().as_markup(),
        )
        await call.answer()
        return

    builder = InlineKeyboardBuilder()
    for order in orders:
        status_emoji = _status_emoji(order.status)
        label = f"{status_emoji} #{order.id} — {order.total_price} тг ({order.created_at.strftime('%d.%m %H:%M')})"
        builder.button(text=label, callback_data=f"admin_order:{order.id}")
    builder.button(text="⬅️ Главное меню", callback_data="admin_main")
    builder.adjust(1)

    await call.message.edit_text(
        f"📦 <b>Последние {len(orders)} заказов:</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )
    await call.answer()


def _status_emoji(status: str) -> str:
    mapping = {
        "new": "🆕",
        "confirmed": "✅",
        "paid": "💰",
        "shipped": "🚚",
        "delivered": "🎉",
        "cancelled": "❌",
    }
    return mapping.get(status, "❓")


# ---------------------------------------------------------------------------
# Order detail
# ---------------------------------------------------------------------------

def _format_admin_order_text(order) -> str:
    items_text = "\n".join(
        f"  • {getattr(item, 'product_name', getattr(item, 'name', 'Товар'))} × {item.quantity} = {item.subtotal} тг"
        for item in order.items
    )

    user_username = getattr(order, "user_username", None)
    user_name = getattr(order, "user_name", None)

    if user_username:
        if user_name and user_name not in ("-", "", "Клиент"):
            user_display = f"{user_name} (@{user_username})"
        else:
            user_display = f"@{user_username}"
    elif user_name and user_name not in ("-", "", "Клиент"):
        user_display = user_name
    elif getattr(order, "user_phone", None):
        user_display = order.user_phone
    else:
        user_display = "—"

    phone_line = f"\n📞 Телефон: {order.user_phone}" if getattr(order, "user_phone", None) else ""

    return (
        f"📦 <b>Заказ #{order.id}</b>\n"
        f"Статус: {_status_emoji(order.status)} <b>{order.status}</b>\n"
        f"Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"👤 Пользователь: {user_display}"
        f"{phone_line}\n"
        f"🏙 Город: {order.city}\n"
        f"🏠 Адрес: {order.address or '—'}\n\n"
        f"🛒 Состав заказа:\n{items_text}\n\n"
        f"💰 Итого: <b>{order.total_price} тг</b>"
    )


@router.callback_query(F.data.startswith("admin_order:"))
async def cb_admin_order_detail(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer(MESSAGES["access_denied"], show_alert=True)
        return

    order_id = int(call.data.split(":")[1])

    async for session in get_session():
        order_repo = OrderRepository(session)
        order = await order_repo.get_order_with_items(order_id)

    if not order:
        await call.answer("Заказ не найден.", show_alert=True)
        return

    text = _format_admin_order_text(order)

    await call.message.edit_text(
        text,
        reply_markup=admin_order_keyboard(order_id).as_markup(),
        parse_mode="HTML",
    )
    await call.answer()


# ---------------------------------------------------------------------------
# Status update
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("admin_status:"))
async def cb_admin_status_update(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer(MESSAGES["access_denied"], show_alert=True)
        return

    _, order_id_str, new_status = call.data.split(":")
    order_id = int(order_id_str)

    async for session in get_session():
        order_repo = OrderRepository(session)
        user_repo = UserRepository(session)

        order = await order_repo.get_order_with_items(order_id)
        if not order:
            await call.answer("Заказ не найден.", show_alert=True)
            return

        await order_repo.update_status(order_id, new_status)
        user = await user_repo.get_by_id(order.user_id)

    # Notify user about status change
    if user and user.telegram_id:
        from app.services.notifications import notify_user_order_status
        try:
            await notify_user_order_status(call.bot, user.telegram_id, order_id, new_status)
        except Exception:
            pass  # User may have blocked the bot

    await call.answer(f"✅ Статус заказа #{order_id} обновлён: {new_status}", show_alert=True)

    # Refresh order detail view
    async for session in get_session():
        order_repo = OrderRepository(session)
        updated_order = await order_repo.get_order_with_items(order_id)

    text = _format_admin_order_text(updated_order)

    await call.message.edit_text(
        text,
        reply_markup=admin_order_keyboard(order_id).as_markup(),
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer(MESSAGES["access_denied"], show_alert=True)
        return

    from app.services.analytics import get_stats

    async for session in get_session():
        stats = await get_stats(session)

    top_products_text = ""
    if stats.get("top_products"):
        top_products_text = "\n\n🏆 <b>Топ товаров:</b>\n" + "\n".join(
            f"  {i + 1}. {p['name']} — {p['count']} шт."
            for i, p in enumerate(stats["top_products"])
        )

    text = (
        f"📊 <b>Статистика магазина</b>\n\n"
        f"👥 Всего пользователей: <b>{stats['total_users']}</b>\n"
        f"📦 Всего заказов: <b>{stats['total_orders']}</b>\n"
        f"💰 Выручка сегодня: <b>{stats['revenue_today']} тг</b>\n"
        f"📅 Выручка за неделю: <b>{stats['revenue_week']} тг</b>"
        f"{top_products_text}"
    )

    await call.message.edit_text(
        text,
        reply_markup=back_to_admin_keyboard().as_markup(),
        parse_mode="HTML",
    )
    await call.answer()


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "admin_users")
async def cb_admin_users(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer(MESSAGES["access_denied"], show_alert=True)
        return

    async for session in get_session():
        user_repo = UserRepository(session)
        total = await user_repo.count_all()
        registered = await user_repo.count_registered()
        blocked = await user_repo.count_blocked()

    text = (
        f"👥 <b>Пользователи</b>\n\n"
        f"Всего: <b>{total}</b>\n"
        f"Зарегистрированы (с телефоном): <b>{registered}</b>\n"
        f"Заблокировали бота: <b>{blocked}</b>"
    )

    await call.message.edit_text(
        text,
        reply_markup=back_to_admin_keyboard().as_markup(),
        parse_mode="HTML",
    )
    await call.answer()


# ---------------------------------------------------------------------------
# Broadcast — entry point
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(call: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(call.from_user.id):
        await call.answer(MESSAGES["access_denied"], show_alert=True)
        return

    await state.set_state(BroadcastState.waiting_message)
    await call.message.edit_text(
        "📣 <b>Рассылка</b>\n\n"
        "Отправьте сообщение для рассылки (текст, фото или видео).\n"
        "Для отмены введите /cancel.",
        parse_mode="HTML",
    )
    await call.answer()


# ---------------------------------------------------------------------------
# Broadcast — receive message
# ---------------------------------------------------------------------------

@router.message(BroadcastState.waiting_message, F.from_user.func(lambda u: is_admin(u.id)))
async def broadcast_receive_message(message: Message, state: FSMContext) -> None:
    # Store the message details in FSM data
    data: dict = {}
    if message.text:
        data["content_type"] = "text"
        data["text"] = message.html_text
    elif message.photo:
        data["content_type"] = "photo"
        data["file_id"] = message.photo[-1].file_id
        data["caption"] = message.html_text or ""
    elif message.video:
        data["content_type"] = "video"
        data["file_id"] = message.video.file_id
        data["caption"] = message.html_text or ""
    else:
        await message.answer("⚠️ Поддерживаются только текст, фото и видео. Попробуйте снова.")
        return

    await state.update_data(**data)
    await state.set_state(BroadcastState.confirming)

    # Show preview
    preview_header = "👁 <b>Предпросмотр рассылки:</b>\n\n"
    if data["content_type"] == "text":
        await message.answer(
            preview_header + data["text"],
            parse_mode="HTML",
            reply_markup=broadcast_confirm_keyboard().as_markup(),
        )
    elif data["content_type"] == "photo":
        await message.answer_photo(
            data["file_id"],
            caption=(preview_header + data["caption"]) if data["caption"] else preview_header,
            parse_mode="HTML",
            reply_markup=broadcast_confirm_keyboard().as_markup(),
        )
    elif data["content_type"] == "video":
        await message.answer_video(
            data["file_id"],
            caption=(preview_header + data["caption"]) if data["caption"] else preview_header,
            parse_mode="HTML",
            reply_markup=broadcast_confirm_keyboard().as_markup(),
        )


# ---------------------------------------------------------------------------
# Broadcast — confirm
# ---------------------------------------------------------------------------

@router.callback_query(BroadcastState.confirming, F.data == "broadcast_confirm")
async def broadcast_confirm(call: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(call.from_user.id):
        await call.answer(MESSAGES["access_denied"], show_alert=True)
        return

    data = await state.get_data()
    await state.clear()

    async for session in get_session():
        user_repo = UserRepository(session)
        users = await user_repo.get_all_active()

    total = len(users)
    sent = 0
    failed = 0

    progress_message = await call.message.answer(f"📤 Рассылка началась...\nОтправлено: 0/{total}")

    for user in users:
        try:
            if data["content_type"] == "text":
                await call.bot.send_message(
                    user.telegram_id,
                    data["text"],
                    parse_mode="HTML",
                )
            elif data["content_type"] == "photo":
                await call.bot.send_photo(
                    user.telegram_id,
                    data["file_id"],
                    caption=data.get("caption", ""),
                    parse_mode="HTML",
                )
            elif data["content_type"] == "video":
                await call.bot.send_video(
                    user.telegram_id,
                    data["file_id"],
                    caption=data.get("caption", ""),
                    parse_mode="HTML",
                )
            sent += 1
        except Exception:
            # User blocked bot or other error — mark as blocked
            failed += 1
            async for session in get_session():
                user_repo = UserRepository(session)
                await user_repo.mark_blocked(user.telegram_id)

        # Update progress every 10 messages
        if (sent + failed) % 10 == 0:
            try:
                await progress_message.edit_text(
                    f"📤 Рассылка...\nОтправлено: {sent}/{total} | Ошибок: {failed}"
                )
            except Exception:
                pass

    await progress_message.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"Отправлено: {sent}/{total}\n"
        f"Ошибок (заблокировали бота): {failed}",
        parse_mode="HTML",
        reply_markup=back_to_admin_keyboard().as_markup(),
    )
    await call.answer()


# ---------------------------------------------------------------------------
# Broadcast — cancel
# ---------------------------------------------------------------------------

@router.callback_query(BroadcastState.confirming, F.data == "broadcast_cancel")
async def broadcast_cancel(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text(
        "❌ Рассылка отменена.",
        reply_markup=back_to_admin_keyboard().as_markup(),
    )
    await call.answer()


# ---------------------------------------------------------------------------
# /cancel command inside FSM
# ---------------------------------------------------------------------------

@router.message(Command("cancel"), BroadcastState.waiting_message)
@router.message(Command("cancel"), BroadcastState.confirming)
async def cmd_cancel_broadcast(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "❌ Действие отменено.",
        reply_markup=admin_main_keyboard().as_markup(),
    )
