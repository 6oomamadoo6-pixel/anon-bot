import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
import sqlite3
from datetime import datetime

# ---------------- تنظیمات ----------------
BOT_TOKEN = "8910984290:AAFjb0POsdmDFIAurBv0mU1590TMJXUYaYw"
ADMIN_ID = 6078875175

# ---------------- دیتابیس ----------------
def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    link_code TEXT UNIQUE,
                    created_at TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS blocks (
                    blocker_id INTEGER,
                    blocked_id INTEGER,
                    PRIMARY KEY (blocker_id, blocked_id)
                )''')
    conn.commit()
    conn.close()

def get_or_create_user(user_id, username, full_name):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT link_code FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if row:
        link_code = row[0]
    else:
        link_code = str(user_id)
        c.execute("INSERT INTO users (user_id, username, full_name, link_code, created_at) VALUES (?, ?, ?, ?, ?)",
                  (user_id, username, full_name, link_code, datetime.now().isoformat()))
        conn.commit()
    conn.close()
    return link_code

def is_blocked(blocker_id, blocked_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT 1 FROM blocks WHERE blocker_id = ? AND blocked_id = ?", (blocker_id, blocked_id))
    result = c.fetchone()
    conn.close()
    return result is not None

def block_user(blocker_id, blocked_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO blocks (blocker_id, blocked_id) VALUES (?, ?)", (blocker_id, blocked_id))
    conn.commit()
    conn.close()

# ---------------- هندلرها ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    link_code = get_or_create_user(user.id, user.username, user.full_name)

    if context.args:
        target_code = context.args[0]
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("SELECT user_id, full_name FROM users WHERE link_code = ?", (target_code,))
        target = c.fetchone()
        conn.close()

        if target and target[0] != user.id:
            context.user_data["target_id"] = target[0]
            context.user_data["target_name"] = target[1]
            await update.message.reply_text(
                f"شما در حال ارسال پیام ناشناس به {target[1]} هستید.\n\n"
                "پیام خود را بنویسید:",
                parse_mode="Markdown",
                reply_markup=ForceReply(selective=True)
            )
            return
        else:
            await update.message.reply_text("لینک نامعتبر است یا نمی‌توانید به خودتان پیام بدهید.")
            return

    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={link_code}"

    keyboard = [
        [InlineKeyboardButton("لینک من رو کپی کن", callback_data="copy_link")],
        [InlineKeyboardButton("راهنما", callback_data="help")]
    ]

    await update.message.reply_text(
        f"سلام {user.first_name} 👋\n\n"
        "این ربات پیام ناشناس است.\n"
        "لینک اختصاصی خودت رو به بقیه بده تا بتونن برات پیام ناشناس بفرستن.\n\n"
        f"🔗 لینک اختصاصی تو:\n{link}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    if "target_id" in context.user_data:
        target_id = context.user_data["target_id"]        target_name = context.user_data.get("target_name", "کاربر")
        if is_blocked(target_id, user.id):
            await update.message.reply_text("شما توسط این کاربر بلاک شده‌اید.")
            context.user_data.clear()
            return

        # ارسال پیام ناشناس
        keyboard = [[InlineKeyboardButton("پاسخ", callback_data=f"reply_{user.id}")]]
        sent = await context.bot.send_message(
            chat_id=target_id,
            text=f"پیام ناشناس جدید 💬\n\n{text}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await update.message.reply_text(f"پیام شما با موفقیت به {target_name} ارسال شد ✅")
    else:
        await update.message.reply_text("برای ارسال پیام، اول روی لینک اختصاصی شروع کن 🤝")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "copy_link":
        bot_username = (await context.bot.get_me()).username
        link_code = get_or_create_user(query.from_user.id, query.from_user.username, query.from_user.full_name)
        link = f"https://t.me/{bot_username}?start={link_code}"
        await query.answer()
        await query.edit_message_text(
            f"📋 لینک تو:\n{link}\n\nروی لینک بزن تا کپی بشه.",
            reply_markup=None
        )
    elif data == "help":    elif data == "help":
        help_keyboard = [[InlineKeyboardButton("بازگشت ◀️", callback_data="back_to_main")]]
        help_text = (
            "🤖 راهنمای ربات پیام ناشناس\n\n"
            "۱. روی /start بزن تا لینک اختصاصیت ساخته بشه.\n"
            "۲. اون لینک رو برای دوستات بفرست.\n"
            "۳. هرکی روش بزنه می‌تونه برات پیام ناشناس بفرسته.\n"
            "۴. تو هم می‌تونی پاسخ بدی — هویت فاش نمیشه.\n\n"
            "/block <شناسه> — مسدود کردن کاربر\n"
            "/unblock <شناسه> — رفع مسدودی"
        )import re

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("ربات فعال شد ✅")if __name__ == "__main__":
