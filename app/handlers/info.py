"""
Info / static pages handler for Apivita honey store bot.
Handles "About us" and "Delivery" sections.
"""
import logging
from pathlib import Path

from aiogram import Router, F
from aiogram.types import Message, FSInputFile

logger = logging.getLogger(__name__)

router = Router(name="info")

# ---------------------------------------------------------------------------
# Static content
# ---------------------------------------------------------------------------

ABOUT_TEXT = (
    "🍯 <b>Apivita — натуральный мёд из Казахстана</b>\n\n"
    "Мы предлагаем широкий ассортимент натурального мёда и продуктов "
    "пчеловодства прямо от пасеки.\n\n"
    "<b>Почему Apivita?</b>\n"
    "• Только натуральный мёд без добавок\n"
    "• Постоянный контроль качества\n"
    "• Широкий ассортимент сортов и фасовок\n"
    "• Удобная доставка по всему Казахстану\n"
    "• Пластиковая и стеклянная тара на выбор\n\n"
    "Свяжитесь с нами: @apivita_support"
)

DELIVERY_TEXT = (
    "🚚 <b>Доставка Apivita</b>\n\n"
    "<b>География:</b>\n"
    "Доставляем по всему Казахстану 🇰🇿\n\n"
    "<b>Способы доставки:</b>\n"
    "• 🚗 Курьер (в вашем городе)\n"
    "• 📮 Казпочта\n"
    "• 🚛 Транспортные компании (СДЭК, DHL, и др.)\n\n"
    "<b>Стоимость доставки:</b>\n"
    "• При заказе от <b>5 кг</b> — доставка <b>бесплатно</b> 🎁\n"
    "• При заказе до 5 кг — стоимость рассчитывается индивидуально\n\n"
    "<b>Сроки:</b>\n"
    "• По городу: 1–2 рабочих дня\n"
    "• По Казахстану: 3–7 рабочих дней\n\n"
    "По вопросам доставки пишите: @apivita_support"
)

# Optional logo image path (relative to project root)
LOGO_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "logo.jpg"


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

@router.message(F.text == "ℹ️ О нас")
async def show_about(message: Message) -> None:
    logger.info("User %s opened 'About' page", message.from_user.id)
    try:
        if LOGO_PATH.exists():
            photo = FSInputFile(str(LOGO_PATH))
            await message.answer_photo(
                photo=photo,
                caption=ABOUT_TEXT,
                parse_mode="HTML",
            )
        else:
            await message.answer(ABOUT_TEXT, parse_mode="HTML")
    except Exception:
        logger.exception("Failed to send 'About' page to user %s", message.from_user.id)
        # Fallback: send text-only
        try:
            await message.answer(ABOUT_TEXT, parse_mode="HTML")
        except Exception:
            logger.exception("Fallback text send also failed for user %s", message.from_user.id)


@router.message(F.text == "🚚 Доставка")
async def show_delivery(message: Message) -> None:
    logger.info("User %s opened 'Delivery' page", message.from_user.id)
    try:
        await message.answer(DELIVERY_TEXT, parse_mode="HTML")
    except Exception:
        logger.exception("Failed to send 'Delivery' page to user %s", message.from_user.id)
