"""
Middlewares for Apivita Telegram bot (Aiogram 3).

Included:
- AuthMiddleware   : blocks unregistered users from non-start actions
- LoggingMiddleware: logs every update
- ThrottlingMiddleware: rate-limits to 1 message per 0.5 s per user
"""

import logging
import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import (
    CallbackQuery,
    Message,
    TelegramObject,
    Update,
)

from app.database.connection import get_session
from app.database.repositories import UserRepository

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# AuthMiddleware
# ---------------------------------------------------------------------------

_ALLOWED_COMMANDS_FOR_GUESTS = {"/start", "/help"}


class AuthMiddleware(BaseMiddleware):
    """
    Allows unregistered users (no phone number in DB) only to:
      - send /start or /help
      - share a contact (for registration)
    All other updates are blocked with a prompt to register first.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Resolve telegram_id from the event
        telegram_id: int | None = None
        is_contact_share = False

        if isinstance(event, Message):
            telegram_id = event.from_user.id if event.from_user else None

            # Allow /start and /help for everyone
            if event.text and any(
                event.text.startswith(cmd) for cmd in _ALLOWED_COMMANDS_FOR_GUESTS
            ):
                return await handler(event, data)

            # Allow contact sharing (for registration step)
            if event.contact is not None:
                is_contact_share = True

        elif isinstance(event, CallbackQuery):
            telegram_id = event.from_user.id if event.from_user else None

        if telegram_id is None:
            # Can't identify user — let pass (e.g. channel posts)
            return await handler(event, data)

        # Check registration
        async for session in get_session():
            repo = UserRepository(session)
            user = await repo.get_by_telegram_id(telegram_id)

        is_registered = user is not None and user.phone is not None

        if is_registered or is_contact_share:
            return await handler(event, data)

        # Unregistered user — block and prompt
        if isinstance(event, Message):
            await event.answer(
                "👋 Для использования бота необходимо пройти регистрацию.\n"
                "Введите /start чтобы начать.",
            )
        elif isinstance(event, CallbackQuery):
            await event.answer(
                "Сначала пройдите регистрацию: /start",
                show_alert=True,
            )

        return None  # Do not call handler


# ---------------------------------------------------------------------------
# LoggingMiddleware
# ---------------------------------------------------------------------------

class LoggingMiddleware(BaseMiddleware):
    """
    Logs every incoming update with:
    - user_id
    - message type  (message / callback_query / etc.)
    - text or callback data (truncated)
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user_id: int | None = None
        event_type = type(event).__name__
        payload: str = ""

        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
            if event.text:
                payload = event.text[:80]
            elif event.caption:
                payload = f"[caption] {event.caption[:80]}"
            elif event.contact:
                payload = "[contact share]"
            elif event.photo:
                payload = "[photo]"
            elif event.video:
                payload = "[video]"
            elif event.document:
                payload = "[document]"
            else:
                payload = "[other media]"

        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
            payload = event.data or ""

        logger.info(
            "UPDATE | type=%s | user_id=%s | payload=%r",
            event_type,
            user_id,
            payload,
        )

        return await handler(event, data)


# ---------------------------------------------------------------------------
# ThrottlingMiddleware
# ---------------------------------------------------------------------------

THROTTLE_RATE: float = 0.5  # seconds between allowed messages per user


class ThrottlingMiddleware(BaseMiddleware):
    """
    Simple in-memory rate limiter: 1 message per THROTTLE_RATE seconds per user.
    Uses a plain dict; suitable for single-process deployments.
    For multi-process setups, switch to Redis-backed storage.
    """

    def __init__(self, rate: float = THROTTLE_RATE, rate_limit: float | None = None) -> None:
        super().__init__()
        self._rate = rate_limit if rate_limit is not None else rate
        self._last_seen: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user_id: int | None = None

        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None

        if user_id is None:
            return await handler(event, data)

        now = time.monotonic()
        last = self._last_seen.get(user_id, 0.0)

        if now - last < self._rate:
            # Too fast — silently drop or answer callback
            if isinstance(event, CallbackQuery):
                await event.answer("⏳ Не так быстро, пожалуйста.", show_alert=False)
            logger.debug("Throttled user_id=%s", user_id)
            return None

        self._last_seen[user_id] = now
        return await handler(event, data)
