"""Repository layer — thin wrappers around SQLAlchemy async sessions."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Sequence

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import (
    Analytics,
    Cart,
    Order,
    OrderItem,
    OrderStatus,
    Product,
    User,
)


# ---------------------------------------------------------------------------
# UserRepository
# ---------------------------------------------------------------------------

class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create(
        self,
        telegram_id: int,
        username: str | None = None,
        full_name: str | None = None,
        lang: str = "ru",
    ) -> tuple[User, bool]:
        """Return (user, created). If the user didn't exist it is added to the session."""
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is not None:
            # Update mutable fields on every call
            user.username = username
            user.full_name = full_name
            return user, False

        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            lang=lang,
        )
        self.session.add(user)
        await self.session.flush()
        return user, True

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def update_phone(self, telegram_id_or_user_id: int, phone: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id_or_user_id)
        )
        user = result.scalar_one_or_none()
        if user is None and -2147483648 <= telegram_id_or_user_id <= 2147483647:
            result = await self.session.execute(
                select(User).where(User.id == telegram_id_or_user_id)
            )
            user = result.scalar_one_or_none()
        if user:
            user.phone = phone
            await self.session.flush()
        return user

    async def get_all(self) -> Sequence[User]:
        result = await self.session.execute(select(User).order_by(User.created_at.desc()))
        return result.scalars().all()

    async def get_all_active(self) -> Sequence[User]:
        result = await self.session.execute(
            select(User).where(User.is_blocked == False).order_by(User.created_at.desc())
        )
        return result.scalars().all()

    async def mark_blocked(self, telegram_id: int, blocked: bool = True) -> None:
        await self.session.execute(
            update(User).where(User.telegram_id == telegram_id).values(is_blocked=blocked)
        )

    async def block(self, telegram_id: int, blocked: bool = True) -> None:
        await self.mark_blocked(telegram_id, blocked)

    async def count_all(self) -> int:
        result = await self.session.execute(select(func.count(User.id)))
        return result.scalar() or 0

    async def count_registered(self) -> int:
        result = await self.session.execute(
            select(func.count(User.id)).where(User.phone.is_not(None))
        )
        return result.scalar() or 0

    async def count_blocked(self) -> int:
        result = await self.session.execute(
            select(func.count(User.id)).where(User.is_blocked == True)
        )
        return result.scalar() or 0


# ---------------------------------------------------------------------------
# ProductRepository
# ---------------------------------------------------------------------------

class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_all_active(self) -> Sequence[Product]:
        result = await self.session.execute(
            select(Product).where(Product.is_active == True).order_by(Product.category, Product.name)
        )
        return result.scalars().all()

    async def get_by_category(self, category: str) -> Sequence[Product]:
        result = await self.session.execute(
            select(Product)
            .where(Product.is_active == True, Product.category == category)
            .order_by(Product.name)
        )
        return result.scalars().all()

    async def get_by_id(self, product_id: int) -> Product | None:
        result = await self.session.execute(
            select(Product).where(Product.id == product_id)
        )
        return result.scalar_one_or_none()

    async def get_by_container_type(self, container_type: str) -> Sequence[Product]:
        result = await self.session.execute(
            select(Product)
            .where(Product.is_active == True, Product.container_type == container_type)
            .order_by(Product.name)
        )
        return result.scalars().all()

    async def get_distinct_categories(self) -> Sequence[str]:
        result = await self.session.execute(
            select(Product.category)
            .where(Product.is_active == True)
            .distinct()
            .order_by(Product.category)
        )
        return result.scalars().all()


async def _resolve_user_id(session: AsyncSession, telegram_or_user_id: int | None) -> int | None:
    if telegram_or_user_id is None:
        return None
    # Look up by telegram_id (BigInteger, standard case)
    result = await session.execute(
        select(User.id).where(User.telegram_id == telegram_or_user_id)
    )
    uid = result.scalar_one_or_none()
    if uid is not None:
        return uid

    # If fits in 32-bit integer, look up by internal primary key User.id
    if -2147483648 <= telegram_or_user_id <= 2147483647:
        result = await session.execute(
            select(User.id).where(User.id == telegram_or_user_id)
        )
        uid = result.scalar_one_or_none()
        if uid is not None:
            return uid

    return telegram_or_user_id


# ---------------------------------------------------------------------------
# CartRepository
# ---------------------------------------------------------------------------

class CartRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _resolve_internal_user_id(self, telegram_or_user_id: int) -> int:
        uid = await _resolve_user_id(self.session, telegram_or_user_id)
        return uid if uid is not None else telegram_or_user_id

    async def _resolve_product_id(self, product_id: int | str, name: str | None = None, price: int | float | None = None) -> int:
        if isinstance(product_id, int):
            return product_id
        # Look up by product code or name
        result = await self.session.execute(
            select(Product.id).where(Product.name == (name or product_id))
        )
        pid = result.scalar_one_or_none()
        if pid is not None:
            return pid
        # Create product on the fly if needed
        p = Product(
            name=name or str(product_id),
            category="honey",
            container_type="plastic",
            price=price or 0,
            is_active=True,
        )
        self.session.add(p)
        await self.session.flush()
        return p.id

    async def add_item(
        self,
        user_id: int,
        product_id: int | str,
        quantity: int = 1,
        price: int | float | None = None,
        name: str | None = None,
        weight: str | None = None,
    ) -> Cart:
        uid = await self._resolve_internal_user_id(user_id)
        pid = await self._resolve_product_id(product_id, name=name, price=price)

        result = await self.session.execute(
            select(Cart).where(Cart.user_id == uid, Cart.product_id == pid)
        )
        cart_item = result.scalar_one_or_none()
        if cart_item:
            cart_item.quantity += quantity
        else:
            cart_item = Cart(user_id=uid, product_id=pid, quantity=quantity)
            self.session.add(cart_item)
        await self.session.flush()
        return cart_item

    async def remove_item(self, user_id: int, product_id: int | str) -> None:
        uid = await self._resolve_internal_user_id(user_id)
        if isinstance(product_id, str):
            result = await self.session.execute(select(Product.id).where(Product.name == product_id))
            p_id = result.scalar_one_or_none()
        else:
            p_id = product_id

        if p_id:
            await self.session.execute(
                delete(Cart).where(Cart.user_id == uid, Cart.product_id == p_id)
            )

    async def clear_cart(self, user_id: int) -> None:
        uid = await self._resolve_internal_user_id(user_id)
        await self.session.execute(delete(Cart).where(Cart.user_id == uid))

    async def clear(self, user_id: int) -> None:
        await self.clear_cart(user_id)

    async def get_items(self, user_id: int) -> list[dict]:
        """Returns items in formatted dict format for cart display."""
        uid = await self._resolve_internal_user_id(user_id)
        result = await self.session.execute(
            select(Cart)
            .options(selectinload(Cart.product))
            .where(Cart.user_id == uid)
            .order_by(Cart.created_at)
        )
        records = result.scalars().all()
        items = []
        for r in records:
            p = r.product
            items.append({
                "product_id": p.id if p else r.product_id,
                "name": p.name if p else "Мёд",
                "weight": f"{p.weight_grams}г" if (p and p.weight_grams) else "",
                "price": int(p.price) if p else 0,
                "quantity": r.quantity,
            })
        return items

    async def get_user_cart(self, user_id: int) -> Sequence[Cart]:
        uid = await self._resolve_internal_user_id(user_id)
        result = await self.session.execute(
            select(Cart)
            .options(selectinload(Cart.product))
            .where(Cart.user_id == uid)
            .order_by(Cart.created_at)
        )
        return result.scalars().all()

    async def get_cart_total(self, user_id: int) -> Decimal:
        uid = await self._resolve_internal_user_id(user_id)
        result = await self.session.execute(
            select(func.sum(Product.price * Cart.quantity))
            .join(Product, Cart.product_id == Product.id)
            .where(Cart.user_id == uid)
        )
        total = result.scalar_one_or_none()
        return Decimal(str(total)) if total is not None else Decimal("0")

    async def update_quantity(self, user_id: int, product_id: int | str, quantity: int) -> None:
        if quantity <= 0:
            await self.remove_item(user_id, product_id)
        else:
            uid = await self._resolve_internal_user_id(user_id)
            pid = await self._resolve_product_id(product_id)
            await self.session.execute(
                update(Cart)
                .where(Cart.user_id == uid, Cart.product_id == pid)
                .values(quantity=quantity)
            )


# ---------------------------------------------------------------------------
# OrderRepository
# ---------------------------------------------------------------------------

