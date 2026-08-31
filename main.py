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
                f"شما در حال ارسال پیام ناشناس به **{target[1]}** هستید.\n\n"
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
        f"🔗 لینک اختصاصی تو:\n`{link}`",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    if "target_id" in context.user_data:
        target_id = context.user_data["target_id"]

        if is_blocked(target_id, user.id):
            await update.message.reply_text("شما توسط این کاربر بلاک شده‌اید.")
            context.user_data.clear()
            return

        keyboard = [
            [
                InlineKeyboardButton("پاسخ", callback_data=f"reply_{user.id}"),
                InlineKeyboardButton("بلاک", callback_data=f"block_{user.id}")
            ]
        ]

        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"📩 **پیام ناشناس جدید**\n\n{text}\n\n"
                     f"از طرف: ناشناس (آیدی عددی: `{user.id}`)",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            await update.message.reply_text("✅ پیام ناشناس با موفقیت ارسال شد.")
        except Exception:
            await update.message.reply_text("❌ ارسال پیام با خطا مواجه شد.")

        context.user_data.clear()
        return

    if "reply_to" in context.user_data:
        reply_to = context.user_data["reply_to"]
        try:
            await context.bot.send_message(
                chat_id=reply_to,
                text=f"💬 **پاسخ ناشناس**\n\n{text}"
            )
            await update.message.reply_text("✅ پاسخ ارسال شد.")
        except:
            await update.message.reply_text("❌ ارسال پاسخ با خطا مواجه شد.")
        context.user_data.clear()
        return

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "copy_link":
        bot_username = (await context.bot.get_me()).username
        link_code = get_or_create_user(user_id, query.from_user.username, query.from_user.full_name)
        link = f"https://t.me/{bot_username}?start={link_code}"
        await query.edit_message_text(f"لینک اختصاصی شما:\n`{link}`", parse_mode="Markdown")

    elif data == "help":
        await query.edit_message_text(
            "📖 راهنما:\n\n"
            "۱. لینک اختصاصی خودت رو به بقیه بده\n"
            "۲. بقیه با لینک وارد ربات می‌شن و بهت پیام ناشناس می‌فرستن\n"
            "۳. می‌تونی جواب بدی یا بلاک کنی\n\n"
            "نکته: هویت فرستنده کاملاً مخفی می‌مونه."
        )

    elif data.startswith("reply_"):
        target = int(data.split("_")[1])
        context.user_data["reply_to"] = target
        await query.message.reply_text(
            "پاسخ خود را بنویسید:",
            reply_markup=ForceReply(selective=True)
        )

    elif data.startswith("block_"):
        blocked = int(data.split("_")[1])
        block_user(user_id, blocked)
        await query.edit_message_text("کاربر بلاک شد.")

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & \~filters.COMMAND, handle_message))

    print("ربات روشن شد...")
    app.run_polling()

if __name__ == "__main__":
    main()
