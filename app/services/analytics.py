"""
Analytics service for logging user actions and generating statistics.
"""
import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import func, select, and_
from loguru import logger

from app.database.repositories import AnalyticsRepository
from app.database.models import Analytics, User, Order, OrderStatus


async def log_action(session, user_id: int, action: str, data: Optional[dict] = None) -> None:
    """Log user action to the analytics table."""
    try:
        repo = AnalyticsRepository(session)
        await repo.log_action(user_id, action, data or {})
    except Exception as e:
        logger.warning(f"Failed to log analytics action '{action}' for user {user_id}: {e}")


async def get_stats(session) -> dict:
    """
    Return aggregated bot statistics.
    
    Returns dict with:
        - total_users: total registered users
        - total_orders: total number of orders
        - revenue_today: total revenue for today (tenge)
        - revenue_week: total revenue for this week
        - new_orders_today: number of new orders today
        - top_actions: most logged actions
    """
    now = datetime.now(tz=timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    try:
        # Total users
        total_users_result = await session.execute(
            select(func.count(User.id)).where(User.is_blocked == False)
        )
        total_users = total_users_result.scalar() or 0

        # Total orders
        total_orders_result = await session.execute(select(func.count(Order.id)))
        total_orders = total_orders_result.scalar() or 0

        # Revenue today (delivered + paid orders)
        revenue_today_result = await session.execute(
            select(func.sum(Order.total_price)).where(
                and_(
                    Order.created_at >= today_start,
                    Order.status.in_([OrderStatus.paid, OrderStatus.delivered]),
                )
            )
        )
        revenue_today = revenue_today_result.scalar() or 0

        # Revenue this week
        revenue_week_result = await session.execute(
            select(func.sum(Order.total_price)).where(
                and_(
                    Order.created_at >= week_start,
                    Order.status.in_([OrderStatus.paid, OrderStatus.delivered]),
                )
            )
        )
        revenue_week = revenue_week_result.scalar() or 0

        # New orders today
        new_orders_today_result = await session.execute(
            select(func.count(Order.id)).where(Order.created_at >= today_start)
        )
        new_orders_today = new_orders_today_result.scalar() or 0

        return {
            "total_users": total_users,
            "total_orders": total_orders,
            "revenue_today": revenue_today,
            "revenue_week": revenue_week,
            "new_orders_today": new_orders_today,
        }

    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return {
            "total_users": 0,
            "total_orders": 0,
            "revenue_today": 0,
            "revenue_week": 0,
            "new_orders_today": 0,
        }


def format_stats_message(stats: dict) -> str:
    """Format statistics dict into a human-readable message."""
    from app.utils.formatters import format_price
    return (
        "📊 <b>Статистика бота</b>\n\n"
        f"👥 Всего пользователей: <b>{stats['total_users']}</b>\n"
        f"📦 Всего заказов: <b>{stats['total_orders']}</b>\n"
        f"🆕 Заказов сегодня: <b>{stats['new_orders_today']}</b>\n\n"
        f"💰 Выручка сегодня: <b>{format_price(stats['revenue_today'])}</b>\n"
        f"💰 Выручка за неделю: <b>{format_price(stats['revenue_week'])}</b>"
    )

