# bot.py

import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
TWITTER_HANDLE = os.getenv("TWITTER_HANDLE")
BOT_USERNAME = "Seizer_affBot"

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_FILE = "user_data.json"

# --- Utility Functions ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_user(user_id):
    data = load_data()
    return data.get(str(user_id), {})

def update_user(user_id, user_info):
    data = load_data()
    data[str(user_id)] = user_info
    save_data(data)

def has_claimed_today(user_info, field):
    today = datetime.utcnow().date().isoformat()
    return user_info.get(field, {}).get("date") == today

def mark_claimed_today(user_info, field):
    today = datetime.utcnow().date().isoformat()
    user_info[field] = {"date": today}

# --- Start Command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user(user.id)

    if "referral" not in user_data:
        if context.args:
            referrer_id = context.args[0]
            if referrer_id != str(user.id):
                referrer_data = get_user(referrer_id)
                referrer_data["points"] = referrer_data.get("points", 0) + 25
                update_user(referrer_id, referrer_data)
                user_data["referral"] = referrer_id

    update_user(user.id, user_data)

    keyboard = [
        [InlineKeyboardButton("✅ Join Telegram Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton("🐦 Follow Twitter", url=f"https://twitter.com/{TWITTER_HANDLE}")],
        [InlineKeyboardButton("🐦 Join Whatsapp Group", url="https://chat.whatsapp.com/KyBPEZKLjAZ8JMgFt9KMft")],
        [InlineKeyboardButton("🐦 Join Whatsapp Channel", url="https://whatsapp.com/channel/0029VbAXEgUFy72Ich07Z53o")],
        [InlineKeyboardButton("🔍 Verify Tasks", callback_data="verify_tasks")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🎯 To participate in the game, complete the following tasks:\n\n"
        f"1. Join our Telegram channel\n"
        f"2. Follow our Twitter account ({TWITTER_HANDLE})\n\n"
        "After that, click the button below to verify!",
        reply_markup=reply_markup
    )

# --- Verify Tasks ---
async def verify_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    try:
        chat_member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if chat_member.status not in ["member", "administrator", "creator"]:
            raise Exception("Not a member")
    except Exception:
        await query.edit_message_text("❌ You have not joined the Telegram channel. Please do that first.")
        return

    keyboard = [[InlineKeyboardButton("✅ I've Followed on Twitter", callback_data="confirm_twitter")]]
    await query.edit_message_text(
        "👀 We can't verify Twitter follows automatically due to API limits.\n\n"
        "Please click the button below *after* you've followed us on Twitter.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- Confirm Twitter ---
async def confirm_twitter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    user_data = get_user(user_id)
    if not has_claimed_today(user_data, "task_points"):
        user_data["points"] = user_data.get("points", 0) + 30  # 3 tasks x 10 points
        mark_claimed_today(user_data, "task_points")
    user_data["verified"] = True
    update_user(user_id, user_data)

    await query.edit_message_text("✅ Tasks completed and 30 points awarded. Use /play to continue.")

# --- Game Menu ---
async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    if not user_data.get("verified"):
        await update.message.reply_text("❌ You must complete the tasks first. Use /start to begin.")
        return

    referral_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"

    keyboard = [
        [InlineKeyboardButton("📊 Points Balance", callback_data="menu_points")],
        [InlineKeyboardButton("👥 Referral", callback_data="menu_referral")],
        [InlineKeyboardButton("🏆 Position", callback_data="menu_position")],
        [InlineKeyboardButton("📝 Tasks", callback_data="menu_tasks")],
        [InlineKeyboardButton("🎁 Bonus Daily Points", callback_data="menu_bonus")],
        [InlineKeyboardButton("🚀 Upgrade to Ambassador", callback_data="menu_ambassador")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🎮 Welcome to the game! Use the menu below to explore:", reply_markup=reply_markup)

# --- Menu Handlers ---
async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data = get_user(user_id)
    data = query.data

    if data == "menu_points":
        text = f"💰 Your current points: {user_data.get('points', 0)}"
    elif data == "menu_referral":
        text = f"👥 Share your referral link: https://t.me/{BOT_USERNAME}?start={user_id}"
    elif data == "menu_position":
        text = "🏆 Leaderboard not implemented yet."
    elif data == "menu_tasks":
        text = "📝 Tasks completed. Come back tomorrow to claim more points."
    elif data == "menu_bonus":
        if not has_claimed_today(user_data, "bonus_points"):
            user_data["points"] = user_data.get("points", 0) + 5
            mark_claimed_today(user_data, "bonus_points")
            update_user(user_id, user_data)
            text = "🎁 You claimed your 5 daily bonus points!"
        else:
            text = "❌ You've already claimed today's bonus. Come back tomorrow."
    elif data == "menu_ambassador":
        text = "🚀 Ambassador upgrade not available yet."
    else:
        text = "Unknown command."

    keyboard = [
        [InlineKeyboardButton("📊 Points Balance", callback_data="menu_points")],
        [InlineKeyboardButton("👥 Referral", callback_data="menu_referral")],
        [InlineKeyboardButton("🏆 Position", callback_data="menu_position")],
        [InlineKeyboardButton("📝 Tasks", callback_data="menu_tasks")],
        [InlineKeyboardButton("🎁 Bonus Daily Points", callback_data="menu_bonus")],
        [InlineKeyboardButton("🚀 Upgrade to Ambassador", callback_data="menu_ambassador")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)

# --- Run Bot ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("play", play))
    app.add_handler(CallbackQueryHandler(verify_tasks, pattern="^verify_tasks$"))
    app.add_handler(CallbackQueryHandler(confirm_twitter, pattern="^confirm_twitter$"))
    app.add_handler(CallbackQueryHandler(handle_menu, pattern="^menu_.*"))

    app.run_polling()

if __name__ == "__main__":
    main()
