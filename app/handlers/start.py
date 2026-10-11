"""
Start handler — registration and main menu.
Handles /start command and phone sharing (authorization).
"""
from aiogram import Router, F
from aiogram.types import Message, Contact
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from app.keyboards.reply import share_phone_keyboard, main_menu_keyboard
from app.database.connection import get_session
from app.database.repositories import UserRepository, AnalyticsRepository
from locales.ru.messages import MESSAGES

router = Router(name="start")


class Registration(StatesGroup):
    waiting_for_phone = State()


async def show_main_menu(message: Message, user_lang: str = "ru") -> None:
    """Show main menu to registered user."""
    await message.answer(
        MESSAGES["main_menu"],
        reply_markup=main_menu_keyboard(lang=user_lang),
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Handle /start command."""
    await state.clear()
    user = message.from_user

    async with get_session() as session:
        repo = UserRepository(session)
        db_user = await repo.get_by_telegram_id(user.id)

        if db_user and db_user.phone:
            # Already registered — go straight to main menu
            analytics_repo = AnalyticsRepository(session)
            await analytics_repo.log_action(db_user.id, "cmd_start_returning", {})
            await show_main_menu(message, user_lang=db_user.lang)
            return

        # New user or no phone yet
        if not db_user:
            db_user, _ = await repo.get_or_create(
                telegram_id=user.id,
                username=user.username or "",
                full_name=user.full_name or "",
            )
            analytics_repo = AnalyticsRepository(session)
            await analytics_repo.log_action(db_user.id, "cmd_start_new", {})

    await state.set_state(Registration.waiting_for_phone)
    await message.answer(
        MESSAGES["welcome"],
        reply_markup=share_phone_keyboard(),
    )
    await message.answer(MESSAGES["share_phone"])


@router.message(Registration.waiting_for_phone, F.contact)
async def handle_contact(message: Message, state: FSMContext) -> None:
    """Handle shared contact (phone number)."""
    contact: Contact = message.contact
    user = message.from_user

    # Validate that user shared their own number
    if contact.user_id and contact.user_id != user.id:
        await message.answer(
            "❌ Пожалуйста, поделитесь своим номером, а не чужим.",
            reply_markup=share_phone_keyboard(),
        )
        return

    phone = contact.phone_number
    # Normalize phone
    if not phone.startswith("+"):
        phone = "+" + phone

    async with get_session() as session:
        repo = UserRepository(session)
        db_user = await repo.get_by_telegram_id(user.id)
        if not db_user:
            db_user, _ = await repo.get_or_create(
                telegram_id=user.id,
                username=user.username or "",
                full_name=user.full_name or "",
            )
        await repo.update_phone(db_user.id, phone)
        analytics_repo = AnalyticsRepository(session)
        await analytics_repo.log_action(db_user.id, "registered", {"phone": phone})
        user_lang = db_user.lang

    await state.clear()
    await message.answer(
        MESSAGES["registered"],
        reply_markup=main_menu_keyboard(lang=user_lang),
    )


@router.message(Registration.waiting_for_phone, ~F.contact)
async def handle_wrong_input_during_registration(message: Message) -> None:
    """Remind user to use the share button."""
    await message.answer(
        MESSAGES["share_phone"],
        reply_markup=share_phone_keyboard(),
    )


@router.message(Command("start"))
async def cmd_start_alias(message: Message, state: FSMContext) -> None:
    """Alias handler — redirect to main start handler."""
    await cmd_start(message, state)

