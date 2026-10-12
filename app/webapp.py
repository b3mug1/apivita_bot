import hashlib
import hmac
import json
import time
from types import SimpleNamespace
from urllib.parse import parse_qsl

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Update
from fastapi import Depends, FastAPI, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database.connection import get_session
from app.database.models import Cart, Order, OrderItem, OrderStatus, Product, User
from app.database.repositories import UserRepository
from app.middlewares.auth import AuthMiddleware, LoggingMiddleware, ThrottlingMiddleware


app = FastAPI()
bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dispatcher: Dispatcher | None = None


def _get_dispatcher() -> Dispatcher:
    global dispatcher
    if dispatcher is None:
        if not settings.REDIS_URL:
            raise HTTPException(status_code=503, detail="Redis storage is not configured.")
        from app.handlers import admin, cart as cart_handler, catalog, info, orders, start

        dispatcher = Dispatcher(storage=RedisStorage.from_url(settings.REDIS_URL))
        for router in (start.router, catalog.router, cart_handler.router, orders.router, info.router, admin.router):
            dispatcher.include_router(router)
        dispatcher.message.middleware(LoggingMiddleware())
        dispatcher.callback_query.middleware(LoggingMiddleware())
        dispatcher.message.middleware(ThrottlingMiddleware(rate_limit=0.5))
        dispatcher.message.middleware(AuthMiddleware())
        dispatcher.callback_query.middleware(AuthMiddleware())
    return dispatcher


def _telegram_user(request: Request) -> dict:
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    try:
        values = dict(parse_qsl(init_data, strict_parsing=True))
        received_hash = values.pop("hash")
        auth_date = int(values["auth_date"])
        now = time.time()
        if now - auth_date > 86400 or auth_date > now + 30:
            raise ValueError("expired init data")
        data_check = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
        secret = hmac.new(b"WebAppData", settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
        expected_hash = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_hash, received_hash):
            raise ValueError("invalid init data signature")
        user = json.loads(values["user"])
        if not isinstance(user.get("id"), int):
            raise ValueError("invalid user")
        return user
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="Откройте приложение из Telegram.")


def _telegram_user_dependency(request: Request) -> dict:
    return _telegram_user(request)


@app.get("/api/products")
async def products():
    async with get_session() as session:
        result = await session.execute(
            select(Product).where(Product.is_active.is_(True)).order_by(Product.category, Product.name, Product.weight_grams)
        )
        return [{
            "id": p.id, "name": p.name, "category": p.category,
            "container": p.container_type, "weight": p.weight_grams,
            "price": float(p.price), "description": p.description,
        } for p in result.scalars()]


async def _get_user(session, telegram_user: dict) -> User:
    repo = UserRepository(session)
    user, _ = await repo.get_or_create(
        telegram_id=telegram_user["id"],
        username=telegram_user.get("username", ""),
        full_name=" ".join(filter(None, [telegram_user.get("first_name"), telegram_user.get("last_name")])),
    )
    if user.is_blocked:
        raise HTTPException(status_code=403, detail="Аккаунт заблокирован.")
    return user


@app.get("/api/cart")
async def get_cart(telegram_user: dict = Depends(_telegram_user_dependency)):
    async with get_session() as session:
        user = await _get_user(session, telegram_user)
        result = await session.execute(
            select(Cart).options(selectinload(Cart.product)).where(Cart.user_id == user.id)
        )
        items = result.scalars().all()
        return {
            "items": [{"product_id": i.product_id, "name": i.product.name,
                       "weight": i.product.weight_grams, "price": float(i.product.price),
                       "quantity": i.quantity} for i in items],
            "total": sum(float(i.product.price) * i.quantity for i in items),
        }


@app.post("/api/cart")
async def update_cart(request: Request, telegram_user: dict = Depends(_telegram_user_dependency)):
    try:
        data = await request.json()
        product_id, quantity = int(data["product_id"]), int(data["quantity"])
    except (ValueError, KeyError, TypeError):
        raise HTTPException(status_code=400, detail="Некорректный товар или количество.")
    if not 1 <= quantity <= 99:
        raise HTTPException(status_code=400, detail="Количество должно быть от 1 до 99.")
    async with get_session() as session:
        user = await _get_user(session, telegram_user)
        product = await session.get(Product, product_id)
        if not product or not product.is_active:
            raise HTTPException(status_code=404, detail="Товар не найден.")
        item = await session.scalar(select(Cart).where(Cart.user_id == user.id, Cart.product_id == product_id))
        if item:
            item.quantity = quantity
        else:
            session.add(Cart(user_id=user.id, product_id=product_id, quantity=quantity))
        return {"ok": True}


