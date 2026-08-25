import os
import asyncio
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


# ============================================================
# НАСТРОЙКИ
# ============================================================

TOKEN = os.getenv("BOT_TOKEN") 

# Username администратора БЕЗ @
ADMIN_USERNAME = "malleodaass"


# ============================================================
# БАЗА ДАННЫХ
# ============================================================

DB_NAME = "market.db"

db = sqlite3.connect(DB_NAME)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    coins INTEGER DEFAULT 0,
    created_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS promo_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    coins INTEGER NOT NULL,
    max_uses INTEGER NOT NULL,
    uses INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1,
    created_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS promo_uses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    promo_id INTEGER NOT NULL,
    telegram_id INTEGER NOT NULL,
    used_at TEXT,
    UNIQUE(promo_id, telegram_id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price INTEGER NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    active INTEGER DEFAULT 1,
    created_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    price INTEGER NOT NULL,
    status TEXT DEFAULT 'Оплачен',
    created_at TEXT
)
""")

db.commit()


# ============================================================
# BOT
# ============================================================

bot = Bot(token=TOKEN)
dp = Dispatcher()


# ============================================================
# СОСТОЯНИЯ
# ============================================================

class PromoStates(StatesGroup):
    waiting_code = State()


class GiveCoinsStates(StatesGroup):
    waiting_username = State()
    waiting_amount = State()


class TakeCoinsStates(StatesGroup):
    waiting_username = State()
    waiting_amount = State()


class CreatePromoStates(StatesGroup):
    waiting_code = State()
    waiting_coins = State()
    waiting_uses = State()


class CreateProductStates(StatesGroup):
    waiting_name = State()
    waiting_price = State()
    waiting_category = State()
    waiting_description = State()


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def is_admin(user) -> bool:
    if not user.username:
        return False

    return user.username.lower() == ADMIN_USERNAME.lower()


def register_user(user):
    username = user.username or ""
    first_name = user.first_name or ""
    now = datetime.now().isoformat()

    cursor.execute(
        """
        INSERT INTO users (
            telegram_id,
            username,
            first_name,
            coins,
            created_at
        )
        VALUES (?, ?, ?, 0, ?)
        ON CONFLICT(telegram_id)
        DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name
        """,
        (
            user.id,
            username,
            first_name,
            now,
        ),
    )

    db.commit()


def get_balance(telegram_id: int) -> int:
    cursor.execute(
        "SELECT coins FROM users WHERE telegram_id = ?",
        (telegram_id,),
    )

    result = cursor.fetchone()

    if result:
        return result[0]

    return 0


def get_user_by_username(username: str):
    username = username.replace("@", "").strip().lower()

    cursor.execute(
        """
        SELECT telegram_id, username, first_name, coins
        FROM users
        WHERE LOWER(username) = ?
        """,
        (username,),
    )

    return cursor.fetchone()


def add_coins(telegram_id: int, amount: int):
    cursor.execute(
        """
        UPDATE users
        SET coins = coins + ?
        WHERE telegram_id = ?
        """,
        (amount, telegram_id),
    )

    db.commit()


def remove_coins(telegram_id: int, amount: int):
    cursor.execute(
        """
        UPDATE users
        SET coins = coins - ?
        WHERE telegram_id = ?
        AND coins >= ?
        """,
        (amount, telegram_id, amount),
    )

    db.commit()

    return cursor.rowcount > 0


def get_category_name(category: str) -> str:

    categories = {
        "seeds": "🌱 Семена",
        "pets": "🐾 Питомцы",
        "sets": "🎁 Наборы",
        "rare": "⭐ Редкие предметы",
    }

    return categories.get(category, category)




# ============================================================
# ГЛАВНОЕ МЕНЮ
# ============================================================

from aiogram import types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# ============================================================
# ГЛАВНОЕ МЕНЮ
# ============================================================

def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 malleodas_market",
                    callback_data="catalog"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💰 Balance",
                    callback_data="profile"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🛠 Тех поддержка",
                    callback_data="support"
                )
            ],
        ]
    )


# ============================================================
# КОМАНДА /START
# ============================================================

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать в malleodas_market!",
        reply_markup=main_menu()
    )

# ============================================================
# ПРОФИЛЬ
# ============================================================

def profile_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎟️ Ввести промокод",
                    callback_data="promo"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="back"
                )
            ],
        ]
    )


# ============================================================
# КАТАЛОГ
# ============================================================

def catalog_menu():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌱 Семена",
                    callback_data="seeds"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🐾 Питомцы",
                    callback_data="pets"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎁 Наборы",
                    callback_data="sets"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ Редкие предметы",
                    callback_data="rare"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="back"
                )
            ],
        ]
    )


# ============================================================
# КНОПКА ОТМЕНЫ
# ============================================================

def cancel_menu():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="cancel"
                )
            ]
        ]
    )


# ============================================================
# АДМИН-ПАНЕЛЬ
# ============================================================

def admin_menu():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🪙 Выдать коины",
                    callback_data="admin_give"
                )
            ],
            [
                InlineKeyboardButton(
                    text="➖ Забрать коины",
                    callback_data="admin_take"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎟️ Создать промокод",
                    callback_data="admin_create_promo"
                )
            ],
            [
                InlineKeyboardButton(
                    text="➕ Добавить товар",
                    callback_data="admin_add_product"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑️ Удалить товар",
                    callback_data="admin_delete_product"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Статистика",
                    callback_data="admin_stats"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="back"
                )
            ],
        ]
    )


# ============================================================
# START
# ============================================================

@dp.message(CommandStart())
async def start(message: Message):

    register_user(message.from_user)

    await message.answer(
        "🌱 <b>MALLEODAS MARKET</b>\n\n"
        "Добро пожаловать в магазин!\n\n"
        "Здесь ты можешь приобрести товары "
        "для Grow a Garden 2.",
        reply_markup=main_menu(),
        parse_mode="HTML",
    )


# ============================================================
# ПРОФИЛЬ
# ============================================================

@dp.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):

    register_user(callback.from_user)

    username = callback.from_user.username

    if username:
        display_username = f"@{username}"
    else:
        display_username = callback.from_user.first_name

    balance = get_balance(callback.from_user.id)

    await callback.message.edit_text(
        "👤 <b>ПРОФИЛЬ</b>\n\n"
        f"👨‍💻 Пользователь: {display_username}\n"
        f"🪙 Баланс: <b>{balance}</b> коинов",
        reply_markup=profile_menu(),
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# ПРОМОКОД — НАЧАЛО
# ============================================================

@dp.callback_query(F.data == "promo")
async def promo_start(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.set_state(
        PromoStates.waiting_code
    )

    await callback.message.edit_text(
        "🎟️ <b>АКТИВАЦИЯ ПРОМОКОДА</b>\n\n"
        "Отправь мне промокод одним сообщением.\n\n"
        "Например:\n"
        "<code>GARDEN500</code>",
        reply_markup=cancel_menu(),
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# ПРОМОКОД — АКТИВАЦИЯ
# ============================================================

@dp.message(PromoStates.waiting_code)
async def promo_activate(
    message: Message,
    state: FSMContext
):

    register_user(message.from_user)

    if not message.text:
        await message.answer(
            "❌ Отправь промокод текстом.",
            reply_markup=cancel_menu()
        )
        return

    code = message.text.strip().upper()

    cursor.execute(
        """
        SELECT id, coins, max_uses, uses, active
        FROM promo_codes
        WHERE code = ?
        """,
        (code,),
    )

    promo = cursor.fetchone()

    if not promo:
        await message.answer(
            "❌ Такой промокод не найден.",
            reply_markup=cancel_menu()
        )
        return

    promo_id, coins, max_uses, uses, active = promo

    if not active:
        await message.answer(
            "❌ Этот промокод отключён.",
            reply_markup=cancel_menu()
        )
        return

    if uses >= max_uses:
        await message.answer(
            "❌ Лимит активаций этого промокода закончился.",
            reply_markup=cancel_menu()
        )
        return

    cursor.execute(
        """
        SELECT id
        FROM promo_uses
        WHERE promo_id = ?
        AND telegram_id = ?
        """,
        (
            promo_id,
            message.from_user.id,
        ),
    )

    if cursor.fetchone():
        await message.answer(
            "❌ Ты уже использовал этот промокод.",
            reply_markup=cancel_menu()
        )
        return

    add_coins(
        message.from_user.id,
        coins
    )

    cursor.execute(
        """
        INSERT INTO promo_uses (
            promo_id,
            telegram_id,
            used_at
        )
        VALUES (?, ?, ?)
        """,
        (
            promo_id,
            message.from_user.id,
            datetime.now().isoformat(),
        ),
    )

    cursor.execute(
        """
        UPDATE promo_codes
        SET uses = uses + 1
        WHERE id = ?
        """,
        (promo_id,),
    )

    db.commit()

    new_balance = get_balance(
        message.from_user.id
    )

    await message.answer(
        "🎉 <b>ПРОМОКОД АКТИВИРОВАН!</b>\n\n"
        f"🎟️ Код: <code>{code}</code>\n"
        f"🪙 Получено: <b>{coins}</b> коинов\n"
        f"💰 Новый баланс: <b>{new_balance}</b> коинов",
        parse_mode="HTML",
        reply_markup=profile_menu(),
    )

    await state.clear()


# ============================================================
# КАТАЛОГ
# ============================================================

@dp.callback_query(F.data == "catalog")
async def catalog(callback: CallbackQuery):

    await callback.message.edit_text(
        "🛍️ <b>КАТАЛОГ</b>\n\n"
        "Выбери категорию:",
        reply_markup=catalog_menu(),
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# ПОКАЗ ТОВАРОВ КАТЕГОРИИ
# ============================================================

@dp.callback_query(
    F.data.in_({
        "seeds",
        "pets",
        "sets",
        "rare",
    })
)
async def category(callback: CallbackQuery):

    category = callback.data
    category_name = get_category_name(category)

    cursor.execute(
        """
        SELECT id, name, price, description
        FROM products
        WHERE category = ?
        AND active = 1
        ORDER BY id DESC
        """,
        (category,),
    )

    products = cursor.fetchall()

    if not products:

        await callback.message.edit_text(
            f"<b>{category_name}</b>\n\n"
            "🚧 В этой категории пока нет товаров.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="⬅️ Назад в каталог",
                            callback_data="catalog"
                        )
                    ]
                ]
            ),
            parse_mode="HTML",
        )

        await callback.answer()
        return

    text = f"<b>{category_name}</b>\n\n"

    buttons = []

    for product_id, name, price, description in products:

        text += (
            f"📦 <b>{name}</b>\n"
            f"🪙 Цена: <b>{price}</b> коинов\n"
        )

        if description:
            text += f"📝 {description}\n"

        text += "\n"

        buttons.append([
            InlineKeyboardButton(
                text=f"🛒 Купить — {name}",
                callback_data=f"buy_{product_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Назад в каталог",
            callback_data="catalog"
        )
    ])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        ),
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# ПРОСМОТР ТОВАРА
# ============================================================

@dp.callback_query(F.data.startswith("buy_"))
async def buy_product(callback: CallbackQuery):

    register_user(callback.from_user)

    try:
        product_id = int(
            callback.data.replace("buy_", "")
        )
    except ValueError:
        await callback.answer(
            "Ошибка товара",
            show_alert=True
        )
        return

    cursor.execute(
        """
        SELECT id, name, price, category, description
        FROM products
        WHERE id = ?
        AND active = 1
        """,
        (product_id,),
    )

    product = cursor.fetchone()

    if not product:

        await callback.answer(
            "❌ Товар больше недоступен.",
            show_alert=True
        )

        return

    product_id, name, price, category, description = product

    balance = get_balance(
        callback.from_user.id
    )

    text = (
        f"📦 <b>{name}</b>\n\n"
        f"🪙 Цена: <b>{price}</b> коинов\n"
        f"💰 Твой баланс: <b>{balance}</b> коинов\n\n"
    )

    if description:
        text += f"📝 {description}\n\n"

    if balance < price:
        text += "❌ Недостаточно коинов."

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад",
                        callback_data=category
                    )
                ]
            ]
        )

    else:

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Купить",
                        callback_data=f"confirm_buy_{product_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад",
                        callback_data=category
                    )
                ]
            ]
        )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# ПОДТВЕРЖДЕНИЕ ПОКУПКИ
# ============================================================

@dp.callback_query(F.data.startswith("confirm_buy_"))
async def confirm_buy(callback: CallbackQuery):

    register_user(callback.from_user)

    try:
        product_id = int(
            callback.data.replace("confirm_buy_", "")
        )
    except ValueError:
        await callback.answer(
            "Ошибка товара",
            show_alert=True
        )
        return

    cursor.execute(
        """
        SELECT id, name, price, category, description
        FROM products
        WHERE id = ?
        AND active = 1
        """,
        (product_id,),
    )

    product = cursor.fetchone()

    if not product:

        await callback.answer(
            "❌ Товар больше недоступен.",
            show_alert=True
        )

        return

    product_id, name, price, category, description = product

    balance = get_balance(
        callback.from_user.id
    )

    if balance < price:

        await callback.answer(
            "❌ Недостаточно коинов.",
            show_alert=True
        )

        return

    success = remove_coins(
        callback.from_user.id,
        price
    )

    if not success:

        await callback.answer(
            "❌ Не удалось провести оплату.",
            show_alert=True
        )

        return

    cursor.execute(
        """
        INSERT INTO orders (
            telegram_id,
            product_id,
            product_name,
            price,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            callback.from_user.id,
            product_id,
            name,
            price,
            "Оплачен",
            datetime.now().isoformat(),
        ),
    )

    db.commit()

    order_id = cursor.lastrowid

    new_balance = get_balance(
        callback.from_user.id
    )

    await callback.message.edit_text(
        "🎉 <b>ПОКУПКА УСПЕШНА!</b>\n\n"
        f"📦 Товар: <b>{name}</b>\n"
        f"🪙 Цена: <b>{price}</b> коинов\n"
        f"🧾 Номер заказа: <code>#{order_id}</code>\n"
        f"💰 Остаток: <b>{new_balance}</b> коинов\n\n"
        "✅ Заказ сохранён в разделе «Мои заказы».",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📦 Мои заказы",
                        callback_data="orders"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🛍️ Каталог",
                        callback_data="catalog"
                    )
                ]
            ]
        ),
        parse_mode="HTML",
    )

    await callback.answer(
        "Покупка совершена!"
    )