class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _resolve_internal_user_id(self, telegram_or_user_id: int) -> int:
        uid = await _resolve_user_id(self.session, telegram_or_user_id)
        return uid if uid is not None else telegram_or_user_id

    async def create_order(
        self,
        user_id: int,
        city: str | None = None,
        address: str | None = None,
        comment: str | None = None,
        items: list | None = None,
        total: int | float | Decimal | None = None,
        delivery_type: str | None = "delivery_kz",
        total_price: Decimal | None = None,
        cart_items: Sequence[Cart] | None = None,
    ) -> int:
        """Create order supporting both dict items and Cart model objects."""
        uid = await self._resolve_internal_user_id(user_id)
        final_total = Decimal(str(total if total is not None else (total_price or 0)))

        order = Order(
            user_id=uid,
            total_price=final_total,
            delivery_type=delivery_type,
            address=address,
            city=city,
            comment=comment,
            status=OrderStatus.new,
        )
        self.session.add(order)
        await self.session.flush()

        if items:
            for item in items:
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=item.get("product_id") if isinstance(item.get("product_id"), int) else None,
                    product_name=item.get("name", "Товар"),
                    quantity=item.get("quantity", 1),
                    price_per_unit=Decimal(str(item.get("price", 0))),
                )
                self.session.add(order_item)
        elif cart_items:
            for c_item in cart_items:
                product = c_item.product
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id if product else None,
                    product_name=product.name if product else "Товар",
                    quantity=c_item.quantity,
                    price_per_unit=product.price if product else Decimal("0"),
                )
                self.session.add(order_item)

        await self.session.flush()
        return order.id

    async def get_user_orders(self, user_id: int) -> list[dict]:
        uid = await self._resolve_internal_user_id(user_id)
        result = await self.session.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.user_id == uid)
            .order_by(Order.created_at.desc())
        )
        orders = result.scalars().all()
        res = []
        for o in orders:
            res.append({
                "id": o.id,
                "status": o.status.value if hasattr(o.status, "value") else str(o.status),
                "created_at": o.created_at,
                "total": int(o.total_price),
                "city": o.city,
                "address": o.address,
                "comment": o.comment,
            })
        return res

    async def get_order_detail(self, order_id: int, user_id: int | None = None) -> dict | None:
        stmt = (
            select(Order)
            .options(selectinload(Order.items), selectinload(Order.user))
            .where(Order.id == order_id)
        )
        if user_id is not None:
            uid = await self._resolve_internal_user_id(user_id)
            stmt = stmt.where(Order.user_id == uid)

        result = await self.session.execute(stmt)
        order = result.scalar_one_or_none()
        if not order:
            return None

        items = []
        for i in order.items:
            items.append({
                "name": i.product_name,
                "product_name": i.product_name,
                "quantity": i.quantity,
                "price": int(i.price_per_unit),
                "price_per_unit": int(i.price_per_unit),
                "subtotal": int(i.price_per_unit * i.quantity),
            })

        user_name = order.user.full_name if order.user else "Клиент с сайта"
        user_phone = order.user.phone if order.user else (order.guest_phone or "")
        user_username = order.user.username if order.user else ""
        user_tg_id = order.user.telegram_id if order.user else None

        return {
            "id": order.id,
            "user_id": order.user_id,
            "telegram_id": user_tg_id,
            "user_name": user_name,
            "user_username": user_username,
            "user_phone": user_phone,
            "status": order.status.value if hasattr(order.status, "value") else str(order.status),
            "created_at": order.created_at,
            "total": int(order.total_price),
            "total_price": int(order.total_price),
            "city": order.city,
            "address": order.address,
            "comment": order.comment,
            "items": items,
        }

    async def get_order_with_items(self, order_id: int):
        """Helper object format with attributes matching admin views."""
        class DotDict:
            def __init__(self, d):
                for k, v in d.items():
                    if k == "items":
                        setattr(self, k, [DotDict(i) for i in v])
                    else:
                        setattr(self, k, v)

        data = await self.get_order_detail(order_id)
        return DotDict(data) if data else None

    async def get_recent_orders(self, limit: int = 20) -> list:
        result = await self.session.execute(
            select(Order)
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        orders = result.scalars().all()
        class AdminOrderBrief:
            def __init__(self, o):
                self.id = o.id
                self.status = o.status.value if hasattr(o.status, "value") else str(o.status)
                self.total_price = int(o.total_price)
                self.created_at = o.created_at
        return [AdminOrderBrief(o) for o in orders]

    async def get_all_orders(
        self, status: OrderStatus | None = None, limit: int = 50, offset: int = 0
    ) -> Sequence[Order]:
        stmt = (
            select(Order)
            .options(selectinload(Order.items), selectinload(Order.user))
            .order_by(Order.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status is not None:
            stmt = stmt.where(Order.status == status)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, order_id: int) -> Order | None:
        result = await self.session.execute(
            select(Order)
            .options(selectinload(Order.items), selectinload(Order.user))
            .where(Order.id == order_id)
        )
        return result.scalar_one_or_none()

    async def update_status(self, order_id: int, status: str | OrderStatus) -> Order | None:
        status_enum = OrderStatus(status) if isinstance(status, str) else status
        await self.session.execute(
            update(Order).where(Order.id == order_id).values(status=status_enum)
        )
        return await self.get_by_id(order_id)


# ---------------------------------------------------------------------------
# AnalyticsRepository
# ---------------------------------------------------------------------------

class AnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _resolve_internal_user_id(self, telegram_or_user_id: int | None) -> int | None:
        return await _resolve_user_id(self.session, telegram_or_user_id)

    async def log_action(
        self,
        user_id: int | None = None,
        action: str = "action",
        data: dict[str, Any] | None = None,
    ) -> Analytics:
        uid = await self._resolve_internal_user_id(user_id)
        record = Analytics(user_id=uid, action=action, data=data)
        self.session.add(record)
        await self.session.flush()
        return record

    async def log_event(
        self,
        user_id: int | None = None,
        event: str = "event",
        payload: dict[str, Any] | None = None,
    ) -> Analytics:
        return await self.log_action(user_id=user_id, action=event, data=payload)
