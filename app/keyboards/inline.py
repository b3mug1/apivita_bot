"""
Inline keyboards for Apivita Telegram bot (Aiogram 3).

All keyboards use either InlineKeyboardBuilder (for dynamic rows)
or direct InlineKeyboardMarkup construction.

Product ID naming convention
─────────────────────────────
Plastic honey  →  plastic_<slug>_<weight>   e.g. plastic_sunflower_1kg
Glass honey    →  glass_<slug>_<weight>     e.g. glass_buckwheat_500g
Other products →  other_<slug>              e.g. other_perga
"""

from typing import Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ─────────────────────────────────────────────────────────────
# Catalogue root
# ─────────────────────────────────────────────────────────────

def catalog_categories_keyboard() -> InlineKeyboardMarkup:
    """Top-level catalogue: three honey categories + Back."""
    builder = InlineKeyboardBuilder()

    builder.button(text="🍯 Мёд в пластике",   callback_data="cat:plastic")
    builder.button(text="🍯 Мёд в стекле",     callback_data="cat:glass")
    builder.button(text="🌿 Другие продукты",  callback_data="cat:other")
    builder.button(text="◀️ Назад",             callback_data="back:main")

    builder.adjust(1)  # one button per row for readability
    return builder.as_markup()


# ─────────────────────────────────────────────────────────────
# Internal data: honey product definitions
# ─────────────────────────────────────────────────────────────

_HONEY_SLUGS = [
    ("подсолнуховый", "sunflower"),
    ("гречишный",     "buckwheat"),
    ("жантачный",     "zhantach"),
    ("степной",       "steppe"),
    ("горный",        "mountain"),
    ("разнотравье",   "meadow"),
    ("акациевый",     "acacia"),
    ("липовый",       "linden"),
]

# Prices: first 6 varieties are "standard", last 2 (acacia/linden) are "premium"
_PLASTIC_WEIGHTS = [("1кг", "1kg"), ("500гр", "500g"), ("200гр", "200g")]
_PLASTIC_PRICES_STD     = {  "1kg": 3500, "500g": 1900, "200g":  900}
_PLASTIC_PRICES_PREMIUM = {  "1kg": 5500, "500g": 3000, "200g": 1400}

_GLASS_WEIGHTS  = [("1кг", "1kg"), ("500гр", "500g"), ("300гр", "300g"), ("150гр", "150g")]
_GLASS_PRICES_STD     = {"1kg": 4000, "500g": 2200, "300g": 1300, "150g":  900}
_GLASS_PRICES_PREMIUM = {"1kg": 6000, "500g": 3300, "300g": 2000, "150g": 1400}


def _is_premium(slug_en: str) -> bool:
    return slug_en in {"acacia", "linden"}


# ─────────────────────────────────────────────────────────────
# Plastic honey keyboard
# ─────────────────────────────────────────────────────────────

def plastic_honey_keyboard() -> InlineKeyboardMarkup:
    """
    All plastic honey products (8 varieties × 3 weights = 24 buttons) + Back.
    Each button label: «Мёд [name] [weight] – [price]тг»
    Callback:          «prod:plastic_<slug>_<weight>»
    """
    builder = InlineKeyboardBuilder()

    for name_ru, name_en in _HONEY_SLUGS:
        prices = _PLASTIC_PRICES_PREMIUM if _is_premium(name_en) else _PLASTIC_PRICES_STD
        for weight_ru, weight_en in _PLASTIC_WEIGHTS:
            product_id = f"plastic_{name_en}_{weight_en}"
            price      = prices[weight_en]
            label      = f"Мёд {name_ru} {weight_ru} – {price:,}тг".replace(",", " ")
            builder.button(text=label, callback_data=f"prod:{product_id}")

    builder.button(text="◀️ Назад", callback_data="back:catalog")

    # 3 columns (one per weight variant per variety), back button on its own row
    builder.adjust(*([3] * len(_HONEY_SLUGS)), 1)
    return builder.as_markup()


# ─────────────────────────────────────────────────────────────
# Glass honey keyboard
# ─────────────────────────────────────────────────────────────

def glass_honey_keyboard() -> InlineKeyboardMarkup:
    """
    All glass honey products (8 varieties × 4 sizes = 32 buttons) + Back.
    Callback: «prod:glass_<slug>_<size>»
    """
    builder = InlineKeyboardBuilder()

    for name_ru, name_en in _HONEY_SLUGS:
        prices = _GLASS_PRICES_PREMIUM if _is_premium(name_en) else _GLASS_PRICES_STD
        for weight_ru, weight_en in _GLASS_WEIGHTS:
            product_id = f"glass_{name_en}_{weight_en}"
            price      = prices[weight_en]
            label      = f"Мёд {name_ru} {weight_ru} – {price:,}тг".replace(",", " ")
            builder.button(text=label, callback_data=f"prod:{product_id}")

    builder.button(text="◀️ Назад", callback_data="back:catalog")

    # 4 columns (one per size variant), back on its own row
    builder.adjust(*([4] * len(_HONEY_SLUGS)), 1)
    return builder.as_markup()


# ─────────────────────────────────────────────────────────────
# Other products keyboard
# ─────────────────────────────────────────────────────────────

