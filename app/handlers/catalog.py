"""
Catalog handler for Apivita honey store bot.
Handles browsing categories, products and adding items to cart.
"""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from app.database.repositories import CartRepository, AnalyticsRepository
from app.database.connection import get_session

logger = logging.getLogger(__name__)

router = Router(name="catalog")

# ---------------------------------------------------------------------------
# Products catalogue
# ---------------------------------------------------------------------------

PRODUCTS = {
    # === PLASTIC ===
    "p_sunflower_1kg":  {"name": "Мёд подсолнуховый", "container": "пластик", "weight": "1кг",      "price": 3500,  "category": "plastic"},
    "p_sunflower_500":  {"name": "Мёд подсолнуховый", "container": "пластик", "weight": "500гр",    "price": 1900,  "category": "plastic"},
    "p_sunflower_200":  {"name": "Мёд подсолнуховый", "container": "пластик", "weight": "200гр",    "price": 900,   "category": "plastic"},
    "p_buckwheat_1kg":  {"name": "Мёд гречишный",     "container": "пластик", "weight": "1кг",      "price": 3500,  "category": "plastic"},
    "p_buckwheat_500":  {"name": "Мёд гречишный",     "container": "пластик", "weight": "500гр",    "price": 1900,  "category": "plastic"},
    "p_buckwheat_200":  {"name": "Мёд гречишный",     "container": "пластик", "weight": "200гр",    "price": 900,   "category": "plastic"},
    "p_zhantac_1kg":    {"name": "Мёд жантачный",     "container": "пластик", "weight": "1кг",      "price": 3500,  "category": "plastic"},
    "p_zhantac_500":    {"name": "Мёд жантачный",     "container": "пластик", "weight": "500гр",    "price": 1900,  "category": "plastic"},
    "p_zhantac_200":    {"name": "Мёд жантачный",     "container": "пластик", "weight": "200гр",    "price": 900,   "category": "plastic"},
    "p_steppe_1kg":     {"name": "Мёд степной",       "container": "пластик", "weight": "1кг",      "price": 3500,  "category": "plastic"},
    "p_steppe_500":     {"name": "Мёд степной",       "container": "пластик", "weight": "500гр",    "price": 1900,  "category": "plastic"},
    "p_steppe_200":     {"name": "Мёд степной",       "container": "пластик", "weight": "200гр",    "price": 900,   "category": "plastic"},
    "p_mountain_1kg":   {"name": "Мёд горный",        "container": "пластик", "weight": "1кг",      "price": 3500,  "category": "plastic"},
    "p_mountain_500":   {"name": "Мёд горный",        "container": "пластик", "weight": "500гр",    "price": 1900,  "category": "plastic"},
    "p_mountain_200":   {"name": "Мёд горный",        "container": "пластик", "weight": "200гр",    "price": 900,   "category": "plastic"},
    "p_mixed_1kg":      {"name": "Мёд разнотравье",   "container": "пластик", "weight": "1кг",      "price": 3500,  "category": "plastic"},
    "p_mixed_500":      {"name": "Мёд разнотравье",   "container": "пластик", "weight": "500гр",    "price": 1900,  "category": "plastic"},
    "p_mixed_200":      {"name": "Мёд разнотравье",   "container": "пластик", "weight": "200гр",    "price": 900,   "category": "plastic"},
    "p_acacia_1kg":     {"name": "Мёд акациевый",     "container": "пластик", "weight": "1кг",      "price": 5500,  "category": "plastic"},
    "p_acacia_500":     {"name": "Мёд акациевый",     "container": "пластик", "weight": "500гр",    "price": 3000,  "category": "plastic"},
    "p_acacia_200":     {"name": "Мёд акациевый",     "container": "пластик", "weight": "200гр",    "price": 1400,  "category": "plastic"},
    "p_linden_1kg":     {"name": "Мёд липовый",       "container": "пластик", "weight": "1кг",      "price": 5500,  "category": "plastic"},
    "p_linden_500":     {"name": "Мёд липовый",       "container": "пластик", "weight": "500гр",    "price": 3000,  "category": "plastic"},
    "p_linden_200":     {"name": "Мёд липовый",       "container": "пластик", "weight": "200гр",    "price": 1400,  "category": "plastic"},
    # === GLASS ===
    "g_sunflower_1kg":  {"name": "Мёд подсолнуховый", "container": "стекло",  "weight": "1кг",      "price": 4000,  "category": "glass"},
    "g_sunflower_500":  {"name": "Мёд подсолнуховый", "container": "стекло",  "weight": "500гр",    "price": 2200,  "category": "glass"},
    "g_sunflower_300":  {"name": "Мёд подсолнуховый", "container": "стекло",  "weight": "300гр",    "price": 1300,  "category": "glass"},
    "g_sunflower_150":  {"name": "Мёд подсолнуховый", "container": "стекло",  "weight": "150гр",    "price": 900,   "category": "glass"},
    "g_buckwheat_1kg":  {"name": "Мёд гречишный",     "container": "стекло",  "weight": "1кг",      "price": 4000,  "category": "glass"},
    "g_buckwheat_500":  {"name": "Мёд гречишный",     "container": "стекло",  "weight": "500гр",    "price": 2200,  "category": "glass"},
    "g_buckwheat_300":  {"name": "Мёд гречишный",     "container": "стекло",  "weight": "300гр",    "price": 1300,  "category": "glass"},
    "g_buckwheat_150":  {"name": "Мёд гречишный",     "container": "стекло",  "weight": "150гр",    "price": 900,   "category": "glass"},
    "g_zhantac_1kg":    {"name": "Мёд жантачный",     "container": "стекло",  "weight": "1кг",      "price": 4000,  "category": "glass"},
    "g_zhantac_500":    {"name": "Мёд жантачный",     "container": "стекло",  "weight": "500гр",    "price": 2200,  "category": "glass"},
    "g_zhantac_300":    {"name": "Мёд жантачный",     "container": "стекло",  "weight": "300гр",    "price": 1300,  "category": "glass"},
    "g_zhantac_150":    {"name": "Мёд жантачный",     "container": "стекло",  "weight": "150гр",    "price": 900,   "category": "glass"},
    "g_steppe_1kg":     {"name": "Мёд степной",       "container": "стекло",  "weight": "1кг",      "price": 4000,  "category": "glass"},
    "g_steppe_500":     {"name": "Мёд степной",       "container": "стекло",  "weight": "500гр",    "price": 2200,  "category": "glass"},
    "g_steppe_300":     {"name": "Мёд степной",       "container": "стекло",  "weight": "300гр",    "price": 1300,  "category": "glass"},
    "g_steppe_150":     {"name": "Мёд степной",       "container": "стекло",  "weight": "150гр",    "price": 900,   "category": "glass"},
    "g_mountain_1kg":   {"name": "Мёд горный",        "container": "стекло",  "weight": "1кг",      "price": 4000,  "category": "glass"},
    "g_mountain_500":   {"name": "Мёд горный",        "container": "стекло",  "weight": "500гр",    "price": 2200,  "category": "glass"},
    "g_mountain_300":   {"name": "Мёд горный",        "container": "стекло",  "weight": "300гр",    "price": 1300,  "category": "glass"},
    "g_mountain_150":   {"name": "Мёд горный",        "container": "стекло",  "weight": "150гр",    "price": 900,   "category": "glass"},
    "g_mixed_1kg":      {"name": "Мёд разнотравье",   "container": "стекло",  "weight": "1кг",      "price": 4000,  "category": "glass"},
    "g_mixed_500":      {"name": "Мёд разнотравье",   "container": "стекло",  "weight": "500гр",    "price": 2200,  "category": "glass"},
    "g_mixed_300":      {"name": "Мёд разнотравье",   "container": "стекло",  "weight": "300гр",    "price": 1300,  "category": "glass"},
    "g_mixed_150":      {"name": "Мёд разнотравье",   "container": "стекло",  "weight": "150гр",    "price": 900,   "category": "glass"},
    "g_acacia_1kg":     {"name": "Мёд акациевый",     "container": "стекло",  "weight": "1кг",      "price": 6000,  "category": "glass"},
    "g_acacia_500":     {"name": "Мёд акациевый",     "container": "стекло",  "weight": "500гр",    "price": 3300,  "category": "glass"},
    "g_acacia_300":     {"name": "Мёд акациевый",     "container": "стекло",  "weight": "300гр",    "price": 2000,  "category": "glass"},
    "g_acacia_150":     {"name": "Мёд акациевый",     "container": "стекло",  "weight": "150гр",    "price": 1400,  "category": "glass"},
    "g_linden_1kg":     {"name": "Мёд липовый",       "container": "стекло",  "weight": "1кг",      "price": 6000,  "category": "glass"},
    "g_linden_500":     {"name": "Мёд липовый",       "container": "стекло",  "weight": "500гр",    "price": 3300,  "category": "glass"},
    "g_linden_300":     {"name": "Мёд липовый",       "container": "стекло",  "weight": "300гр",    "price": 2000,  "category": "glass"},
    "g_linden_150":     {"name": "Мёд липовый",       "container": "стекло",  "weight": "150гр",    "price": 1400,  "category": "glass"},
    # === OTHER ===
    "other_perga":      {"name": "Перга",              "container": "-",       "weight": "1кг",      "price": 25000, "category": "other"},
    "other_pollen":     {"name": "Пыльца",             "container": "-",       "weight": "1кг",      "price": 10000, "category": "other"},
    "other_propolis":   {"name": "Прополис",           "container": "-",       "weight": "10гр",     "price": 1000,  "category": "other"},
    "other_comb":       {"name": "Сотовый мёд",        "container": "-",       "weight": "1.7-2кг",  "price": 10000, "category": "other"},
}

