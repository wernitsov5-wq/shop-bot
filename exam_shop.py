import logging
import sqlite3
from datetime import datetime, timedelta
import uuid

import threading

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)


    
# ================== НАСТРОЙКИ ==================
BOT_TOKEN = "8690771289:AAEKOfGBeICFT1Rfex77-QPpxDijbBOjAms"
MANAGER_ID = 1911945305

CARD_NUMBER = "ошибка"
CARD_HOLDER = "Максим"
BANK_NAME = "Альфа Банк"

PRIVACY_URL = "https://telegra.ph/SOGLASHENIE-05-26-4"
AGREEMENT_URL = "https://telegra.ph/SOGLASHENIE-05-26-4"

DB_NAME = "orders.db"

logging.basicConfig(level=logging.INFO)

# ================== БАЗА ДАННЫХ ==================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        user_id INTEGER,
        product TEXT,
        price INTEGER,
        status TEXT,
        created_at TEXT,
        deadline TEXT,
        consent INTEGER
    )
    """)

    conn.commit()
    conn.close()

# ================== МЕНЮ ==================
def main_menu():
    keyboard = [
        [InlineKeyboardButton("ОТВЕТЫ ОГЭ 2026", callback_data="oge")],
        [InlineKeyboardButton("ОТВЕТЫ НА ВПР", callback_data="vpr")],
        [InlineKeyboardButton("ОТВЕТЫ НА МЦКО", callback_data="mcko")],
        [InlineKeyboardButton("ПРОБНИКИ", callback_data="probnik")],
        [InlineKeyboardButton("Мои покупки", callback_data="my_orders")],
        [InlineKeyboardButton("Помощь", callback_data="help")],
    ]
    return InlineKeyboardMarkup(keyboard)

def back_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ НАЗАД", callback_data="back")]
    ])

# ================== СТАРТ ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
🎓 Добро пожаловать в магазин ответов

📚 Здесь вы можете приобрести:
• ОГЭ 2026  
• ВПР  
• МЦКО  
• Пробники  

⚡ Быстро. Удобно. Без лишних действий.

💳 После оплаты вы получите ответы через менеджера

👇 Выберите нужный раздел:
"""
    await update.message.reply_text(text, reply_markup=main_menu())

# ================== КАТЕГОРИИ ==================
async def oge_menu(update, context):
    keyboard = [
        [InlineKeyboardButton("VIP PREMIUM | 2490₽", callback_data="buy_oge_premium")],
        [InlineKeyboardButton("VIP MEDIUM | 1490₽", callback_data="buy_oge_medium")],
        [InlineKeyboardButton("VIP LITE | 990₽", callback_data="buy_oge_lite")],
        [InlineKeyboardButton("⬅️ НАЗАД", callback_data="back")]
    ]
    await update.callback_query.edit_message_text("Выберите тариф ОГЭ:", reply_markup=InlineKeyboardMarkup(keyboard))

async def vpr_menu(update, context):
    keyboard = [
        [InlineKeyboardButton("VIP ДОСТУП | 1300₽", callback_data="buy_vpr_vip")],
        [InlineKeyboardButton("1 НА ВЫБОР | 500₽", callback_data="buy_vpr_one")],
        [InlineKeyboardButton("⬅️ НАЗАД", callback_data="back")]
    ]
    await update.callback_query.edit_message_text("ВПР:", reply_markup=InlineKeyboardMarkup(keyboard))

async def mcko_menu(update, context):
    keyboard = [
        [InlineKeyboardButton("VIP ДОСТУП | 1300₽", callback_data="buy_mcko_vip")],
        [InlineKeyboardButton("1 НА ВЫБОР | 500₽", callback_data="buy_mcko_one")],
        [InlineKeyboardButton("⬅️ НАЗАД", callback_data="back")]
    ]
    await update.callback_query.edit_message_text("МЦКО:", reply_markup=InlineKeyboardMarkup(keyboard))

async def probnik_menu(update, context):
    keyboard = [
        [InlineKeyboardButton("ПРОБНИКИ | 500₽", callback_data="buy_probnik")],
        [InlineKeyboardButton("⬅️ НАЗАД", callback_data="back")]
    ]
    await update.callback_query.edit_message_text("Пробники:", reply_markup=InlineKeyboardMarkup(keyboard))

# ================== СОЗДАНИЕ ЗАКАЗА ==================
def create_order(user_id, product, price):
    order_id = str(uuid.uuid4())[:8]
    created = datetime.now()
    deadline = created + timedelta(minutes=15)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        order_id,
        user_id,
        product,
        price,
        "pending",
        created.isoformat(),
        deadline.isoformat(),
        0
    ))

    conn.commit()
    conn.close()

    return order_id, deadline

