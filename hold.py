# bot.py

import os
import json
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
TWITTER_HANDLE = os.getenv("TWITTER_HANDLE")

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
    return data.get(str(user_id), {
        "verified": False,
        "points": 0,
        "referrals": [],
        "screenshot_uploaded": False,
        "username": "",
    })


def update_user(user_id, updates):
    data = load_data()
    uid = str(user_id)
    if uid not in data:
        data[uid] = get_user(user_id)
    data[uid].update(updates)
    save_data(data)


def generate_referral_link(user_id):
    return f"https://t.me/{os.getenv('BOT_USERNAME')}?start={user_id}"


# --- Start Command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or ""

    if context.args:
        referrer_id = context.args[0]
        if referrer_id != str(user_id):
            ref_data = get_user(referrer_id)
            if str(user_id) not in ref_data["referrals"]:
                ref_data["referrals"].append(str(user_id))
                ref_data["points"] += 10  # Reward referrer
                update_user(referrer_id, ref_data)

    update_user(user_id, {"username": username})  # Save username

    keyboard = [
        [InlineKeyboardButton("✅ Join Telegram Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton("🐦 Follow Twitter", url=f"https://twitter.com/{TWITTER_HANDLE}")],
        [InlineKeyboardButton("🐦 Join Whatsapp Group", url="https://chat.whatsapp.com/KyBPEZKLjAZ8JMgFt9KMft")],
        [InlineKeyboardButton("🐦 Join Whatsapp Channel", url="https://whatsapp.com/channel/0029VbAXEgUFy72Ich07Z53o")],
        [InlineKeyboardButton("🔍 Verify Tasks", callback_data="verify_tasks")]
    ]
    await update.message.reply_text(
        "🎯 To participate in the game, complete the following tasks:\n\n"
        "1. Join our Telegram channel\n"
        "2. Follow our Twitter account\n\n"
        "Then click 'Verify Tasks'.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# --- Verify Tasks ---
async def verify_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status not in ["member", "administrator", "creator"]:
            raise Exception("Not joined")
    except Exception:
        await query.edit_message_text("❌ You have not joined the Telegram channel. Please do that first.")
        return

    keyboard = [[InlineKeyboardButton("✅ I've Followed on Twitter", callback_data="confirm_twitter")]]
    await query.edit_message_text(
        "👀 We can't verify Twitter follows automatically.\n\n"
        "Click the button below *after* you've followed us.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# --- Confirm Twitter ---
async def confirm_twitter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    update_user(user_id, {"verified": True})
    await query.edit_message_text("✅ You're verified. Use /play to begin!")


# --- Play Command ---
async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)

    if not user_data.get("verified"):
        await update.message.reply_text("❌ You must complete tasks first. Use /start to begin.")
        return

    keyboard = [
        [InlineKeyboardButton("📊 Points Balance", callback_data="menu_points")],
        [InlineKeyboardButton("👥 Referral", callback_data="menu_referral")],
        [InlineKeyboardButton("🏆 Position", callback_data="menu_position")],
        [InlineKeyboardButton("📝 Tasks", callback_data="menu_tasks")],
        [InlineKeyboardButton("📸 Verify Tasks Completion", callback_data="menu_verify_tasks")],
        [InlineKeyboardButton("🚀 Upgrade to Ambassador", callback_data="menu_ambassador")],
    ]
    await update.message.reply_text("🎮 Welcome! Use the menu below:", reply_markup=InlineKeyboardMarkup(keyboard))


# --- Menu Callbacks ---
async def menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data = get_user(user_id)

    if query.data == "menu_points":
        await query.edit_message_text(f"📊 You have {user_data.get('points', 0)} points.")

    elif query.data == "menu_referral":
        ref_link = generate_referral_link(user_id)
        count = len(user_data.get("referrals", []))
        await query.edit_message_text(f"👥 Your referral link:\n{ref_link}\n\nYou’ve referred {count} users.")

    elif query.data == "menu_position":
        data = load_data()
        sorted_users = sorted(data.items(), key=lambda x: x[1].get("points", 0), reverse=True)
        position = 1065  # default start
        for i, (uid, udata) in enumerate(sorted_users, start=1):
            if str(user_id) == uid:
                position = i + 1064
                break
        await query.edit_message_text(f"🏆 Your leaderboard position: {position}")

    elif query.data == "menu_tasks":
        await query.edit_message_text(
            "📝 Complete the following tasks:\n"
            "1. Join our Telegram: https://t.me/{CHANNEL_USERNAME}\n"
            "2. Follow us on Twitter: https://twitter.com/{TWITTER_HANDLE}\n"
            "3. Join our WhatsApp group & channel"
        )

    elif query.data == "menu_verify_tasks":
        await query.edit_message_text(
            "📸 Upload a screenshot showing you've completed all tasks.\n"
            "⚠️ Submissions will be manually verified."
        )

    elif query.data == "menu_ambassador":
        await query.edit_message_text(
            "🚀 To become an ambassador:\n"
            "- At least 10 verified referrals\n"
            "- 200 points minimum\n"
            "Reply here to apply."
        )


# --- Screenshot Upload ---
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photo = update.message.photo[-1]
    file_path = f"screenshots/{user_id}.jpg"
    os.makedirs("screenshots", exist_ok=True)
    await photo.get_file().download_to_drive(file_path)

    update_user(user_id, {"screenshot_uploaded": True})
    await update.message.reply_text("✅ Screenshot received. It will be reviewed shortly.")


# --- Main ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("play", play))

    app.add_handler(CallbackQueryHandler(verify_tasks, pattern="^verify_tasks$"))
    app.add_handler(CallbackQueryHandler(confirm_twitter, pattern="^confirm_twitter$"))
    app.add_handler(CallbackQueryHandler(menu_buttons, pattern="^menu_"))

    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    app.run_polling()


if __name__ == "__main__":
    main()