_OTHER_PRODUCTS = [
    ("🐝 Перга 25 000тг/кг",          "other_perga"),
    ("🌸 Пыльца 10 000тг/кг",         "other_pollen"),
    ("🟤 Прополис 1 000тг/10гр",       "other_propolis"),
    ("🍯 Сотовый мёд 10 000тг/1.7-2кг", "other_honeycomb"),
]


def other_products_keyboard() -> InlineKeyboardMarkup:
    """
    Other bee products + Back.
    """
    builder = InlineKeyboardBuilder()

    for label, product_id in _OTHER_PRODUCTS:
        builder.button(text=label, callback_data=f"prod:{product_id}")

    builder.button(text="◀️ Назад", callback_data="back:catalog")
    builder.adjust(1)
    return builder.as_markup()


# ─────────────────────────────────────────────────────────────
# Product detail keyboard
# ─────────────────────────────────────────────────────────────

def product_detail_keyboard(
    product_id: str,
    in_cart: bool = False,
) -> InlineKeyboardMarkup:
    """
    Shown on a single product's detail page.
    • If not in cart  → «➕ В корзину»
    • If already in cart → «✅ В корзине»  (still clickable to add another)
    Always shows «◀️ Назад».
    """
    builder = InlineKeyboardBuilder()

    cart_label = "✅ В корзине (добавить ещё)" if in_cart else "➕ В корзину"
    builder.button(text=cart_label,  callback_data=f"add_cart:{product_id}")
    builder.button(text="◀️ Назад",  callback_data="back:catalog")

    builder.adjust(1)
    return builder.as_markup()


# ─────────────────────────────────────────────────────────────
# Cart keyboard
# ─────────────────────────────────────────────────────────────

def cart_keyboard(has_items: bool = True) -> InlineKeyboardMarkup:
    """
    Cart view keyboard.
    has_items=True  → Checkout | Clear | Back
    has_items=False → Back only
    """
    builder = InlineKeyboardBuilder()

    if has_items:
        builder.button(text="✅ Оформить заказ", callback_data="checkout")
        builder.button(text="🗑️ Очистить корзину", callback_data="clear_cart")

    builder.button(text="◀️ Назад", callback_data="back:main")

    builder.adjust(1)
    return builder.as_markup()


# ─────────────────────────────────────────────────────────────
# Quantity selector keyboard
# ─────────────────────────────────────────────────────────────

def quantity_keyboard(product_id: str) -> InlineKeyboardMarkup:
    """
    Quantity picker 1-5 for a given product, plus Back.
    Callbacks: «qty:<product_id>:<n>»
    """
    builder = InlineKeyboardBuilder()

    for qty in range(1, 6):
        builder.button(
            text=str(qty),
            callback_data=f"qty:{product_id}:{qty}",
        )

    builder.button(text="◀️ Назад", callback_data="back:product")

    # 5 quantity buttons in one row, Back on its own
    builder.adjust(5, 1)
    return builder.as_markup()


# ─────────────────────────────────────────────────────────────
# Order confirmation keyboard
# ─────────────────────────────────────────────────────────────

def order_confirm_keyboard() -> InlineKeyboardMarkup:
    """
    Final order confirmation dialog.
    """
    builder = InlineKeyboardBuilder()

    builder.button(text="✅ Подтвердить", callback_data="order:confirm")
    builder.button(text="✏️ Изменить",    callback_data="order:edit")
    builder.button(text="❌ Отмена",      callback_data="order:cancel")

    builder.adjust(1)
    return builder.as_markup()


# ─────────────────────────────────────────────────────────────
# Admin: order status keyboard
# ─────────────────────────────────────────────────────────────

def admin_order_keyboard(order_id: int | str) -> InlineKeyboardMarkup:
    """
    Sent to admins alongside a new/updated order notification.
    Allows updating the order status directly from Telegram.
    """
    builder = InlineKeyboardBuilder()

    statuses = [
        ("✅ Подтвердить", "confirmed"),
        ("💰 Оплачен",    "paid"),
        ("🚚 Отправлен",  "shipped"),
        ("📦 Доставлен",  "delivered"),
        ("❌ Отменить",   "cancelled"),
    ]

    for label, status in statuses:
        builder.button(
            text=label,
            callback_data=f"admin_status:{order_id}:{status}",
        )

    builder.adjust(2, 2, 1)  # 2 | 2 | 1 layout
    return builder.as_markup()


# ─────────────────────────────────────────────────────────────
# Admin: broadcast confirmation keyboard
# ─────────────────────────────────────────────────────────────

def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    """
    Confirmation step before sending a broadcast message to all users.
    """
    builder = InlineKeyboardBuilder()

    builder.button(text="✅ Отправить рассылку", callback_data="broadcast:confirm")
    builder.button(text="❌ Отмена",              callback_data="broadcast:cancel")

    builder.adjust(1)
    return builder.as_markup()


# ─────────────────────────────────────────────────────────────
# Convenience: expose all product IDs (useful for handlers / DB seeding)
# ─────────────────────────────────────────────────────────────

def get_all_product_ids() -> list[str]:
    """Return every possible product_id used across all keyboards."""
    ids: list[str] = []

    for _, name_en in _HONEY_SLUGS:
        for _, weight_en in _PLASTIC_WEIGHTS:
            ids.append(f"plastic_{name_en}_{weight_en}")
        for _, weight_en in _GLASS_WEIGHTS:
            ids.append(f"glass_{name_en}_{weight_en}")

    ids.extend(pid for _, pid in _OTHER_PRODUCTS)
    return ids
