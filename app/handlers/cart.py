"""
Cart handler for Apivita honey store bot.
Handles cart display, item removal, clearing, and the checkout FSM.
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.repositories import CartRepository, OrderRepository, UserRepository
from app.database.connection import get_session

logger = logging.getLogger(__name__)

router = Router(name="cart")

# ---------------------------------------------------------------------------
# FSM states
# ---------------------------------------------------------------------------

class CheckoutState(StatesGroup):
    city    = State()
    address = State()
    comment = State()
    confirm = State()


# ---------------------------------------------------------------------------
# Keyboard builders
# ---------------------------------------------------------------------------

def cart_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Оформить заказ",  callback_data="checkout")
    builder.button(text="🗑 Очистить корзину", callback_data="clear_cart")
    builder.button(text="🏠 Главное меню",    callback_data="back:main_menu")
    builder.adjust(1)
    return builder.as_markup()


def empty_cart_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Перейти в каталог", callback_data="open_catalog")
    builder.adjust(1)
    return builder.as_markup()


def checkout_skip_keyboard():
    """Skip button for the comment step."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⏭ Пропустить", callback_data="skip_comment")
    builder.button(text="❌ Отмена",     callback_data="cancel_checkout")
    builder.adjust(2)
    return builder.as_markup()


def checkout_cancel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel_checkout")
    builder.adjust(1)
    return builder.as_markup()


def confirm_order_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить заказ", callback_data="confirm_order")
    builder.button(text="❌ Отмена",            callback_data="cancel_checkout")
    builder.adjust(1)
    return builder.as_markup()


def remove_item_keyboard(items: list):
    """Cart items with individual remove buttons."""
    builder = InlineKeyboardBuilder()
    for item in items:
        builder.button(
            text=f"❌ Убрать: {item['name']} {item.get('weight', '')}",
            callback_data=f"remove_item:{item['product_id']}",
        )
    builder.button(text="✅ Оформить заказ",  callback_data="checkout")
    builder.button(text="🗑 Очистить корзину", callback_data="clear_cart")
    builder.button(text="🏠 Главное меню",    callback_data="back:main_menu")
    builder.adjust(1)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_cart(items: list) -> tuple[str, int]:
    """Return (text, total) for a non-empty cart."""
    lines = ["🛒 <b>Ваша корзина:</b>\n"]
    total = 0
    for item in items:
        subtotal = item["price"] * item["quantity"]
        total += subtotal
        lines.append(
            f"• <b>{item['name']}</b> {item.get('weight', '')}\n"
            f"  {item['quantity']} шт. × {item['price']:,} ₸ = <b>{subtotal:,} ₸</b>"
        )
    lines.append(f"\n💰 <b>Итого: {total:,} ₸</b>")
    return "\n".join(lines), total


def _format_order_summary(city: str, address: str, comment: str | None, items: list, total: int) -> str:
    item_lines = "\n".join(
        f"  • {i['name']} {i.get('weight', '')} × {i['quantity']} = {i['price'] * i['quantity']:,} ₸"
        for i in items
    )
    comment_line = f"\n💬 Комментарий: {comment}" if comment else ""
    return (
        f"📋 <b>Подтверждение заказа</b>\n\n"
        f"📍 Город: {city}\n"
        f"🏠 Адрес: {address}"
        f"{comment_line}\n\n"
        f"<b>Состав заказа:</b>\n{item_lines}\n\n"
        f"💰 <b>Итого: {total:,} ₸</b>\n\n"
        f"Подтвердить заказ?"
    )


# ---------------------------------------------------------------------------
# Show cart
# ---------------------------------------------------------------------------

