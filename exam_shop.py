import logging
import sqlite3
from datetime import datetime, timedelta
import uuid
import os
import threading

from flask import Flask

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

# ================== FLASK ==================
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Bot running"

@flask_app.route("/health")
def health():
    return "OK", 200

def run_web():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)

# ================== НАСТРОЙКИ ==================
BOT_TOKEN = "ТВОЙ_ТОКЕН_СЮДА"
MANAGER_ID = 1911945305

CARD_NUMBER = "2200 1545 7393 3982"
CARD_HOLDER = "Максим"
BANK_NAME = "Альфа Банк"

PRIVACY_URL = "https://telegra.ph/SOGLASHENIE-05-26-4"
AGREEMENT_URL = "https://telegra.ph/SOGLASHENIE-05-26-4"

DB_NAME = "orders.db"

logging.basicConfig(level=logging.INFO)

# ================== БАЗА ==================
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
    await update.message.reply_text("Добро пожаловать", reply_markup=main_menu())

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

    text = f"Заказ {order_id}\nОплатить до {deadline.strftime('%H:%M')}"

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

    await update.callback_query.message.reply_text(f"Чек отправь менеджеру. Заказ: {order_id}")

# ================== ФОТО ==================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Фото получено")

# ================== ОБРАБОТЧИК ==================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    await update.callback_query.answer()

    if data.startswith("paid_"):
        await paid_handler(update, context)

# ================== MAIN ==================
def main():
    init_db()

    # Flask (Render)
    threading.Thread(target=run_web, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    app.run_polling()

if __name__ == "__main__":
    main()
