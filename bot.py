import os
import logging
from flask import Flask
from threading import Thread
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler, CallbackContext
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
TWITTER_HANDLE = os.getenv("TWITTER_HANDLE")

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Web server for Railway keep-alive
app = Flask(__name__)

@app.route("/")
def index():
    return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

# Verified users set
verified_users = set()

# Bot Handlers
def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("✅ Join Telegram Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton("🐦 Follow Twitter", url=f"https://twitter.com/{TWITTER_HANDLE}")],
        [InlineKeyboardButton("🔍 Verify Tasks", callback_data="verify_tasks")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        "🎯 To participate, complete the following tasks:\n\n"
        f"1. Join our Telegram channel\n"
        f"2. Follow our Twitter (@{TWITTER_HANDLE})\n\n"
        "Then click the button below to verify!",
        reply_markup=reply_markup
    )

def verify_tasks(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id

    try:
        chat_member = context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if chat_member.status not in ["member", "administrator", "creator"]:
            raise Exception("Not a member.")
    except Exception as e:
        query.answer()
        query.edit_message_text("❌ You have not joined the Telegram channel. Please do that first.")
        return

    keyboard = [
        [InlineKeyboardButton("✅ I've Followed on Twitter", callback_data="confirm_twitter")]
    ]
    query.answer()
    query.edit_message_text(
        "👀 We can't automatically verify Twitter follows.\n\n"
        "Please click below *after* you've followed us.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def confirm_twitter(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id

    verified_users.add(user_id)

    query.answer()
    query.edit_message_text(
        "✅ Details submitted, be patient as the data is being processed."
    )

def play(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in verified_users:
        update.message.reply_text("❌ You must complete the tasks first. Use /start.")
        return

    update.message.reply_text("🎲 Welcome to the game! [Insert game logic here...]")

def main():
    # Start the web server in a separate thread
    Thread(target=run_flask).start()

    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("play", play))
    dp.add_handler(CallbackQueryHandler(verify_tasks, pattern="^verify_tasks$"))
    dp.add_handler(CallbackQueryHandler(confirm_twitter, pattern="^confirm_twitter$"))

    print("🤖 Bot is running...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