CATEGORY_LABELS = {
    "plastic": "🍯 Пластик",
    "glass":   "🫙 Стекло",
    "other":   "🌿 Другое",
}


@router.message(Command("tags"))
@router.message(F.text.regexp(r"^/теги(?:@\w+)?(?:\s|$)"))
async def show_catalog_tags(message: Message) -> None:
    """Show the catalog categories available as product tags."""
    await message.answer(
        "🏷 <b>Категории товаров</b>\n\nВыберите раздел, чтобы посмотреть товары:",
        reply_markup=categories_keyboard(),
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# Keyboard builders
# ---------------------------------------------------------------------------

def categories_keyboard():
    """Inline keyboard with the three main categories + back to main menu."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🍯 Пластиковая тара",  callback_data="cat:plastic")
    builder.button(text="🫙 Стеклянная тара",   callback_data="cat:glass")
    builder.button(text="🌿 Другое",            callback_data="cat:other")
    builder.button(text="🏠 Главное меню",       callback_data="back:main")
    builder.adjust(2, 1, 1)
    return builder.as_markup()


def product_list_keyboard(category: str):
    """Inline keyboard listing all products in the given category."""
    builder = InlineKeyboardBuilder()
    category_products = {pid: p for pid, p in PRODUCTS.items() if p["category"] == category}
    for pid, product in category_products.items():
        label = f"{product['name']} {product['weight']} — {product['price']:,} ₸"
        builder.button(text=label, callback_data=f"prod:{pid}")
    builder.button(text="⬅️ Назад к категориям", callback_data="back:catalog")
    builder.adjust(1)
    return builder.as_markup()


def product_detail_keyboard(product_id: str):
    """Inline keyboard shown on a product detail page."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Добавить в корзину", callback_data=f"add_cart:{product_id}")
    builder.button(
        text="⬅️ Назад",
        callback_data=f"cat:{PRODUCTS[product_id]['category']}",
    )
    builder.adjust(1)
    return builder.as_markup()