# ================== ОПЛАТА ==================
async def send_payment(update, context, product, price):
    user_id = update.callback_query.from_user.id
    order_id, deadline = create_order(user_id, product, price)
    context.user_data["awaiting_payment"] = order_id

    text = f"""
🧾 Заказ №{order_id}
📦 Товар: {product}
💰 Сумма: {price}₽
⏳ Оплатить до: {deadline.strftime('%H:%M')}

💳 Реквизиты:
Карта: {CARD_NUMBER}
Получатель: {CARD_HOLDER}
Банк: {BANK_NAME}

Нажимая кнопку "✅ Я ОПЛАТИЛ", вы соглашаетесь с политикой:
{PRIVACY_URL}
"""

    keyboard = [
        [InlineKeyboardButton("✅ Я ОПЛАТИЛ", callback_data=f"paid_{order_id}")],
        [InlineKeyboardButton("⬅️ НАЗАД", callback_data="back")]
    ]

    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ================== ОПЛАТИЛ ==================
async def paid_handler(update, context):
    order_id = update.callback_query.data.split("_")[1]

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET consent=1 WHERE id=?", (order_id,))
    conn.commit()
    conn.close()

    text = f"""
✅ Платёж отмечен!

📩 Теперь отправьте чек менеджеру:
👉 @bazaotvetov2026oge

❗ В сообщении укажите:
— Номер заказа: {order_id}

После проверки вам выдадут ответы 📚
"""

    await update.callback_query.message.reply_text(text)

# ================== ФОТО ==================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "awaiting_payment" not in context.user_data:
        return

    order_id = context.user_data["awaiting_payment"]

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT product, price FROM orders WHERE id=?", (order_id,))
    order = cursor.fetchone()

    if not order:
        return

    product, price = order

    user = update.message.from_user

    username = f"@{user.username}" if user.username else f"{user.first_name} (ID: {user.id})"

    caption = f"Пользователь {username} оплатил {product} на {price}₽. Согласие получено."

    await context.bot.forward_message(
        chat_id=MANAGER_ID,
        from_chat_id=update.message.chat_id,
        message_id=update.message.message_id
    )

    await context.bot.send_message(MANAGER_ID, caption)

    await update.message.reply_text("Чек отправлен на проверку ✅")

# ================== МОИ ПОКУПКИ ==================
async def my_orders(update, context):
    user_id = update.callback_query.from_user.id

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT product FROM orders WHERE user_id=? AND status='completed'", (user_id,))
    orders = cursor.fetchall()

    text = "Ваши покупки:\n"
    if not orders:
        text += "Нет покупок"
    else:
        for o in orders:
            text += f"✔ {o[0]}\n"

    await update.callback_query.edit_message_text(text, reply_markup=back_button())

# ================== ПОМОЩЬ ==================
async def help_menu(update, context):
    text = "Выберите товар → оплатите → отправьте чек → получите доступ"
    await update.callback_query.edit_message_text(text, reply_markup=back_button())

# ================== МЕНЕДЖЕР ==================
async def check_orders(update, context):
    if update.effective_user.id != MANAGER_ID:
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT id, product FROM orders WHERE status='pending'")
    orders = cursor.fetchall()

    text = "Ожидающие заказы:\n"
    for o in orders:
        text += f"{o[0]} - {o[1]}\n"

    await update.message.reply_text(text)

async def confirm_order(update, context):
    if update.effective_user.id != MANAGER_ID:
        return

    order_id = context.args[0]

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("UPDATE orders SET status='completed' WHERE id=?", (order_id,))
    conn.commit()

    await update.message.reply_text(f"Заказ {order_id} подтвержден")

async def cancel_order(update, context):
    if update.effective_user.id != MANAGER_ID:
        return

    order_id = context.args[0]

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("UPDATE orders SET status='cancelled' WHERE id=?", (order_id,))
    conn.commit()

    await update.message.reply_text(f"Заказ {order_id} отменен")

# ================== ОБРАБОТЧИК ==================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    await query.answer()

    if data == "oge":
        await oge_menu(update, context)
    elif data == "vpr":
        await vpr_menu(update, context)
    elif data == "mcko":
        await mcko_menu(update, context)
    elif data == "probnik":
        await probnik_menu(update, context)
    elif data == "back":
        await query.edit_message_text("Главное меню", reply_markup=main_menu())
    elif data == "help":
        await help_menu(update, context)
    elif data == "my_orders":
        await my_orders(update, context)

    elif data.startswith("buy_"):
        mapping = {
            "buy_oge_premium": ("ОГЭ PREMIUM", 2490),
            "buy_oge_medium": ("ОГЭ MEDIUM", 1490),
            "buy_oge_lite": ("ОГЭ LITE", 990),
            "buy_vpr_vip": ("ВПР VIP", 1300),
            "buy_vpr_one": ("ВПР 1 предмет", 500),
            "buy_mcko_vip": ("МЦКО VIP", 1300),
            "buy_mcko_one": ("МЦКО 1 предмет", 500),
            "buy_probnik": ("ПРОБНИКИ", 500),
        }

        product, price = mapping[data]
        await send_payment(update, context, product, price)

    elif data.startswith("paid_"):
        await paid_handler(update, context)

# ================== MAIN ==================
import os
import threading


def main():
    init_db()

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    application.run_polling()
    


if __name__ == "__main__":
    main()
