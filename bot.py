# Regenerating the Telegram bot script with updated logic for:
# - Referral: earnings added directly to balance
# - Withdrawal: sends request to admin for processing
# - Account setup: full process saved correctly

import json
import os
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler, CallbackQueryHandler
)

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
TWITTER_HANDLE = os.getenv("TWITTER_HANDLE")
ADMIN_ID = int(os.getenv("ADMIN_ID"))  # Set this to your Telegram user ID
DATA_FILE = "user_data.json"

# --- Helper Functions ---
def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({}, f)
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_user(user_id):
    data = load_data()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "balance": 0,
            "referrals": [],
            "tasks_done": False,
            "verified": False,
            "account": {},
            "withdrawals": []
        }
        save_data(data)
    return data[uid]

def update_user(user_id, user_data):
    data = load_data()
    data[str(user_id)] = user_data
    save_data(data)

# --- Menus ---
def main_menu():
    return ReplyKeyboardMarkup([
        ["💰 Balance", "📝 Tasks"],
        ["🏦 Set Account", "👥 Referral"],
        ["💸 Withdraw", "📜 Withdrawals"],
        ["🏅 Level", "🎁 Daily Bonus"]
    ], resize_keyboard=True)

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user(user.id)

    ref = context.args[0] if context.args else None
    if ref and ref != str(user.id):
        ref_user = get_user(ref)
        if user.id not in ref_user["referrals"]:
            ref_user["referrals"].append(user.id)
            ref_user["balance"] += 70
            update_user(ref, ref_user)

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
        f"🎯 Welcome {user.first_name or user.username}!\n\n"
        "To begin, please complete the tasks below then tap Verify Tasks.",
        reply_markup=reply_markup
    )

# --- Task Verification ---
async def verify_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status not in ["member", "administrator", "creator"]:
            raise Exception("Not joined")
    except Exception:
        await query.edit_message_text("❌ You haven't joined the Telegram channel.")
        return

    keyboard = [[InlineKeyboardButton("✅ I Followed on Twitter", callback_data="confirm_twitter")]]
    await query.edit_message_text(
        "👀 Twitter verification is manual.\n\n"
        "Click below once you’ve followed.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def confirm_twitter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ Twitter follow confirmed.\nSend a screenshot showing all tasks completed.")
    return

# --- Tasks + Screenshot Verification ---
async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 Complete the following:\n"
        "1. Join our Telegram channel\n"
        "2. Follow our Twitter\n"
        "3. Share the bot to 5 WhatsApp groups\n"
        "4. Post this: 'Join Utilizers & earn ₦50 every 2 weeks!'\n\n"
        "📸 Then send a screenshot here to verify."
    )

async def receive_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user(user.id)

    if not user_data["tasks_done"]:
        user_data["tasks_done"] = True
        user_data["balance"] += 50
        user_data["verified"] = True
        update_user(user.id, user_data)
        await update.message.reply_text("✅ Screenshot received and verified. ₦50 added to your balance.")
    else:
        await update.message.reply_text("✅ You’ve already completed tasks.")

# --- Balance ---
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user(update.effective_user.id)
    await update.message.reply_text(f"💰 Your current balance: ₦{user_data['balance']}")

# --- Set Account ---
ACCOUNT_BANK, ACCOUNT_NUMBER, ACCOUNT_NAME = range(3)

async def set_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    markup = ReplyKeyboardMarkup([["Opay", "Palmpay"]], resize_keyboard=True, one_time_keyboard=True)
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
    await update.message.reply_text("✅ Account saved successfully.")
    return ConversationHandler.END

# --- Referral ---
async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    link = f"https://t.me/{context.bot.username}?start={user_id}"
    user_data = get_user(user_id)
    ref_count = len(user_data["referrals"])
    await update.message.reply_text(
        f"👥 Referrals: {ref_count}\n"
        f"🔗 Your referral link:\n{link}"
    )

# --- Withdrawals ---
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
            await update.message.reply_text("❌ Minimum is ₦1000.")
        elif amount > user["balance"]:
            await update.message.reply_text("❌ Insufficient balance.")
        elif not user["account"]:
            await update.message.reply_text("⚠️ Please set your account details first.")
        else:
            user["balance"] -= amount
            withdrawal = {
                "amount": amount,
                "date": datetime.utcnow().strftime("%Y-%m-%d"),
                "account": user["account"]
            }
            user["withdrawals"].append(withdrawal)
            update_user(user_id, user)

            # Notify admin
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    f"📥 New withdrawal request:\n\n"
                    f"👤 User: @{update.effective_user.username} ({user_id})\n"
                    f"💵 Amount: ₦{amount}\n"
                    f"🏦 Bank: {user['account']['bank']}\n"
                    f"🔢 Number: {user['account']['number']}\n"
                    f"🧾 Name: {user['account']['name']}"
                )
            )

            await update.message.reply_text("✅ Withdrawal request sent for processing.")
    except ValueError:
        await update.message.reply_text("❌ Enter a valid amount.")
    return ConversationHandler.END

# --- Withdrawal History ---
async def withdrawal_records(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user(update.effective_user.id)
    history = user_data["withdrawals"]
    if not history:
        await update.message.reply_text("📜 No withdrawals yet.")
    else:
        msg = "📜 Your Withdrawals:\n"
        for h in history:
            msg += f"• ₦{h['amount']} on {h['date']}\n"
        await update.message.reply_text(msg)

# --- Level ---
async def level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user(update.effective_user.id)
    ref_count = len(user_data["referrals"])
    earned = user_data["balance"] + sum(w["amount"] for w in user_data["withdrawals"])
    level = "Novice"
    if ref_count >= 100: level = "Guru"
    elif ref_count >= 50: level = "Pro"
    elif ref_count >= 20: level = "Amateur"

    await update.message.reply_text(f"🏅 Your Level: {level}")

# --- Bonus ---
async def daily_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    if user.get("daily_bonus") == today:
        await update.message.reply_text("❌ Already claimed today.")
    else:
        user["balance"] += 25
        user["daily_bonus"] = today
        update_user(update.effective_user.id, user)
        await update.message.reply_text("🎁 ₦25 daily bonus added!")

# --- Bot Entry ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("play", tasks))
    app.add_handler(CallbackQueryHandler(verify_tasks, pattern="^verify_tasks$"))
    app.add_handler(CallbackQueryHandler(confirm_twitter, pattern="^confirm_twitter$"))

    app.add_handler(MessageHandler(filters.Regex("💰 Balance"), balance))
    app.add_handler(MessageHandler(filters.Regex("📝 Tasks"), tasks))
    app.add_handler(MessageHandler(filters.PHOTO, receive_screenshot))
    app.add_handler(MessageHandler(filters.Regex("🏦 Set Account"), set_account))
    app.add_handler(MessageHandler(filters.Regex("👥 Referral"), referral))
    app.add_handler(MessageHandler(filters.Regex("💸 Withdraw"), withdraw))
    app.add_handler(MessageHandler(filters.Regex("📜 Withdrawals"), withdrawal_records))
    app.add_handler(MessageHandler(filters.Regex("🏅 Level"), level))
    app.add_handler(MessageHandler(filters.Regex("🎁 Daily Bonus"), daily_bonus))

    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw)],
        states={WITHDRAW: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_amount)]},
        fallbacks=[]
    ))

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("set_account", set_account)],
        states={
            ACCOUNT_BANK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bank)],
            ACCOUNT_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_number)],
            ACCOUNT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        },
        fallbacks=[]
    ))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
