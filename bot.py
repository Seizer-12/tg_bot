# bot.py

import os
import json
import logging
from datetime import datetime
import urllib.parse
from telegram.constants import ParseMode
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application, ConversationHandler, ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
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
        f"🎯 WELCOME {user.username} \n\nTo participate in the campaign, complete the tasks below:\n\n\n"
        "Click the Verify Tasks button below to verify!",
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
    user_data["tasks_completed"] = True
    update_user(user_id, user_data)

    await query.edit_message_text("✅ You're verified. \n\nTap or type /play to begin!")


# COMMAND: /play
@dp.message_handler(commands=["play"])
async def play_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = get_user(user_id)

    if not user_data.get("verified"):
        await update.message.reply_text("❌ You need to verify before playing.")
        return

    keyboard = [
        [KeyboardButton("📊 Balance"), KeyboardButton("📝 Tasks")],
        [KeyboardButton("🏦 Set Account"), KeyboardButton("👥 Referral")],
        [KeyboardButton("💸 Withdraw"), KeyboardButton("📁 Withdrawals")],
        [KeyboardButton("🎯 Level")]
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Welcome to the Utilizers Bot Menu! Choose an option below:",
        reply_markup=reply_markup
    )

# balance
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    bal = user.get("balance", 0)
    await update.message.reply_text(f"💰 Your balance: ₦{bal}")

# tasks
async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user.get("tasks_completed"):
        user["tasks_completed"] = True
        user["balance"] = user.get("balance", 0) + 50
        user["earnings"] = user.get("earnings", 0) + 50
        update_user(user_id, user)
        await update.message.reply_text("✅ Tasks completed. ₦50 credited!")
    else:
        await update.message.reply_text("✔️ You have already completed your tasks.")

# Referral
async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    referrals = user.get("referrals", [])
    link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
    await update.message.reply_text(
        f"👥 Your referral link: {link}\nTotal referrals: {len(referrals)}"
    )

# Level
async def level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    referrals = len(user.get("referrals", []))
    earnings = user.get("earnings", 0)
    level = "Level 1 (Novice)"
    if referrals >= 100 and earnings >= 10000:
        level = "Level 5 (Guru)"
    elif referrals >= 75 and earnings >= 7500:
        level = "Level 4 (Master)"
    elif referrals >= 50 and earnings >= 5000:
        level = "Level 3 (Pro)"
    elif referrals >= 20 and earnings >= 2500:
        level = "Level 2 (Amateur)"

    await update.message.reply_text(f"🔺 Your Level: {level}")

# Withdrawal
WITHDRAW_AMOUNT = 0
WITHDRAW = range(1)

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💸 How much would you like to withdraw?")
    return WITHDRAW

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    try:
        amount = int(update.message.text)
        if amount < 1000:
            await update.message.reply_text("❌ Minimum withdrawal is ₦1000")
        elif amount > user.get("balance", 0):
            await update.message.reply_text("❌ Insufficient balance")
        else:
            user["balance"] -= amount
            user["withdrawals"] = user.get("withdrawals", []) + [
                {"amount": amount, "timestamp": datetime.utcnow().isoformat()}
            ]
            update_user(user_id, user)
            await update.message.reply_text("✅ Withdrawal request submitted.")
    except ValueError:
        await update.message.reply_text("❌ Enter a valid number")
    return ConversationHandler.END

# Withdrawal records
async def withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    records = user.get("withdrawals", [])
    total = sum(r["amount"] for r in records)
    text = f"📜 Total Earnings: ₦{user.get('earnings', 0)}\nWithdrawals:"
    for r in records:
        text += f"\n- ₦{r['amount']} on {r['timestamp'][:10]}"
    await update.message.reply_text(text)


# Account setting
ACCOUNT_BANK, ACCOUNT_NUMBER, ACCOUNT_NAME = range(3)

async def set_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    markup = ReplyKeyboardMarkup([
        ["Opay", "Palmpay"]
    ], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("🏦 Choose your bank:", reply_markup=markup)
    return ACCOUNT_BANK

async def get_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["bank"] = update.message.text
    await update.message.reply_text("🔢 Enter your account number:", reply_markup=ReplyKeyboardRemove())
    return ACCOUNT_NUMBER

async def get_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["number"] = update.message.text
    await update.message.reply_text("🧾 Enter your account name:")
    return ACCOUNT_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    user["account"] = {
        "bank": context.user_data["bank"],
        "number": context.user_data["number"],
        "name": update.message.text
    }
    update_user(user_id, user)
    await update.message.reply_text("✅ Account info saved.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Canceled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# --- Run Bot ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(confirm_twitter, pattern="^confirm_twitter$"))
    app.add_handler(CommandHandler("play", play))
    app.add_handler(CallbackQueryHandler(verify_tasks, pattern="^verify_tasks$"))

    app.add_handler(CommandHandler("play", play))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("tasks", tasks))
    app.add_handler(CommandHandler("referral", referral))
    app.add_handler(CommandHandler("withdrawals", withdrawals))
    app.add_handler(CommandHandler("level", level))


    withdraw_conv = ConversationHandler(
        entry_points=[CommandHandler("withdraw", withdraw)],
        states={WITHDRAW: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_amount)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    account_conv = ConversationHandler(
        entry_points=[CommandHandler("set_account", set_account)],
        states={
            ACCOUNT_BANK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bank)],
            ACCOUNT_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_number)],
            ACCOUNT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(withdraw_conv)
    app.add_handler(account_conv)


    app.run_polling()

if __name__ == "__main__":
    main()