# ============================================================
# МОИ ЗАКАЗЫ
# ============================================================

@dp.callback_query(F.data == "orders")
async def orders(callback: CallbackQuery):

    register_user(callback.from_user)

    cursor.execute(
        """
        SELECT id, product_name, price, status, created_at
        FROM orders
        WHERE telegram_id = ?
        ORDER BY id DESC
        """,
        (callback.from_user.id,),
    )

    orders_list = cursor.fetchall()

    if not orders_list:

        await callback.message.edit_text(
            "📦 <b>МОИ ЗАКАЗЫ</b>\n\n"
            "У тебя пока нет заказов.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="⬅️ Назад",
                            callback_data="back"
                        )
                    ]
                ]
            ),
            parse_mode="HTML",
        )

        await callback.answer()
        return

    text = "📦 <b>МОИ ЗАКАЗЫ</b>\n\n"

    for order_id, product_name, price, status, created_at in orders_list:

        try:
            date = datetime.fromisoformat(
                created_at
            ).strftime("%d.%m.%Y %H:%M")
        except Exception:
            date = created_at

        text += (
            f"🧾 <b>Заказ #{order_id}</b>\n"
            f"📦 {product_name}\n"
            f"🪙 {price} коинов\n"
            f"📌 Статус: <b>{status}</b>\n"
            f"🕐 {date}\n\n"
        )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🛍️ Каталог",
                        callback_data="catalog"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад",
                        callback_data="back"
                    )
                ]
            ]
        ),
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# ПОДДЕРЖКА
# ============================================================

