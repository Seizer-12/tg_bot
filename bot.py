# bot.py

import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
TWITTER_HANDLE = os.getenv("TWITTER_HANDLE")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store verified users
verified_users = set()

# --- Task Menu Keyboard ---
def task_menu():
    keyboard = [
        [InlineKeyboardButton("✅ Join Telegram Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton("🐦 Follow Twitter", url=f"https://twitter.com/{TWITTER_HANDLE}")],
        [InlineKeyboardButton("📱 Join Whatsapp Group", url="https://chat.whatsapp.com/KyBPEZKLjAZ8JMgFt9KMft")],
        [InlineKeyboardButton("📢 Join Whatsapp Channel", url="https://whatsapp.com/channel/0029VbAXEgUFy72Ich07Z53o")],
        [InlineKeyboardButton("🔍 Verify Tasks", callback_data="verify_tasks")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Start Command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎯 To submit your entry, complete the following tasks:\n\n"
        f"1. Join our Telegram channel\n"
        f"2. Follow our Twitter account ({TWITTER_HANDLE})\n"
        f"3. Join our WhatsApp group\n"
        f"4. Join our WhatsApp channel\n\n"
        "After that, click the button below to verify!",
        reply_markup=task_menu()
    )

# --- Verify Tasks ---
async def verify_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    try:
        # Fetch the user's status in the channel
        chat_member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        user_status = chat_member.status

        # Check if the user is a member
        if user_status in ["member", "administrator", "creator"]:
            verified_users.add(user_id)
            await query.edit_message_text(
                "✅ Congratulations! You have successfully completed all tasks.\n\n"
                "You can now use /play to join"
            )
        else:
            raise Exception("User not a proper member")

    except Exception as e:
        logger.error(f"Verification failed for user {user_id}: {e}")
        await query.edit_message_text(
            "❌ You have not completed all the tasks in the menu yet.\n\n"
            "Please complete the task and try again:",
            reply_markup=task_menu()
        )

# --- Confirm Twitter ---
async def confirm_twitter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    verified_users.add(user_id)

    await query.edit_message_text(
        "✅ Details submitted successfully. You can now use /play to start the game!"
    )

"""
# --- Play Command ---
async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    username = query.from_user.username
    user_id = update.effective_user.id
    if user_id not in verified_users:
        await update.message.reply_text(
            "❌ You must complete the tasks first. Use /start to begin."
        )
        return
    await update.message.reply_text(f"Entry successfully submitted for user {query.from_user.username}")
"""

def play_menu():
    keyboard = [
        [InlineKeyboardButton("💰 Points Balance", callback_data="menu_points")],
        [InlineKeyboardButton("🤝 Referral", callback_data="menu_referral")],
        [InlineKeyboardButton("📊 Position", callback_data="menu_position")],
        [InlineKeyboardButton("📌 Tasks", callback_data="menu_tasks")],
        [InlineKeyboardButton("📤 Verify Tasks Completion", callback_data="menu_verify_tasks")],
        [InlineKeyboardButton("🚀 Upgrade to Ambassador", callback_data="menu_upgrade")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Play Command ---
async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in verified_users:
        await update.message.reply_text("❌ You must complete the tasks first. Use /start to begin.")
        return

    await update.message.reply_text(
        "🎮 Welcome to the game menu. Choose an option below to continue:",
        reply_markup=play_menu()
    )

# --- Menu Handlers ---

async def menu_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    user = update.callback_query.from_user
    points = 100  # Replace with dynamic user value
    await update.callback_query.edit_message_text(f"💰 *Your current points:* `{points}`", parse_mode=ParseMode.MARKDOWN)

async def menu_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    user = update.callback_query.from_user
    referral_link = f"https://t.me/{context.bot.username}?start={user.id}"
    referrals = 5  # Replace with real tracking
    await update.callback_query.edit_message_text(
        f"🤝 *Your Referral Link:*\n{referral_link}\n\n"
        f"📈 Total Referrals: {referrals}",
        parse_mode=ParseMode.MARKDOWN
    )

async def menu_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    position = 1065 + 1  # Simulate example
    await update.callback_query.edit_message_text(f"📊 Your current leaderboard position is: *{position}*", parse_mode=ParseMode.MARKDOWN)

async def menu_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    task_list = (
        "📌 *Available Tasks:*\n\n"
        "1. Join our Telegram group: https://t.me/examplegroup\n"
        "2. Follow us on Twitter: https://twitter.com/example\n"
        "3. Like our Instagram page: https://instagram.com/example\n\n"
        "_Complete all tasks before verifying_ ✅"
    )
    await update.callback_query.edit_message_text(task_list, parse_mode=ParseMode.MARKDOWN)

async def menu_verify_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    warning = (
        "📤 *Upload Screenshots of Completed Tasks*\n\n"
        "Please send screenshots of your completed tasks here.\n"
        "⚠️ All submissions will be reviewed manually. Submitting fake proofs may lead to disqualification."
    )
    await update.callback_query.edit_message_text(warning, parse_mode=ParseMode.MARKDOWN)

async def menu_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    criteria = (
        "🚀 *Upgrade to Ambassador*\n\n"
        "To become an ambassador, you must:\n"
        "• Refer at least 50 users\n"
        "• Complete all available tasks\n"
        "• Maintain an active presence in the group\n\n"
        "If you meet these criteria, reply here to apply!"
    )
    await update.callback_query.edit_message_text(criteria, parse_mode=ParseMode.MARKDOWN)


# --- Run Bot ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("play", play))
    app.add_handler(CallbackQueryHandler(verify_tasks, pattern="^verify_tasks$"))
    app.add_handler(CallbackQueryHandler(confirm_twitter, pattern="^confirm_twitter$"))

    app.add_handler(CallbackQueryHandler(menu_points, pattern="^menu_points$"))
    app.add_handler(CallbackQueryHandler(menu_referral, pattern="^menu_referral$"))
    app.add_handler(CallbackQueryHandler(menu_position, pattern="^menu_position$"))
    app.add_handler(CallbackQueryHandler(menu_tasks, pattern="^menu_tasks$"))
    app.add_handler(CallbackQueryHandler(menu_verify_tasks, pattern="^menu_verify_tasks$"))
    app.add_handler(CallbackQueryHandler(menu_upgrade, pattern="^menu_upgrade$"))


    app.run_polling()

if __name__ == "__main__":
    main()
