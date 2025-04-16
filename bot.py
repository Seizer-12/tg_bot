import logging
import os
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
TWITTER_HANDLE = os.getenv("TWITTER_HANDLE")

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dummy store to track users who completed tasks
verified_users = set()

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✅ Join Telegram Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton("🐦 Follow Twitter", url=f"https://twitter.com/{TWITTER_HANDLE}")],
        [InlineKeyboardButton("🔍 Verify Tasks", callback_data="verify_tasks")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🎯 To participate in the game, complete the following tasks:\n\n"
        f"1. Join our Telegram channel\n"
        f"2. Follow our Twitter account (@{TWITTER_HANDLE})\n\n"
        "After that, click the button below to verify!",
        reply_markup=reply_markup
    )

# --- Verification Handler ---

async def verify_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    # Verify Telegram Channel Membership
    try:
        chat_member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if chat_member.status not in ["member", "administrator", "creator"]:
            raise Exception("User not a member of the channel.")
    except Exception as e:
        await query.edit_message_text("❌ You have not joined the Telegram channel. Please do that first.")
        return

    # Simulated Twitter Follow Check (Manual)
    # You could use Twitter API here if needed
    keyboard = [
        [InlineKeyboardButton("✅ I've Followed on Twitter", callback_data="confirm_twitter")]
    ]
    await query.edit_message_text(
        "👀 We can't verify Twitter follows automatically due to Twitter API limitations.\n\n"
        "Please click the button below *after* you've followed us on Twitter.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def confirm_twitter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    verified_users.add(user_id)

    await query.edit_message_text(
        "✅ All tasks verified!\n\nYou're now allowed to access the game. Type /play to begin 🎮"
    )

# --- Game Command ---

async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in verified_users:
        await update.message.reply_text("❌ You must complete the tasks first. Use /start to begin.")
        return

    # Replace this with your actual game logic
    await update.message.reply_text("🎲 Welcome to the game! [Insert game logic here...]")

# --- Main Bot Setup ---

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("play", play))
    app.add_handler(CallbackQueryHandler(verify_tasks, pattern="^verify_tasks$"))
    app.add_handler(CallbackQueryHandler(confirm_twitter, pattern="^confirm_twitter$"))

    print("Bot running...")
    app.run_polling()

if __name__ == '__main__':
    main()