def quantity_keyboard(product_id: str):
    """Inline keyboard for selecting quantity 1–5."""
    builder = InlineKeyboardBuilder()
    for qty in range(1, 6):
        builder.button(text=str(qty), callback_data=f"qty:{product_id}:{qty}")
    builder.button(text="❌ Отмена", callback_data=f"prod:{product_id}")
    builder.adjust(5, 1)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_product_detail(pid: str) -> str:
    p = PRODUCTS[pid]
    container_line = f"📦 Тара: {p['container']}\n" if p["container"] != "-" else ""
    return (
        f"<b>{p['name']}</b>\n\n"
        f"⚖️ Вес: {p['weight']}\n"
        f"{container_line}"
        f"💰 Цена: <b>{p['price']:,} ₸</b>"
    )


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

@router.message(Command("catalog"))
@router.message(F.text == "🛒 Каталог")
async def show_catalog(message: Message) -> None:
    """Entry point: show category selector."""
    logger.info("User %s opened catalog", message.from_user.id)
    try:
        async with get_session() as session:
            analytics = AnalyticsRepository(session)
            await analytics.log_event(
                user_id=message.from_user.id,
                event="catalog_open",
            )
    except Exception:
        logger.exception("Analytics log failed for catalog_open")

    await message.answer(
        "🍯 <b>Каталог Apivita</b>\n\nВыберите категорию:",
        reply_markup=categories_keyboard(),
        parse_mode="HTML",
    )


# --- Category callbacks ---

@router.callback_query(F.data == "cat:plastic")
async def category_plastic(callback: CallbackQuery) -> None:
    await _show_category(callback, "plastic")


@router.callback_query(F.data == "cat:glass")
async def category_glass(callback: CallbackQuery) -> None:
    await _show_category(callback, "glass")


