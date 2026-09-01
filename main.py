from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply, ChatMember
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.error import TelegramError
import sqlite3
from datetime import datetime
import random
import string

BOT_TOKEN = "8965685820:AAGuwWH9XkeIkrydQoJPnrkaUOFK5G9_V58"
ADMIN_ID = 6078875175

CHANNEL = "@hidemychatRobot0"

def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    link_code TEXT UNIQUE,
                    anon_code TEXT UNIQUE,
                    created_at TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS blocks (
                    blocker_id INTEGER,
                    blocked_id INTEGER,
                    PRIMARY KEY (blocker_id, blocked_id)
                )''')
    conn.commit()
    conn.close()

def generate_anon_code():
    return ''.join(random.choices(string.digits, k=7))

def get_or_create_user(user_id, username, full_name):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT link_code, anon_code FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if row:
        conn.close()
        return row[0], row[1]
    
    link_code = str(user_id)
    anon_code = generate_anon_code()
    
    while True:
        c.execute("SELECT 1 FROM users WHERE anon_code = ?", (anon_code,))
        if not c.fetchone():
            break
        anon_code = generate_anon_code()
    
    c.execute(
        "INSERT INTO users (user_id, username, full_name, link_code, anon_code, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, username, full_name, link_code, anon_code, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    return link_code, anon_code

def is_blocked(blocker_id, blocked_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT 1 FROM blocks WHERE blocker_id = ? AND blocked_id = ?", (blocker_id, blocked_id))
    result = c.fetchone()
    conn.close()
    return bool(result)

def block_user(blocker_id, blocked_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO blocks (blocker_id, blocked_id) VALUES (?, ?)", (blocker_id, blocked_id))
    conn.commit()
    conn.close()

async def is_member(bot, user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL, user_id=user_id)
        return member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except TelegramError:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    link_code, anon_code = get_or_create_user(user.id, user.username, user.full_name)

    if context.args:
        if not await is_member(context.bot, user.id):
            await send_join_message(update, context)
            return

        target_code = context.args[0]
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("SELECT user_id, full_name FROM users WHERE link_code = ?", (target_code,))
        target = c.fetchone()
        conn.close()

        if target and target[0] != user.id:
            context.user_data["target_id"] = target[0]
            await update.message.reply_text(
                "شما در حال ارسال پیام ناشناس هستید.\n\nپیام خود را بنویسید:",
                reply_markup=ForceReply(selective=True)
            )
            return
        else:
            await update.message.reply_text("لینک نامعتبر است.")
            return

    if not await is_member(context.bot, user.id):
        await send_join_message(update, context)
        return

    await send_main_panel(update, context)

async def send_join_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("کانال اجباری", url="https://t.me/hidemychatRobot0")],
        [InlineKeyboardButton("جوین شدم✅", callback_data="check_join")]
    ]
    text = (
        "درود و عرض ادب !\n"
        "خوش اومدی\n\n"
        "🥹❤️برای ادامه استفاده از ربات زحمت بکش توی کانال زیر جوین شو"
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def send_main_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("دریافت لینک ناشناس 🔗", callback_data="copy_link")],
        [InlineKeyboardButton("لیست مسدودی 🔴", callback_data="block_list")],
        [InlineKeyboardButton("چنل پشتیبانی ✅", url="https://t.me/hidemychatRobot0")],
        [InlineKeyboardButton("راهنما 🤔", callback_data="help")]
    ]
    text = (
        "درودد مجدد\n"
        "ممنون که ربات مارو انتخاب کردی\n"
        "میتونی با پنل شیشه ای زیر از قابلیت های ربات ما استفاده کنی :"
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    if not await is_member(context.bot, user.id):
        await send_join_message(update, context)
        return

    if "target_id" in context.user_data:
        target_id = context.user_data["target_id"]

        if is_blocked(target_id, user.id):
            await update.message.reply_text("شما توسط این کاربر بلاک شده‌اید.")
            context.user_data.clear()
            return

        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("SELECT anon_code FROM users WHERE user_id = ?", (user.id,))
        row = c.fetchone()
        anon_code = row[0] if row else "0000000"
        conn.close()

        keyboard = [[
            InlineKeyboardButton("پاسخ", callback_data=f"reply_{user.id}"),
            InlineKeyboardButton("بلاک", callback_data=f"block_{user.id}")
        ]]

        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"کاربر {anon_code} برای شما پیام ناشناسی ارسال کرد :\n\n{text}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            await update.message.reply_text("✅ پیام ناشناس با موفقیت ارسال شد.")
        except:
            await update.message.reply_text("❌ خطا در ارسال پیام.")
        
        context.user_data.clear()
        return

    if "reply_to" in context.user_data:
        try:
            await context.bot.send_message(
                chat_id=context.user_data["reply_to"],
                text=f"💬 پاسخ ناشناس:\n\n{text}"
            )
            await update.message.reply_text("✅ پاسخ ارسال شد.")
        except:
            await update.message.reply_text("❌ خطا در ارسال پاسخ.")
        context.user_data.clear()

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "check_join":
        if await is_member(context.bot, user_id):
            await send_main_panel(update, context)
        else:
            await query.answer("هنوز عضو همه کانال ها نشدی❌ - گلدن چت", show_alert=True)
            await send_join_message(update, context)

    elif data == "copy_link":
        bot_username = (await context.bot.get_me()).username
        link_code, _ = get_or_create_user(user_id, query.from_user.username, query.from_user.full_name)
        link = f"https://t.me/{bot_username}?start={link_code}"
        await query.edit_message_text(f"لینک اختصاصی شما:\n`{link}`", parse_mode="Markdown")

    elif data == "help":
        await query.edit_message_text(
            "📖 راهنما:\n\n"
            "۱. لینک ناشناست رو بگیر و به بقیه بده\n"
            "۲. بقیه می‌تونن برات پیام ناشناس بفرستن\n"
            "۳. می‌تونی جواب بدی یا بلاک کنی"
        )

    elif data == "block_list":
        await query.answer("این قابلیت به زودی اضافه می‌شه", show_alert=True)

    elif data.startswith("reply_"):
        context.user_data["reply_to"] = int(data.split("_")[1])
        await query.message.reply_text("پاسخ خود را بنویسید:", reply_markup=ForceReply(selective=True))

    elif data.startswith("block_"):
        blocked = int(data.split("_")[1])
        block_user(user_id, blocked)
        await query.edit_message_text("کاربر بلاک شد.")

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    print("ربات روشن شد...")
    app.run_polling()

if __name__ == "__main__":
    main()
