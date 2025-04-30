# bot.py
import os
import json
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
TWITTER_HANDLE = os.getenv("TWITTER_HANDLE")

# File-based storage
DATA_FILE = "user_data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_user(user_id):
    data = load_data()
    return data.get(str(user_id), None)

def update_user(user_id, **kwargs):
    data = load_data()
    user = data.get(str(user_id), {
        "points": 0,
        "referrals": 0,
        "verified": False,
        "ambassador": False,
        "username": "",
        "full_name": ""
    })
    user.update(kwargs)
    data[str(user_id)] = user
    save_data(data)
    return user

def all_users():
    return load_data()

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = update.message.from_user
    user_id = user_data.id
    args = context.args
    referrer_id = args[0] if args and args[0].isdigit() else None

    if not get_user(user_id):
        update_user(
            user_id,
            username=user_data.username,
            full_name=user_data.full_name or f"{user_data.first_name} {user_data.last_name or ''}".strip()
        )
        if referrer_id and int(referrer_id) != user_id:
            referrer = get_user(referrer_id)
            if referrer:
                update_user(referrer_id,
                    referrals=referrer["referrals"] + 1,
                    points=referrer["points"] + 10
                )
    await play(update, context)

# Play command
async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    if not user or not user.get("verified"):
        await update.message.reply_text("❌ You must complete the tasks first. Use /start to begin.")
        return

    keyboard = [
        [InlineKeyboardButton("💰 Points Balance", callback_data="menu_points")],
        [InlineKeyboardButton("🔗 Referral", callback_data="menu_referral")],
        [InlineKeyboardButton("🏆 Position", callback_data="menu_position")],
        [InlineKeyboardButton("📋 Tasks", callback_data="menu_tasks")],
        [InlineKeyboardButton("📸 Verify Tasks Completion", callback_data="menu_verify_tasks")],
        [InlineKeyboardButton("🚀 Upgrade to Ambassador", callback_data="menu_ambassador")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("🎮 Welcome to the Game Menu!", reply_markup=reply_markup)

# Verify Telegram Channel
async def verify_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    try:
        chat_member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if chat_member.status not in ["member", "administrator", "creator"]:
            raise Exception("Not a member")
        update_user(user_id, verified=True)
        await query.edit_message_text("✅ Telegram channel verified successfully!")
    except Exception:
        await query.edit_message_text("❌ You have not joined the Telegram channel. Please do that first.")

# Screenshot handler
async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = update.message.from_user
    user_id = user_data.id

    if update.message.photo:
        update_user(user_id, verified=True)
        await update.message.reply_text("✅ Screenshot received. Your task will be verified.")
    else:
        await update.message.reply_text("❌ Please upload a screenshot image.")

# Menu actions
async def menu_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    user_id = update.callback_query.from_user.id
    user = get_user(user_id)
    await update.callback_query.edit_message_text(
        f"💰 Your points: `{user['points']}`", parse_mode="Markdown")

async def menu_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    user_id = update.callback_query.from_user.id
    user = get_user(user_id)
    referral_link = f"https://t.me/{context.bot.username}?start={user_id}"
    await update.callback_query.edit_message_text(
        f"🔗 Your referral link:\n{referral_link}\n\n👥 Referrals: {user['referrals']}")

async def menu_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    user_id = update.callback_query.from_user.id
    data = all_users()
    sorted_users = sorted(data.items(), key=lambda x: x[1]["points"], reverse=True)
    for i, (uid, u) in enumerate(sorted_users):
        if str(user_id) == uid:
            pos = i + 1065
            await update.callback_query.edit_message_text(
                f"🏆 Your leaderboard position: #{pos}\nPoints: {u['points']}")
            return
    await update.callback_query.edit_message_text("❌ You are not on the leaderboard.")

async def menu_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    keyboard = [
        [InlineKeyboardButton("✅ Join Telegram Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton("🐦 Follow Twitter", url=f"https://twitter.com/{TWITTER_HANDLE}")],
        [InlineKeyboardButton("👥 Join WhatsApp Group", url="https://chat.whatsapp.com/KyBPEZKLjAZ8JMgFt9KMft")],
        [InlineKeyboardButton("📢 Join WhatsApp Channel", url="https://whatsapp.com/channel/0029VbAXEgUFy72Ich07Z53o")],
        [InlineKeyboardButton("🔍 Verify Telegram Task", callback_data="verify_tasks")]
    ]
    await update.callback_query.edit_message_text(
        "🎯 Complete the following tasks to continue:",
        reply_markup=InlineKeyboardMarkup(keyboard))

async def menu_verify_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "📸 Please upload a screenshot showing you've completed the tasks.\n⚠️ Your submission will be verified manually.")

async def menu_ambassador(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "🚀 Requirements to become an ambassador:\n\n- Minimum 200 points\n- At least 5 referrals\n- Active participation\n\nApply now by messaging @admin")

# Main bot setup
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("play", play))

    app.add_handler(CallbackQueryHandler(verify_tasks, pattern="^verify_tasks$"))
    app.add_handler(CallbackQueryHandler(menu_points, pattern="^menu_points$"))
    app.add_handler(CallbackQueryHandler(menu_referral, pattern="^menu_referral$"))
    app.add_handler(CallbackQueryHandler(menu_position, pattern="^menu_position$"))
    app.add_handler(CallbackQueryHandler(menu_tasks, pattern="^menu_tasks$"))
    app.add_handler(CallbackQueryHandler(menu_verify_tasks, pattern="^menu_verify_tasks$"))
    app.add_handler(CallbackQueryHandler(menu_ambassador, pattern="^menu_ambassador$"))

    app.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))

    app.run_polling()

if __name__ == "__main__":
    main()
