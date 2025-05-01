# bot.py

import os
import json
import logging
from datetime import datetime
import urllib.parse
from telegram.constants import ParseMode
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
TWITTER_HANDLE = os.getenv("TWITTER_HANDLE")
BOT_USERNAME = "UtilizersBot"

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
                referrer_data["referrals"] = referrer_data.get("referrals", 0) + 1
                update_user(referrer_id, referrer_data)
                user_data["referral"] = referrer_id
                await update.message.reply_text(
                    "🎯 You just referred a user and got 25 Points...",
                    reply_markup=reply_markup
                )

    update_user(user.id, user_data)

    keyboard = [
        [InlineKeyboardButton("✅ Join Telegram Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton("🐦 Follow Twitter", url=f"https://twitter.com/{TWITTER_HANDLE}")],
        [InlineKeyboardButton("💬 Join Whatsapp Group", url="https://chat.whatsapp.com/KyBPEZKLjAZ8JMgFt9KMft")],
        [InlineKeyboardButton("📢 Join Whatsapp Channel", url="https://whatsapp.com/channel/0029VbAXEgUFy72Ich07Z53o")],
        [InlineKeyboardButton("🔍 Verify Tasks", callback_data="verify_tasks")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"🎯 WELCOME {user.username} \n\nTo participate in the campaign, complete the following tasks:\n\n"
        f"1. Join our Telegram channel\n"
        f"2. Follow our Twitter account ({TWITTER_HANDLE})\n\n"
        "After that, click the button below to verify!",
        reply_markup=reply_markup
    )


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
        "Click the button below after you've followed us.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# --- Confirm Twitter ---
async def confirm_twitter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data = get_user(user_id)
    user_data["verified_user"] = True
    update_user(user_id, user_data)

    await query.edit_message_text("✅ You're verified. \n\nTap or type /play to begin!")


# --- Verify Daily Tasks ---
async def verify_daily_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    await query.edit_message_text("📸 Please upload screenshots to verify task completion.")
    context.user_data["awaiting_verification"] = True

# --- Handle Verification Images ---
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    reply_keyboard = [
        [ KeyboardButton("/play") ]
    ]
    markup = ReplyKeyboardMarkup(
        reply_keyboard,
        resize_keyboard=True,      # make buttons fit nicely
        one_time_keyboard=False    # keep the keyboard up until user dismisses
    )
    #keyboard = [[InlineKeyboardButton("Menu", callback_data="play")]]

    if context.user_data.get("awaiting_verification"):
        if not has_claimed_today(user_data, "task_points"):
            user_data["points"] = user_data.get("points", 0) + 30
            mark_claimed_today(user_data, "task_points")
            user_data["verified"] = True
            update_user(user_id, user_data)
            await update.message.reply_text("✅ Screenshot received. You have been awarded 30 points.", reply_markup=markup)
        else:
            await update.message.reply_text("✅ Screenshot received. You've already claimed task points for today.", reply_markup=markup)
        context.user_data["awaiting_verification"] = False


# --- Game Menu ---
async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)

    keyboard = [
        [InlineKeyboardButton("📊 Points Balance", callback_data="menu_points")],
        [InlineKeyboardButton("👥 Referral", callback_data="menu_referral")],
        [InlineKeyboardButton("🏆 Position", callback_data="menu_position")],
        [InlineKeyboardButton("📝 Tasks", callback_data="menu_tasks")],
        [InlineKeyboardButton("✅ Verify Daily Task Completion", callback_data="verify_daily_tasks")],
        [InlineKeyboardButton("🎁 Bonus Daily Points", callback_data="menu_bonus")],
        [InlineKeyboardButton("🚀 Upgrade to Ambassador", callback_data="menu_ambassador")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome utilizer! Use the menu below to explore:", reply_markup=reply_markup)

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
        ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        count = user_data.get("referrals", 0)
        text = f"👥 Your referral link:\n{ref_link}\n\nTotal referrals: {count}"
    elif data == "menu_position":
        all_users = load_data()
        sorted_users = sorted(all_users.items(), key=lambda x: x[1].get("points", 0), reverse=True)
        position = next((i for i, (uid, _) in enumerate(sorted_users, 1) if uid == str(user_id)), None)
        if position is not None:
            rank = position + 1064
            text = f"🏆 Your leaderboard position: {rank} \n\nYou could be 1 of 1,000 lucky members picked to be a verified tester and earn $50 every 2 weeks, no payment needed! \n\nEarn more points to rank up!"
        else:
            text = "❌ Could not determine your position."
    elif data == "menu_tasks":
        bot_link = "https://t.me/UtilizersBot"
        task_link1 = f"https://twitter.com/{TWITTER_HANDLE}"
        post_text = f"I just joined the Utilizers, and you should too! \n\nGet picked as one of the 1,000 verified testers of THE UTILIZERS beta platform and earn $50 every 2 weeks for FREE. \n\nAct fast, spots are limited!\n\n{bot_link}"
        encoded_text = urllib.parse.quote(post_text)
        task_link2 = f"https://twitter.com/intent/tweet?text={encoded_text}"
        task_link3 = f"https://wa.me/?text={encoded_text}"

        message = (
            f"📝 Follow <a href='{task_link1}'>Utilizer01</a>\n\n"
            f"📝 <a href='{task_link2}'>Post on X (Twitter)</a>\n\n"
            f"📝 <a href='{task_link3}'>Share to 5 WhatsApp groups and your status</a>"
        )

        await query.message.reply_text(message, parse_mode=ParseMode.HTML)

        #text = f"📝 Follow Utilizer01 {task_link1} \n\n 📝 Post on X (fka Twitter) {task_link2} \n\n 📝 Share to 5 whatsapp group and status {task_link3}"
    elif data == "menu_bonus":
        if not has_claimed_today(user_data, "bonus_points"):
            user_data["points"] = user_data.get("points", 0) + 5
            mark_claimed_today(user_data, "bonus_points")
            update_user(user_id, user_data)
            text = "🎁 You claimed your 5 daily bonus points!"
        else:
            text = "❌ You've already claimed today's bonus. Come back tomorrow."
    elif data == "menu_ambassador":
        text = "🚀 To become an Ambassador, you must have the following... \n 1. Must have invited 50 members. \n 2. Must have above 500 points"
    else:
        text = "Unknown command."

    keyboard = [
        [InlineKeyboardButton("📊 Points Balance", callback_data="menu_points")],
        [InlineKeyboardButton("👥 Referral", callback_data="menu_referral")],
        [InlineKeyboardButton("🏆 Position", callback_data="menu_position")],
        [InlineKeyboardButton("📝 Tasks", callback_data="menu_tasks")],
        [InlineKeyboardButton("✅ Verify Task Completion", callback_data="verify_daily_tasks")],
        [InlineKeyboardButton("🎁 Bonus Daily Points", callback_data="menu_bonus")],
        [InlineKeyboardButton("🚀 Upgrade to Ambassador", callback_data="menu_ambassador")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)

# --- Run Bot ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(confirm_twitter, pattern="^confirm_twitter$"))
    app.add_handler(CommandHandler("play", play))
    app.add_handler(CallbackQueryHandler(verify_tasks, pattern="^verify_tasks$"))
    app.add_handler(CallbackQueryHandler(verify_daily_tasks, pattern="^verify_daily_tasks$"))
    app.add_handler(CallbackQueryHandler(handle_menu, pattern="^menu_.*"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    app.run_polling()

if __name__ == "__main__":
    main()
