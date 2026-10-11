# Apivita Telegram Bot

Бот для оформления заказов мёда и продуктов пчеловодства **АпивитА**.

## Стек технологий

- **Python 3.11+**
- **Aiogram 3.x** — асинхронный Telegram Bot API фреймворк
- **PostgreSQL** — база данных
- **SQLAlchemy (asyncpg)** — ORM
- **Alembic** — миграции БД
- **Loguru** — логирование

## Структура проекта

```
apivita_bot/
├── main.py                    # Точка входа
├── .env                       # Переменные окружения (не коммитить!)
├── .env.example               # Пример конфигурации
├── requirements.txt           # Зависимости
├── app/
│   ├── config.py              # Настройки из .env
│   ├── database/
│   │   ├── models.py          # SQLAlchemy модели
│   │   ├── connection.py      # Подключение к БД
│   │   └── repositories.py   # Репозитории данных
│   ├── handlers/
│   │   ├── start.py           # /start, регистрация
│   │   ├── catalog.py         # Каталог товаров
│   │   ├── cart.py            # Корзина и оформление заказа
│   │   ├── orders.py          # История заказов
│   │   ├── info.py            # О нас, доставка
│   │   └── admin.py           # Панель администратора
│   ├── keyboards/
│   │   ├── reply.py           # Reply-клавиатуры
│   │   └── inline.py          # Inline-клавиатуры
│   ├── middlewares/
│   │   └── auth.py            # Авторизация, логирование, антиспам
│   ├── services/
│   │   ├── analytics.py       # Аналитика
│   │   └── notifications.py   # Уведомления
│   └── utils/
│       └── formatters.py      # Форматирование текста
├── locales/
│   └── ru/
│       └── messages.py        # Все тексты на русском
├── migrations/
│   └── init.sql               # SQL-схема и начальные данные
└── assets/                    # Медиа-файлы (логотип и т.д.)
```

## Установка и запуск

### 1. Клонирование и установка зависимостей

```bash
git clone <repo>
cd apivita_bot
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
```

### 2. Настройка переменных окружения

```bash
copy .env.example .env
```

Отредактируйте `.env`:

```env
BOT_TOKEN=ваш_токен_от_BotFather
ADMIN_IDS=ваш_telegram_id
DB_HOST=localhost
DB_PORT=5432
DB_NAME=apivita_db
DB_USER=apivita_user
DB_PASSWORD=ваш_пароль
```

### 3. Настройка PostgreSQL

```sql
-- Подключиться к psql как postgres
CREATE DATABASE apivita_db;
CREATE USER apivita_user WITH PASSWORD 'ваш_пароль';
GRANT ALL PRIVILEGES ON DATABASE apivita_db TO apivita_user;
```

Применить схему:

```bash
psql -U apivita_user -d apivita_db -f migrations/init.sql
```

### 4. Запуск бота

```bash
python main.py
```

## Регистрация бота через BotFather

1. Откройте [@BotFather](https://t.me/BotFather)
2. Отправьте `/newbot`
3. Введите **название**: `АпивитА — Натуральный мёд`
4. Введите **username**: `apivita_order_bot` (или другой свободный)
5. Сохраните полученный **токен** в `.env`

### Настройка описания бота:
```
/setdescription → АпивитА — натуральный казахстанский мёд и продукты пчеловодства. 
Оформляйте заказы прямо в боте! 🍯 Бесплатная доставка по всему Казахстану при заказе от 5кг.

/setabouttext → 🍯 Магазин натурального мёда АпивитА. Мёд в пластике и стекле, перга, пыльца, прополис, сотовый мёд.

/setuserpic → загрузите логотип АпивитА
```

## Функционал бота

### Для пользователей:
- 📱 **Авторизация** через кнопку "Поделиться" (номер телефона)
- 🛍 **Каталог** с разделами: Мёд в пластике, Мёд в стекле, Другие продукты
- 🛒 **Корзина** с редактированием и подсчётом итога
- 📦 **История заказов** со статусами
- 🚚 **Оформление заказа**: город → адрес → комментарий → подтверждение
- ℹ️ **О нас** и информация о доставке

### Для администраторов (`/admin`):
- 📦 Просмотр всех заказов
- 🔄 Изменение статусов заказов
- 📣 Рассылки (текст/фото/видео) с подтверждением
- 📊 Статистика (пользователи, заказы, выручка)

## Статусы заказов

| Статус | Emoji | Описание |
|--------|-------|----------|
| `new` | 🔵 | Новый заказ |
| `confirmed` | 🟡 | Подтверждён |
| `paid` | 🟢 | Оплачен |
| `shipped` | 🚚 | Отправлен |
| `delivered` | ✅ | Доставлен |
| `cancelled` | ❌ | Отменён |

## Мультиязычность

Все тексты вынесены в `locales/ru/messages.py`. Для добавления нового языка:
1. Создайте `locales/kz/messages.py` с переводами
2. Передайте `lang=user.lang` в функции клавиатур и сообщений