@router.callback_query(F.data == "cat:other")
async def category_other(callback: CallbackQuery) -> None:
    await _show_category(callback, "other")


async def _show_category(callback: CallbackQuery, category: str) -> None:
    logger.info("User %s browsing category '%s'", callback.from_user.id, category)
    try:
        async with get_session() as session:
            analytics = AnalyticsRepository(session)
            await analytics.log_event(
                user_id=callback.from_user.id,
                event="category_view",
                payload={"category": category},
            )
    except Exception:
        logger.exception("Analytics log failed for category_view")

    label = CATEGORY_LABELS.get(category, category)
    count = sum(1 for p in PRODUCTS.values() if p["category"] == category)
    await callback.message.edit_text(
        f"<b>{label}</b> — {count} позиций\n\nВыберите товар:",
        reply_markup=product_list_keyboard(category),
        parse_mode="HTML",
    )
    await callback.answer()


# --- Product detail ---

@router.callback_query(F.data.startswith("prod:"))
async def show_product(callback: CallbackQuery) -> None:
    product_id = callback.data.split(":", 1)[1]
    if product_id not in PRODUCTS:
        await callback.answer("Товар не найден.", show_alert=True)
        return

    logger.info("User %s viewing product '%s'", callback.from_user.id, product_id)
    try:
        async with get_session() as session:
            analytics = AnalyticsRepository(session)
            await analytics.log_event(
                user_id=callback.from_user.id,
                event="product_view",
                payload={"product_id": product_id},
            )
    except Exception:
        logger.exception("Analytics log failed for product_view")

    await callback.message.edit_text(
        _format_product_detail(product_id),
        reply_markup=product_detail_keyboard(product_id),
        parse_mode="HTML",
    )
    await callback.answer()


# --- Add to cart: show quantity selector ---

@router.callback_query(F.data.startswith("add_cart:"))
async def add_to_cart_select_qty(callback: CallbackQuery) -> None:
    product_id = callback.data.split(":", 1)[1]
    if product_id not in PRODUCTS:
        await callback.answer("Товар не найден.", show_alert=True)
        return

    product = PRODUCTS[product_id]
    await callback.message.edit_text(
        f"<b>{product['name']} {product['weight']}</b>\n\n"
        f"Выберите количество:",
        reply_markup=quantity_keyboard(product_id),
        parse_mode="HTML",
    )
    await callback.answer()


# --- Quantity selected: add to cart ---

@router.callback_query(F.data.startswith("qty:"))
async def add_to_cart_confirm(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Неверный формат данных.", show_alert=True)
        return

    _, product_id, qty_str = parts
    if product_id not in PRODUCTS:
        await callback.answer("Товар не найден.", show_alert=True)
        return

    try:
        qty = int(qty_str)
    except ValueError:
        await callback.answer("Неверное количество.", show_alert=True)
        return

    product = PRODUCTS[product_id]
    user_id = callback.from_user.id

    try:
        async with get_session() as session:
            cart_repo = CartRepository(session)
            await cart_repo.add_item(
                user_id=user_id,
                product_id=product_id,
                quantity=qty,
                price=product["price"],
                name=product["name"],
                weight=product["weight"],
            )
            analytics = AnalyticsRepository(session)
            await analytics.log_event(
                user_id=user_id,
                event="add_to_cart",
                payload={"product_id": product_id, "quantity": qty},
            )
    except Exception:
        logger.exception("Failed to add product '%s' to cart for user %s", product_id, user_id)
        await callback.answer("❌ Ошибка при добавлении в корзину. Попробуйте позже.", show_alert=True)
        return

    logger.info("User %s added %d × '%s' to cart", user_id, qty, product_id)

    subtotal = product["price"] * qty
    await callback.answer(
        f"✅ Добавлено: {product['name']} {product['weight']} × {qty}\n"
        f"Сумма: {subtotal:,} ₸",
        show_alert=True,
    )

    # Return to product detail
    await callback.message.edit_text(
        _format_product_detail(product_id),
        reply_markup=product_detail_keyboard(product_id),
        parse_mode="HTML",
    )


# --- Back navigations ---

@router.callback_query(F.data == "back:catalog")
async def back_to_catalog(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "🍯 <b>Каталог Apivita</b>\n\nВыберите категорию:",
        reply_markup=categories_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "back:main")
async def back_to_main(callback: CallbackQuery) -> None:
    await callback.message.delete()
    await callback.message.answer(
        "🏠 Вы в главном меню.\n\nВыберите раздел с помощью кнопок ниже.",
    )
    await callback.answer()
