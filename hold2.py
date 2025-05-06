
import os
import json
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes,
    ConversationHandler, CallbackQueryHandler, filters
)

# --- Configuration ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
TWITTER_HANDLE = os.getenv("TWITTER_HANDLE")
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
            "referrals": {},
            "tasks_done": False,
            "verified": False,
            "daily_bonus": "",
            "account": {},
            "withdrawals": []
        }
        save_data(data)
    return data[uid]

def update_user(user_id, new_data):
    data = load_data()
    data[str(user_id)] = new_data
    save_data(data)

# --- Menu Markup ---
def main_menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("💰 Balance"), KeyboardButton("📝 Tasks")],
        [KeyboardButton("🏦 Set Account"), KeyboardButton("💸 Withdraw")],
        [KeyboardButton("👥 Referrals"), KeyboardButton("📜 Withdrawals")],
        [KeyboardButton("🎁 Daily Bonus")]
    ], resize_keyboard=True)

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref = context.args[0] if context.args else None
    user_data = get_user(user.id)

    if ref and ref != str(user.id):
        referrer = get_user(ref)
        if str(user.id) not in referrer["referrals"]:
            referrer["referrals"][str(user.id)] = False
            update_user(ref, referrer)

    update_user(user.id, user_data)

    buttons = [
        [InlineKeyboardButton("✅ Join Telegram Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton("🐦 Follow Twitter", url=f"https://twitter.com/{TWITTER_HANDLE}")],
        [InlineKeyboardButton("🔍 Verify Tasks", callback_data="verify_tasks")]
    ]
    await update.message.reply_text(
        "👋 Welcome! Complete the tasks below to get started:\n"
        "- Join our Telegram channel\n"
        "- Follow us on Twitter\n\n"
        "Then tap 'Verify Tasks'.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def verify_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status not in ["member", "administrator", "creator"]:
            raise Exception("Not joined")
    except:
        await query.edit_message_text("❌ You're not in the Telegram channel. Please join and try again.")
        return

    keyboard = [[InlineKeyboardButton("✅ I've Followed on Twitter", callback_data="confirm_twitter")]]
    await query.edit_message_text(
        "Click below once you've followed us on Twitter.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def confirm_twitter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data = get_user(user_id)
    user_data["verified"] = True
    update_user(user_id, user_data)

    # reward referrer
    data = load_data()
    for uid, u in data.items():
        if str(user_id) in u.get("referrals", {}) and not u["referrals"][str(user_id)]:
            u["balance"] += 70
            u["referrals"][str(user_id)] = True
            update_user(uid, u)

    await query.edit_message_text("✅ Tasks verified. Use /play to continue.")

async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Main Menu:", reply_markup=main_menu())

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user(update.effective_user.id)
    await update.message.reply_text(f"💰 Your balance is ₦{user_data['balance']}")

# Tasks
async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 Complete these tasks:\n"
        "1. Join our channel: https://t.me/UtilizersChannel\n"
        "2. Post this message: 'Join Utilizers to earn ₦50 every 2 weeks. Try now!'\n"
        "3. Share this bot in 5 WhatsApp groups\n\n"
        "Send a screenshot showing proof of all tasks to receive ₦50."
    )
    return 1

async def receive_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user["tasks_done"]:
        user["tasks_done"] = True
        user["balance"] += 50
        update_user(user_id, user)
        await update.message.reply_text("✅ Screenshot received. ₦50 added to your balance.")
    else:
        await update.message.reply_text("You've already submitted your tasks.")
    return ConversationHandler.END

# Daily Bonus
async def daily_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    if user["daily_bonus"] == today:
        await update.message.reply_text("❌ You've already claimed your daily bonus.")
    else:
        user["balance"] += 25
        user["daily_bonus"] = today
        update_user(user_id, user)
        await update.message.reply_text("🎁 You received ₦25!")

# Referrals
async def referrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    total_refs = sum(1 for rewarded in user["referrals"].values() if rewarded)
    link = f"https://t.me/{context.bot.username}?start={user_id}"
    await update.message.reply_text(
        f"👥 Referrals: {total_refs}\n"
        f"💸 Referral Link:\n{link}"
    )

# Account Setup
ACCOUNT_BANK, ACCOUNT_NUMBER, ACCOUNT_NAME = range(3)

async def set_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    markup = ReplyKeyboardMarkup([["Opay", "Palmpay"]], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("🏦 Choose your bank:", reply_markup=markup)
    return ACCOUNT_BANK

async def get_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["bank"] = update.message.text
    await update.message.reply_text("🔢 Enter your account number:", reply_markup=ReplyKeyboardRemove())
    return ACCOUNT_NUMBER

async def get_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["number"] = update.message.text
    await update.message.reply_text("👤 Enter your account name:")
    return ACCOUNT_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    user["account"] = {
        "bank": context.user_data["bank"],
        "number": context.user_data["number"],
        "name": update.message.text
    }
    update_user(update.effective_user.id, user)
    await update.message.reply_text("✅ Account saved.")
    return ConversationHandler.END

# Withdrawals
WITHDRAW = range(1)

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💸 How much would you like to withdraw?")
    return WITHDRAW

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    try:
        amount = int(update.message.text)
        if amount < 1000:
            await update.message.reply_text("❌ Minimum is ₦1000.")
        elif amount > user["balance"]:
            await update.message.reply_text("❌ Not enough balance.")
        else:
            user["balance"] -= amount
            user["withdrawals"].append({"amount": amount, "time": datetime.utcnow().isoformat()})
            update_user(update.effective_user.id, user)
            await update.message.reply_text("✅ Withdrawal request submitted.")
    except:
        await update.message.reply_text("❌ Enter a valid number.")
    return ConversationHandler.END

async def withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if not user["withdrawals"]:
        await update.message.reply_text("📜 No withdrawals yet.")
    else:
        msg = "📜 Withdrawals:\n"
        for w in user["withdrawals"]:
            msg += f"₦{w['amount']} on {w['time']}\n"
        await update.message.reply_text(msg)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END

# --- Main ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("play", play))
    app.add_handler(CallbackQueryHandler(verify_tasks, pattern="^verify_tasks$"))
    app.add_handler(CallbackQueryHandler(confirm_twitter, pattern="^confirm_twitter$"))

    app.add_handler(MessageHandler(filters.Regex("💰 Balance"), balance))
    app.add_handler(MessageHandler(filters.Regex("📝 Tasks"), tasks))
    app.add_handler(MessageHandler(filters.Regex("🎁 Daily Bonus"), daily_bonus))
    app.add_handler(MessageHandler(filters.Regex("👥 Referrals"), referrals))
    app.add_handler(MessageHandler(filters.Regex("📜 Withdrawals"), withdrawals))

    account_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("🏦 Set Account"), set_account)],
        states={
            ACCOUNT_BANK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bank)],
            ACCOUNT_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_number)],
            ACCOUNT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    withdraw_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("💸 Withdraw"), withdraw)],
        states={WITHDRAW: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_amount)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    screenshot_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.PHOTO, receive_screenshot)],
        states={},
        fallbacks=[]
    )

    app.add_handler(account_conv)
    app.add_handler(withdraw_conv)
    app.add_handler(screenshot_conv)

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()

