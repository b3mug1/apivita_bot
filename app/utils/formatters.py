"""
Utility functions for text formatting.
"""
from datetime import datetime
from html import escape
from typing import Optional


def format_price(price: int) -> str:
    """Format price as '3 500 тг'."""
    return f"{price:,}".replace(",", " ") + " тг"


def format_order_status(status: str) -> str:
    """Return status with emoji and human-readable label."""
    STATUS_MAP = {
        "new": "🔵 Новый",
        "confirmed": "🟡 Подтверждён",
        "paid": "🟢 Оплачен",
        "shipped": "🚚 Отправлен",
        "delivered": "✅ Доставлен",
        "cancelled": "❌ Отменён",
    }
    return STATUS_MAP.get(status, f"❓ {status}")


def format_cart_item(
    name: str, weight: str, container: str, qty: int, price: int
) -> str:
    """Return a formatted string for a single cart item."""
    container_str = f" ({container})" if container and container != "-" else ""
    subtotal = price * qty
    return (
        f"• <b>{name} {weight}</b>{container_str}\n"
        f"  {qty} × {format_price(price)} = <b>{format_price(subtotal)}</b>"
    )


def _get_item_fields(item):
    if isinstance(item, dict):
        name = item.get("name") or item.get("product_name") or "Товар"
        price = item.get("price") or item.get("price_per_unit") or 0
        qty = item.get("quantity", 1)
    else:
        name = getattr(item, "product_name", getattr(item, "name", "Товар"))
        price = getattr(item, "price_per_unit", getattr(item, "price", 0))
        qty = getattr(item, "quantity", 1)
    return name, float(price), int(qty)


def format_order_summary(order, items: list) -> str:
    """Return full order summary text with HTML formatting."""
    lines = [
        f"📦 <b>Заказ №<code>{order.id}</code></b>",
        f"📅 {order.created_at.strftime('%d.%m.%Y %H:%M')}",
        f"Статус: {format_order_status(order.status.value if hasattr(order.status, 'value') else order.status)}",
        "",
        "<b>Состав заказа:</b>",
    ]
    for item in items:
        name, price, qty = _get_item_fields(item)
        subtotal = price * qty
        lines.append(f"  • {name} × {qty} = {format_price(subtotal)}")
    lines.append("")
    lines.append(f"💰 <b>Итого: {format_price(order.total_price)}</b>")
    if order.city:
        lines.append(f"🏙 Город: {order.city}")
    if order.address:
        lines.append(f"🏠 Адрес: {order.address}")
    if order.comment:
        lines.append(f"💬 Комментарий: {order.comment}")
    return "\n".join(lines)


def format_admin_order_notification(order, user, items: list) -> str:
    """Format new order notification for admins."""
    user_display = f"@{user.username}" if getattr(user, "username", None) else (user.full_name or "Клиент")
    if getattr(user, "username", None) and user.full_name and user.full_name not in ("-", "", "Клиент"):
        user_display = f"{user.full_name} (@{user.username})"
    user_display = escape(user_display)

    lines = [
        "🆕 <b>Новый заказ!</b>",
        "",
        f"🔖 Номер: <code>{order.id}</code>",
        f"👤 Пользователь: {user_display}",
    ]
    if getattr(user, "phone", None):
        lines.append(f"📞 Телефон: <code>{escape(user.phone)}</code>")
    lines.append("")
    lines.append("<b>Состав:</b>")
    for item in items:
        name, price, qty = _get_item_fields(item)
        subtotal = price * qty
        lines.append(f"  • {escape(name)} × {qty} = {format_price(subtotal)}")
    lines.append("")
    lines.append(f"💰 <b>Итого: {format_price(order.total_price)}</b>")
    if order.city:
        lines.append(f"🏙 Город: {escape(order.city)}")
    if order.address:
        lines.append(f"🏠 Адрес: {escape(order.address)}")
    if order.comment:
        lines.append(f"💬 Комментарий: {escape(order.comment)}")
    lines.append("")
    lines.append("💳 Оплата: перевод на карту")
    return "\n".join(lines)


def truncate_text(text: str, max_len: int = 100) -> str:
    """Truncate text to max_len characters, appending '...' if needed."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def format_datetime(dt: datetime) -> str:
    """Format datetime as 'dd.mm.yyyy hh:mm'."""
    return dt.strftime("%d.%m.%Y %H:%M")