@router.message(F.text == "🛒 Корзина")
async def show_cart(message: Message) -> None:
    user_id = message.from_user.id
    logger.info("User %s viewing cart", user_id)
    try:
        async with get_session() as session:
            cart_repo = CartRepository(session)
            items = await cart_repo.get_items(user_id=user_id)
    except Exception:
        logger.exception("Failed to fetch cart for user %s", user_id)
        await message.answer("❌ Не удалось загрузить корзину. Попробуйте позже.")
        return

    if not items:
        await message.answer(
            "🛒 Ваша корзина пуста.\n\nПерейдите в каталог, чтобы выбрать товары.",
            reply_markup=empty_cart_keyboard(),
        )
        return

    text, total = _format_cart(items)
    await message.answer(text, reply_markup=remove_item_keyboard(items), parse_mode="HTML")


# ---------------------------------------------------------------------------
# Remove single item
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("remove_item:"))
async def remove_item(callback: CallbackQuery) -> None:
    product_id = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    try:
        async with get_session() as session:
            cart_repo = CartRepository(session)
            await cart_repo.remove_item(user_id=user_id, product_id=product_id)
            items = await cart_repo.get_items(user_id=user_id)
    except Exception:
        logger.exception("Failed to remove item '%s' for user %s", product_id, user_id)
        await callback.answer("❌ Ошибка при удалении товара.", show_alert=True)
        return

    if not items:
        await callback.message.edit_text(
            "🛒 Ваша корзина пуста.\n\nПерейдите в каталог, чтобы выбрать товары.",
            reply_markup=empty_cart_keyboard(),
        )
    else:
        text, _ = _format_cart(items)
        await callback.message.edit_text(
            text,
            reply_markup=remove_item_keyboard(items),
            parse_mode="HTML",
        )
    await callback.answer("Товар удалён из корзины.")