@dp.callback_query(F.data == "support")
async def support(callback: CallbackQuery):

    await callback.message.edit_text(
        "💬 <b>ПОДДЕРЖКА</b>\n\n"
        "Если у тебя возникли вопросы, "
        "обратись к администратору.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад",
                        callback_data="back"
                    )
                ]
            ]
        ),
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# НАЗАД
# ============================================================

@dp.callback_query(F.data == "back")
async def back(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.clear()

    await callback.message.edit_text(
        "🌱 <b>MALLEODAS MARKET</b>\n\n"
        "Выбери нужный раздел:",
        reply_markup=main_menu(),
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# ОТМЕНА
# ============================================================

@dp.callback_query(F.data == "cancel")
async def cancel_action(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.clear()

    try:
        await callback.message.delete()
    except Exception:
        pass

    if is_admin(callback.from_user):

        await callback.message.answer(
            "🔐 <b>АДМИН-ПАНЕЛЬ</b>\n\n"
            "Выбери действие:",
            reply_markup=admin_menu(),
            parse_mode="HTML",
        )

    else:

        await callback.message.answer(
            "🌱 <b>MALLEODAS MARKET</b>\n\n"
            "Выбери нужный раздел:",
            reply_markup=main_menu(),
            parse_mode="HTML",
        )

    await callback.answer()


# ============================================================
# АДМИН-КОМАНДА
# ============================================================

@dp.message(F.text == "/admin")
async def admin_command(message: Message):

    register_user(message.from_user)

    if not is_admin(message.from_user):

        await message.answer(
            "❌ У тебя нет доступа к админ-панели."
        )

        return

    await message.answer(
        "🔐 <b>АДМИН-ПАНЕЛЬ</b>\n\n"
        "Выбери действие:",
        reply_markup=admin_menu(),
        parse_mode="HTML",
    )


# ============================================================
# ВЫДАТЬ КОИНЫ
# ============================================================

@dp.callback_query(F.data == "admin_give")
async def admin_give_start(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(callback.from_user):

        await callback.answer(
            "Нет доступа",
            show_alert=True
        )

        return

    await state.set_state(
        GiveCoinsStates.waiting_username
    )

    await callback.message.edit_text(
        "🪙 <b>ВЫДАТЬ КОИНЫ</b>\n\n"
        "Отправь username пользователя.\n\n"
        "Например:\n"
        "<code>@malleodas</code>",
        reply_markup=cancel_menu(),
        parse_mode="HTML",
    )

    await callback.answer()


@dp.message(GiveCoinsStates.waiting_username)
async def admin_give_username(
    message: Message,
    state: FSMContext
):

    if not message.text:

        await message.answer(
            "❌ Введи username.",
            reply_markup=cancel_menu()
        )

        return

    username = message.text.strip()

    user = get_user_by_username(username)

    if not user:

        await message.answer(
            "❌ Пользователь не найден.\n\n"
            "Пользователь должен хотя бы один раз "
            "запустить бота через /start.",
            reply_markup=cancel_menu(),
        )

        return

    await state.update_data(
        telegram_id=user[0],
        username=user[1],
    )

    await state.set_state(
        GiveCoinsStates.waiting_amount
    )

    await message.answer(
        f"👤 Пользователь: @{user[1]}\n\n"
        "🪙 Сколько коинов выдать?\n\n"
        "Например:\n"
        "<code>500</code>",
        reply_markup=cancel_menu(),
        parse_mode="HTML",
    )


@dp.message(GiveCoinsStates.waiting_amount)
async def admin_give_amount(
    message: Message,
    state: FSMContext
):

    if not message.text:

        await message.answer(
            "❌ Введи целое число.",
            reply_markup=cancel_menu()
        )

        return

    try:
        amount = int(message.text)

    except ValueError:

        await message.answer(
            "❌ Введи целое число.",
            reply_markup=cancel_menu()
        )

        return

    if amount <= 0:

        await message.answer(
            "❌ Количество должно быть больше нуля.",
            reply_markup=cancel_menu()
        )

        return

    data = await state.get_data()

    telegram_id = data["telegram_id"]
    username = data["username"]

    add_coins(
        telegram_id,
        amount
    )

    balance = get_balance(
        telegram_id
    )

    await message.answer(
        "✅ <b>КОИНЫ НАЧИСЛЕНЫ</b>\n\n"
        f"👤 Пользователь: @{username}\n"
        f"🪙 Выдано: <b>{amount}</b>\n"
        f"💰 Новый баланс: <b>{balance}</b>",
        parse_mode="HTML",
        reply_markup=admin_menu(),
    )

    await state.clear()


# ============================================================
# ЗАБРАТЬ КОИНЫ
# ============================================================

@dp.callback_query(F.data == "admin_take")
async def admin_take_start(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(callback.from_user):

        await callback.answer(
            "Нет доступа",
            show_alert=True
        )

        return

    await state.set_state(
        TakeCoinsStates.waiting_username
    )

    await callback.message.edit_text(
        "➖ <b>ЗАБРАТЬ КОИНЫ</b>\n\n"
        "Отправь username пользователя.\n\n"
        "Например:\n"
        "<code>@malleodas</code>",
        reply_markup=cancel_menu(),
        parse_mode="HTML",
    )

    await callback.answer()


@dp.message(TakeCoinsStates.waiting_username)
async def admin_take_username(
    message: Message,
    state: FSMContext
):

    if not message.text:

        await message.answer(
            "❌ Введи username.",
            reply_markup=cancel_menu()
        )

        return

    username = message.text.strip()

    user = get_user_by_username(username)

    if not user:

        await message.answer(
            "❌ Пользователь не найден.",
            reply_markup=cancel_menu()
        )

        return

    await state.update_data(
        telegram_id=user[0],
        username=user[1],
    )

    await state.set_state(
        TakeCoinsStates.waiting_amount
    )

    await message.answer(
        f"👤 Пользователь: @{user[1]}\n\n"
        "🪙 Сколько коинов забрать?",
        reply_markup=cancel_menu(),
        parse_mode="HTML",
    )


@dp.message(TakeCoinsStates.waiting_amount)
async def admin_take_amount(
    message: Message,
    state: FSMContext
):

    if not message.text:

        await message.answer(
            "❌ Введи целое число.",
            reply_markup=cancel_menu()
        )

        return

    try:
        amount = int(message.text)

    except ValueError:

        await message.answer(
            "❌ Введи целое число.",
            reply_markup=cancel_menu()
        )

        return

    if amount <= 0:

        await message.answer(
            "❌ Количество должно быть больше нуля.",
            reply_markup=cancel_menu()
        )

        return

    data = await state.get_data()

    telegram_id = data["telegram_id"]
    username = data["username"]

    success = remove_coins(
        telegram_id,
        amount
    )

    if not success:

        await message.answer(
            "❌ У пользователя недостаточно коинов.",
            reply_markup=cancel_menu()
        )

        return

    balance = get_balance(
        telegram_id
    )

    await message.answer(
        "✅ <b>КОИНЫ СПИСАНЫ</b>\n\n"
        f"👤 Пользователь: @{username}\n"
        f"➖ Списано: <b>{amount}</b>\n"
        f"💰 Новый баланс: <b>{balance}</b>",
        parse_mode="HTML",
        reply_markup=admin_menu(),
    )

    await state.clear()


# ============================================================
# СОЗДАНИЕ ПРОМОКОДА
# ============================================================

@dp.callback_query(F.data == "admin_create_promo")
async def admin_create_promo_start(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(callback.from_user):

        await callback.answer(
            "Нет доступа",
            show_alert=True
        )

        return

    await state.set_state(
        CreatePromoStates.waiting_code
    )

    await callback.message.edit_text(
        "🎟️ <b>СОЗДАНИЕ ПРОМОКОДА</b>\n\n"
        "Придумай код.\n\n"
        "Например:\n"
        "<code>GARDEN500</code>",
        reply_markup=cancel_menu(),
        parse_mode="HTML",
    )

    await callback.answer()


@dp.message(CreatePromoStates.waiting_code)
async def create_promo_code(
    message: Message,
    state: FSMContext
):

    if not message.text:

        await message.answer(
            "❌ Введи код.",
            reply_markup=cancel_menu()
        )

        return

    code = message.text.strip().upper()

    if len(code) < 3:

        await message.answer(
            "❌ Код должен содержать минимум 3 символа.",
            reply_markup=cancel_menu()
        )

        return

    cursor.execute(
        "SELECT id FROM promo_codes WHERE code = ?",
        (code,),
    )

    if cursor.fetchone():

        await message.answer(
            "❌ Такой промокод уже существует.",
            reply_markup=cancel_menu()
        )

        return

    await state.update_data(
        code=code
    )

    await state.set_state(
        CreatePromoStates.waiting_coins
    )

    await message.answer(
        "🪙 Сколько коинов будет давать промокод?\n\n"
        "Например:\n"
        "<code>500</code>",
        reply_markup=cancel_menu(),
        parse_mode="HTML",
    )


@dp.message(CreatePromoStates.waiting_coins)
async def create_promo_coins(
    message: Message,
    state: FSMContext
):

    if not message.text:

        await message.answer(
            "❌ Введи число.",
            reply_markup=cancel_menu()
        )

        return

    try:
        coins = int(message.text)

    except ValueError:

        await message.answer(
            "❌ Введи целое число.",
            reply_markup=cancel_menu()
        )

        return

    if coins <= 0:

        await message.answer(
            "❌ Количество коинов должно быть больше нуля.",
            reply_markup=cancel_menu()
        )

        return

    await state.update_data(
        coins=coins
    )

    await state.set_state(
        CreatePromoStates.waiting_uses
    )

    await message.answer(
        "👥 Сколько раз можно активировать промокод?\n\n"
        "Например:\n"
        "<code>100</code>",
        reply_markup=cancel_menu(),
        parse_mode="HTML",
    )


@dp.message(CreatePromoStates.waiting_uses)
async def create_promo_uses(
    message: Message,
    state: FSMContext
):

    if not message.text:

        await message.answer(
            "❌ Введи число.",
            reply_markup=cancel_menu()
        )

        return

    try:
        max_uses = int(message.text)

    except ValueError:

        await message.answer(
            "❌ Введи целое число.",
            reply_markup=cancel_menu()
        )

        return

    if max_uses <= 0:

        await message.answer(
            "❌ Количество активаций должно быть больше нуля.",
            reply_markup=cancel_menu()
        )

        return

    data = await state.get_data()

    code = data["code"]
    coins = data["coins"]

    cursor.execute(
        """
        INSERT INTO promo_codes (
            code,
            coins,
            max_uses,
            uses,
            active,
            created_at
        )
        VALUES (?, ?, ?, 0, 1, ?)
        """,
        (
            code,
            coins,
            max_uses,
            datetime.now().isoformat(),
        ),
    )

    db.commit()

    await message.answer(
        "🎉 <b>ПРОМОКОД СОЗДАН!</b>\n\n"
        f"🎟️ Код: <code>{code}</code>\n"
        f"🪙 Награда: <b>{coins}</b> коинов\n"
        f"👥 Активаций: <b>{max_uses}</b>",
        parse_mode="HTML",
        reply_markup=admin_menu(),
    )

    await state.clear()


# ============================================================
# ДОБАВЛЕНИЕ ТОВАРА — НАЧАЛО
# ============================================================

@dp.callback_query(F.data == "admin_add_product")
async def admin_add_product_start(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(callback.from_user):

        await callback.answer(
            "Нет доступа",
            show_alert=True
        )

        return

    await state.set_state(
        CreateProductStates.waiting_name
    )

    await callback.message.edit_text(
        "➕ <b>ДОБАВЛЕНИЕ ТОВАРА</b>\n\n"
        "Введи название товара.\n\n"
        "Например:\n"
        "<code>Rainbow Seed</code>",
        reply_markup=cancel_menu(),
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# ДОБАВЛЕНИЕ ТОВАРА — НАЗВАНИЕ
# ============================================================

@dp.message(CreateProductStates.waiting_name)
async def create_product_name(
    message: Message,
    state: FSMContext
):

    if not message.text:

        await message.answer(
            "❌ Введи название товара.",
            reply_markup=cancel_menu()
        )

        return

    name = message.text.strip()

    if len(name) < 1:

        await message.answer(
            "❌ Название не может быть пустым.",
            reply_markup=cancel_menu()
        )

        return

    await state.update_data(
        name=name
    )

    await state.set_state(
        CreateProductStates.waiting_price
    )

    await message.answer(
        "🪙 <b>ЦЕНА ТОВАРА</b>\n\n"
        "Введи цену в коинах.\n\n"
        "Например:\n"
        "<code>500</code>",
        reply_markup=cancel_menu(),
        parse_mode="HTML",
    )


# ============================================================
# ДОБАВЛЕНИЕ ТОВАРА — ЦЕНА
# ============================================================

@dp.message(CreateProductStates.waiting_price)
async def create_product_price(
    message: Message,
    state: FSMContext
):

    if not message.text:

        await message.answer(
            "❌ Введи цену числом.",
            reply_markup=cancel_menu()
        )

        return

    try:
        price = int(message.text)

    except ValueError:

        await message.answer(
            "❌ Цена должна быть целым числом.\n\n"
            "Например: <code>500</code>",
            reply_markup=cancel_menu(),
            parse_mode="HTML",
        )

        return

    if price <= 0:

        await message.answer(
            "❌ Цена должна быть больше нуля.",
            reply_markup=cancel_menu()
        )

        return

    await state.update_data(
        price=price
    )

    await state.set_state(
        CreateProductStates.waiting_category
    )

    await message.answer(
        "📂 <b>КАТЕГОРИЯ</b>\n\n"
        "Выбери категорию товара:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🌱 Семена",
                        callback_data="product_cat_seeds"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🐾 Питомцы",
                        callback_data="product_cat_pets"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🎁 Наборы",
                        callback_data="product_cat_sets"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⭐ Редкие предметы",
                        callback_data="product_cat_rare"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Отмена",
                        callback_data="cancel"
                    )
                ],
            ]
        ),
        parse_mode="HTML",
    )


# ============================================================
# ДОБАВЛЕНИЕ ТОВАРА — КАТЕГОРИЯ
# ============================================================

@dp.callback_query(
    F.data.in_({
        "product_cat_seeds",
        "product_cat_pets",
        "product_cat_sets",
        "product_cat_rare",
    })
)
async def create_product_category(
    callback: CallbackQuery,
    state: FSMContext
):

    categories = {
        "product_cat_seeds": "seeds",
        "product_cat_pets": "pets",
        "product_cat_sets": "sets",
        "product_cat_rare": "rare",
    }

    category = categories[callback.data]

    await state.update_data(
        category=category
    )

    await state.set_state(
        CreateProductStates.waiting_description
    )

    await callback.message.edit_text(
        "📝 <b>ОПИСАНИЕ ТОВАРА</b>\n\n"
        "Напиши описание товара.\n\n"
        "Например:\n"
        "<code>Редкое семя для выращивания растения.</code>",
        reply_markup=cancel_menu(),
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# ДОБАВЛЕНИЕ ТОВАРА — ОПИСАНИЕ
# ============================================================

@dp.message(CreateProductStates.waiting_description)
async def create_product_description(
    message: Message,
    state: FSMContext
):

    if not message.text:

        await message.answer(
            "❌ Введи описание товара.",
            reply_markup=cancel_menu()
        )

        return

    description = message.text.strip()

    data = await state.get_data()

    name = data["name"]
    price = data["price"]
    category = data["category"]

    cursor.execute(
        """
        INSERT INTO products (
            name,
            price,
            category,
            description,
            active,
            created_at
        )
        VALUES (?, ?, ?, ?, 1, ?)
        """,
        (
            name,
            price,
            category,
            description,
            datetime.now().isoformat(),
        ),
    )

    db.commit()

    product_id = cursor.lastrowid

    category_name = get_category_name(category)

    await message.answer(
        "🎉 <b>ТОВАР ДОБАВЛЕН!</b>\n\n"
        f"🆔 ID: <code>{product_id}</code>\n"
        f"📦 Название: <b>{name}</b>\n"
        f"🪙 Цена: <b>{price}</b> коинов\n"
        f"📂 Категория: <b>{category_name}</b>\n"
        f"📝 Описание: {description}",
        reply_markup=admin_menu(),
        parse_mode="HTML",
    )

    await state.clear()


# ============================================================
# УДАЛЕНИЕ ТОВАРА — СПИСОК
# ============================================================

@dp.callback_query(F.data == "admin_delete_product")
async def admin_delete_product(
    callback: CallbackQuery
):

    if not is_admin(callback.from_user):

        await callback.answer(
            "Нет доступа",
            show_alert=True
        )

        return

    cursor.execute(
        """
        SELECT id, name, price
        FROM products
        WHERE active = 1
        ORDER BY id DESC
        """
    )

    products = cursor.fetchall()

    if not products:

        await callback.message.edit_text(
            "🗑️ <b>УДАЛЕНИЕ ТОВАРА</b>\n\n"
            "Активных товаров нет.",
            reply_markup=admin_menu(),
            parse_mode="HTML",
        )

        await callback.answer()
        return

    buttons = []

    for product_id, name, price in products:

        buttons.append([
            InlineKeyboardButton(
                text=f"🗑️ {name} — {price} 🪙",
                callback_data=f"delete_product_{product_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="admin_panel"
        )
    ])

    await callback.message.edit_text(
        "🗑️ <b>УДАЛЕНИЕ ТОВАРА</b>\n\n"
        "Выбери товар, который нужно убрать из каталога:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        ),
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# УДАЛЕНИЕ ТОВАРА
# ============================================================

@dp.callback_query(F.data.startswith("delete_product_"))
async def delete_product(
    callback: CallbackQuery
):

    if not is_admin(callback.from_user):

        await callback.answer(
            "Нет доступа",
            show_alert=True
        )

        return

    try:
        product_id = int(
            callback.data.replace(
                "delete_product_",
                ""
            )
        )
    except ValueError:

        await callback.answer(
            "Ошибка товара",
            show_alert=True
        )

        return

    cursor.execute(
        """
        SELECT name
        FROM products
        WHERE id = ?
        """,
        (product_id,),
    )

    product = cursor.fetchone()

    if not product:

        await callback.answer(
            "Товар не найден.",
            show_alert=True
        )

        return

    product_name = product[0]

    # Не удаляем запись физически.
    # Просто выключаем товар.
    cursor.execute(
        """
        UPDATE products
        SET active = 0
        WHERE id = ?
        """,
        (product_id,),
    )

    db.commit()

    await callback.message.edit_text(
        "🗑️ <b>ТОВАР УДАЛЁН</b>\n\n"
        f"📦 {product_name}\n\n"
        "Товар больше не отображается в каталоге.",
        reply_markup=admin_menu(),
        parse_mode="HTML",
    )

    await callback.answer(
        "Товар удалён"
    )


# ============================================================
# АДМИН-ПАНЕЛЬ ЧЕРЕЗ КНОПКУ
# ============================================================

@dp.callback_query(F.data == "admin_panel")
async def admin_panel_callback(
    callback: CallbackQuery
):

    if not is_admin(callback.from_user):

        await callback.answer(
            "Нет доступа",
            show_alert=True
        )

        return

    await callback.message.edit_text(
        "🔐 <b>АДМИН-ПАНЕЛЬ</b>\n\n"
        "Выбери действие:",
        reply_markup=admin_menu(),
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# СТАТИСТИКА
# ============================================================

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):

    if not is_admin(callback.from_user):

        await callback.answer(
            "Нет доступа",
            show_alert=True
        )

        return

    cursor.execute(
        "SELECT COUNT(*) FROM users"
    )

    users = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COALESCE(SUM(coins), 0) FROM users"
    )

    total_coins = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM promo_codes"
    )

    promos = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM products
        WHERE active = 1
        """
    )

    products = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM orders"
    )

    orders_count = cursor.fetchone()[0]

    await callback.message.edit_text(
        "📊 <b>СТАТИСТИКА</b>\n\n"
        f"👥 Пользователей: <b>{users}</b>\n"
        f"🪙 Всего коинов: <b>{total_coins}</b>\n"
        f"🎟️ Промокодов: <b>{promos}</b>\n"
        f"📦 Товаров: <b>{products}</b>\n"
        f"🧾 Заказов: <b>{orders_count}</b>",
        reply_markup=admin_menu(),
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# ЗАПУСК
# ============================================================

async def main():

    print("====================================")
    print("🌱 MALLEODAS MARKET")
    print("🤖 Бот запущен!")
    print("====================================")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