@app.delete("/api/cart/{product_id}")
async def delete_cart_item(product_id: int, telegram_user: dict = Depends(_telegram_user_dependency)):
    try:
        product_id = int(product_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Некорректный товар.")
    async with get_session() as session:
        user = await _get_user(session, telegram_user)
        item = await session.scalar(select(Cart).where(Cart.user_id == user.id, Cart.product_id == product_id))
        if item:
            await session.delete(item)
        return {"ok": True}


@app.get("/api/orders")
async def get_orders(telegram_user: dict = Depends(_telegram_user_dependency)):
    async with get_session() as session:
        user = await _get_user(session, telegram_user)
        result = await session.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.user_id == user.id)
            .order_by(Order.created_at.desc())
        )
        orders = result.scalars().all()
        return [{
            "id": order.id,
            "status": order.status.value,
            "created_at": order.created_at.isoformat(),
            "total": float(order.total_price),
            "city": order.city,
            "address": order.address,
            "comment": order.comment,
            "items": [{
                "name": item.product_name,
                "quantity": item.quantity,
                "price": float(item.price_per_unit),
            } for item in order.items],
        } for order in orders]


@app.post("/api/orders")
async def create_order(request: Request, telegram_user: dict = Depends(_telegram_user_dependency)):
    try:
        data = await request.json()
        city, address, phone = (str(data.get(key, "")).strip() for key in ("city", "address", "phone"))
        comment = str(data.get("comment", "")).strip()
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Некорректные данные заказа.")
    if not city or not address or not phone or len(city) > 255 or len(address) > 2000 or len(comment) > 2000 or len(phone) > 32:
        raise HTTPException(status_code=400, detail="Заполните город, адрес и телефон.")
    notification_items = []
    async with get_session() as session:
        user = await _get_user(session, telegram_user)
        result = await session.execute(
            select(Cart).options(selectinload(Cart.product)).where(Cart.user_id == user.id)
        )
        items = result.scalars().all()
        if not items or any(not item.product or not item.product.is_active for item in items):
            raise HTTPException(status_code=400, detail="Корзина пуста или содержит недоступный товар.")
        user.phone = phone
        total = sum(item.product.price * item.quantity for item in items)
        order = Order(user_id=user.id, total_price=total, delivery_type="delivery_kz",
                      city=city, address=address, comment=comment, status=OrderStatus.new)
        session.add(order)
        await session.flush()
        for item in items:
            notification_items.append({
                "name": item.product.name,
                "price": item.product.price,
                "quantity": item.quantity,
            })
            session.add(OrderItem(order_id=order.id, product_id=item.product_id,
                                  product_name=item.product.name, quantity=item.quantity,
                                  price_per_unit=item.product.price))
            await session.delete(item)
        order_id = order.id
        notification_order = SimpleNamespace(
            id=order.id,
            total_price=order.total_price,
            city=order.city,
            address=order.address,
            comment=order.comment,
            created_at=order.created_at,
            status=order.status,
        )
        notification_user = SimpleNamespace(
            username=user.username,
            full_name=user.full_name,
            phone=user.phone,
        )

    from app.services.notifications import notify_admin_new_order

    await notify_admin_new_order(bot, notification_order, notification_user, notification_items)
    return {"ok": True, "order_id": order_id}


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    if not settings.WEBHOOK_SECRET or not hmac.compare_digest(
        request.headers.get("X-Telegram-Bot-Api-Secret-Token", ""),
        settings.WEBHOOK_SECRET,
    ):
        raise HTTPException(status_code=403, detail="Invalid webhook secret.")
    try:
        update = Update.model_validate(await request.json(), context={"bot": bot})
        await _get_dispatcher().feed_update(bot, update)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid Telegram update.")
    return {"ok": True}


@app.get("/health")
async def health():
    return {"status": "ok"}
