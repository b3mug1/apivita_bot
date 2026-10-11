"""
Reply keyboards for Apivita Telegram bot (Aiogram 3).
"""

from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)

from locales.ru.messages import MESSAGES


def main_menu_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    """
    Main menu reply keyboard.
    Buttons: Каталог, Корзина, Мои заказы, О нас, Доставка
    """
    # For future multi-language extension, dictionary can be extended
    m = MESSAGES

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=m.get("btn_catalog", "🛒 Каталог")),
                KeyboardButton(text=m.get("btn_cart", "🛒 Корзина")),
            ],
            [
                KeyboardButton(text=m.get("btn_orders", "📦 Мои заказы")),
            ],
            [
                KeyboardButton(text=m.get("btn_about", "ℹ️ О нас")),
                KeyboardButton(text=m.get("btn_delivery", "🚚 Доставка")),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder=m.get("main_menu_placeholder", "Выберите раздел..."),
    )
    return keyboard


def share_phone_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    """
    Keyboard with a single "Share phone" button that requests the user's contact.
    """
    m = MESSAGES

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text=m.get("btn_share", "📱 Поделиться"),
                    request_contact=True,
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder=m.get("share_phone_placeholder", "Нажмите кнопку ниже 👇🏿"),
    )
    return keyboard


def skip_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    """
    Keyboard with "Skip" and "Back" buttons — used during multi-step flows
    where the current step is optional.
    """
    m = MESSAGES

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=m.get("btn_skip", "➡️ Пропустить")),
                KeyboardButton(text=m.get("btn_back", "◀️ Назад")),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder=m.get("skip_placeholder", "Можно пропустить этот шаг"),
    )
    return keyboard


def back_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    """
    Keyboard with a single "Back" button.
    """
    m = MESSAGES

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=m.get("btn_back", "◀️ Назад")),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder=m.get("back_placeholder", "Нажмите «Назад» для возврата"),
    )
    return keyboard


def remove_keyboard() -> ReplyKeyboardRemove:
    """Helper to remove the reply keyboard entirely."""
    return ReplyKeyboardRemove()