# ---------------------------------------------------------------------------
# Clear cart
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "clear_cart")
async def clear_cart(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    try:
        async with get_session() as session:
            cart_repo = CartRepository(session)
            await cart_repo.clear(user_id=user_id)
    except Exception:
        logger.exception("Failed to clear cart for user %s", user_id)
        await callback.answer("❌ Ошибка при очистке корзины.", show_alert=True)
        return

    await callback.message.edit_text(
        "🛒 Корзина очищена.\n\nПерейдите в каталог, чтобы выбрать товары.",
        reply_markup=empty_cart_keyboard(),
    )
    await callback.answer("Корзина очищена.")


# ---------------------------------------------------------------------------
# Checkout FSM — Step 1: city
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "checkout")
async def checkout_start(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = callback.from_user.id
    # Verify cart is not empty before entering FSM
    try:
        async with get_session() as session:
            cart_repo = CartRepository(session)
            items = await cart_repo.get_items(user_id=user_id)
    except Exception:
        logger.exception("Failed to fetch cart for user %s during checkout", user_id)
        await callback.answer("❌ Ошибка. Попробуйте позже.", show_alert=True)
        return

    if not items:
        await callback.answer("Корзина пуста.", show_alert=True)
        return

    await state.set_state(CheckoutState.city)
    await callback.message.answer(
        "📍 <b>Оформление заказа</b>\n\n"
        "Шаг 1/3 — Введите ваш <b>город</b>:",
        reply_markup=checkout_cancel_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Checkout FSM — Step 2: address
# ---------------------------------------------------------------------------

@router.message(CheckoutState.city)
async def checkout_city(message: Message, state: FSMContext) -> None:
    city = message.text.strip()
    if not city:
        await message.answer("Пожалуйста, введите название города.")
        return

    await state.update_data(city=city)
    await state.set_state(CheckoutState.address)
    await message.answer(
        "🏠 Шаг 2/3 — Введите ваш <b>адрес доставки</b>\n"
        "(улица, дом, квартира):",
        reply_markup=checkout_cancel_keyboard(),
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# Checkout FSM — Step 3: comment
# ---------------------------------------------------------------------------

@router.message(CheckoutState.address)
async def checkout_address(message: Message, state: FSMContext) -> None:
    address = message.text.strip()
    if not address:
        await message.answer("Пожалуйста, введите адрес доставки.")
        return

    await state.update_data(address=address)
    await state.set_state(CheckoutState.comment)
    await message.answer(
        "💬 Шаг 3/3 — Добавьте <b>комментарий</b> к заказу\n"
        "или нажмите «Пропустить»:",
        reply_markup=checkout_skip_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "skip_comment", CheckoutState.comment)
async def skip_comment(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(comment=None)
    await _show_order_summary(callback.message, state, callback.from_user.id)
    await callback.answer()


@router.message(CheckoutState.comment)
async def checkout_comment(message: Message, state: FSMContext) -> None:
    comment = message.text.strip() or None
    await state.update_data(comment=comment)
    await _show_order_summary(message, state, message.from_user.id)


# ---------------------------------------------------------------------------
# Checkout FSM — Step 4: confirmation
# ---------------------------------------------------------------------------

async def _show_order_summary(message: Message, state: FSMContext, user_id: int) -> None:
    data = await state.get_data()
    try:
        async with get_session() as session:
            cart_repo = CartRepository(session)
            items = await cart_repo.get_items(user_id=user_id)
    except Exception:
        logger.exception("Failed to fetch cart for summary (user %s)", user_id)
        await message.answer("❌ Ошибка. Попробуйте позже.")
        await state.clear()
        return

    _, total = _format_cart(items)
    text = _format_order_summary(
        city=data["city"],
        address=data["address"],
        comment=data.get("comment"),
        items=items,
        total=total,
    )
    await state.set_state(CheckoutState.confirm)
    await message.answer(text, reply_markup=confirm_order_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "confirm_order", CheckoutState.confirm)
async def confirm_order(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = callback.from_user.id
    data = await state.get_data()

    try:
        async with get_session() as session:
            cart_repo  = CartRepository(session)
            order_repo = OrderRepository(session)
            user_repo  = UserRepository(session)

            items = await cart_repo.get_items(user_id=user_id)
            if not items:
                await callback.answer("Корзина пуста.", show_alert=True)
                await state.clear()
                return

            _, total = _format_cart(items)
            order_id = await order_repo.create_order(
                user_id=user_id,
                city=data["city"],
                address=data["address"],
                comment=data.get("comment"),
                items=items,
                total=total,
            )
            user_obj = await user_repo.get_by_telegram_id(user_id)
            order_obj = await order_repo.get_by_id(order_id)
            await cart_repo.clear(user_id=user_id)
    except Exception:
        logger.exception("Failed to create order for user %s", user_id)
        await callback.answer("❌ Ошибка при создании заказа. Попробуйте позже.", show_alert=True)
        return

    # Trigger admin notification
    try:
        from app.services.notifications import notify_admin_new_order
        if order_obj and user_obj:
            await notify_admin_new_order(callback.bot, order_obj, user_obj, items)
    except Exception:
        logger.exception("Failed to send admin notification for order #%s", order_id)

    await state.clear()
    logger.info("Order #%s created for user %s", order_id, user_id)

    await callback.message.edit_text(
        f"🎉 <b>Заказ успешно оформлен!</b>\n\n"
        f"Ваш номер заказа: <code>{order_id}</code>\n\n"
        f"Наш менеджер свяжется с вами в ближайшее время для подтверждения.\n"
        f"Спасибо, что выбрали Apivita! 🍯",
        parse_mode="HTML",
    )
    await callback.answer("Заказ оформлен!")


@router.callback_query(F.data == "cancel_checkout")
async def cancel_checkout(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer(
        "❌ Оформление заказа отменено.\n\nВаша корзина сохранена.",
    )
    await callback.answer("Отменено.")


# ---------------------------------------------------------------------------
# Misc navigations triggered from cart view
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "open_catalog")
async def open_catalog_from_cart(callback: CallbackQuery) -> None:
    await callback.message.delete()
    await callback.message.answer("Перейдите в каталог с помощью кнопки <b>🛒 Каталог</b> в меню.", parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "back:main_menu")
async def back_to_main_menu(callback: CallbackQuery) -> None:
    await callback.message.delete()
    await callback.message.answer("🏠 Вы в главном меню.\n\nВыберите раздел с помощью кнопок ниже.")
    await callback.answer()
