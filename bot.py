import json
import os
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler, CallbackQueryHandler
)

# Load .env variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
TWITTER_HANDLE = os.getenv("TWITTER_HANDLE")
BOT_USERNAME = "UtilizersBot"
DATA_FILE = "user_data.json"

# --- Data Functions ---
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
    user_id = str(user_id)
    if user_id not in data:
        data[user_id] = {
            "balance": 0,
            "referrals": {},
            "tasks_done": False,
            "daily_bonus": "",
            "account": {},
            "withdrawals": [],
            "verified": False,
            "total_earned": 0
        }
        save_data(data)
    return data[user_id]

def update_user(user_id, user_data):
    data = load_data()
    data[str(user_id)] = user_data
    save_data(data)

# --- Menus ---
def main_menu():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("💰 Balance"), KeyboardButton("📝 Tasks")],
            [KeyboardButton("🏦 Set Account"), KeyboardButton("👥 Referral")],
            [KeyboardButton("💸 Withdraw"), KeyboardButton("📜 Withdrawals")],
            [KeyboardButton("🏅 Level"), KeyboardButton("🎁 Daily Bonus")]
        ],
        resize_keyboard=True
    )

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user(user.id)
    ref = context.args[0] if context.args else None

    if ref and ref != str(user.id):
        referrer = get_user(ref)
        if str(user.id) not in referrer['referrals']:
            referrer['referrals'][str(user.id)] = {'user_id': user.id, 'rewarded': False}
            update_user(ref, referrer)

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

async def confirm_twitter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data = get_user(user_id)
    user_data["verified"] = True  # Fixed key name from "verified_user"
    update_user(user_id, user_data)

    await query.edit_message_text("✅ You're verified. \n\nTap or type /play to begin!")

async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user(user.id)
    user_data['verified'] = True
    update_user(user.id, user_data)

    await update.message.reply_text(
        "Welcome! Use the buttons below to navigate.",
        reply_markup=main_menu()
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)

    reward_count = 0
    for ref_id in user_data["referrals"].keys():
        if not user_data['referrals'][ref_id]['rewarded']:
            ref_user = get_user(ref_id)
            if ref_user['verified'] and ref_user['tasks_done']:
                user_data["referrals"][ref_id]['rewarded'] = True
                user_data["balance"] += 70
                user_data["total_earned"] += 70
                reward_count += 1
    if reward_count > 0:
        update_user(user_id, user_data)

    await update.message.reply_text(f"💰 Your balance: ₦{user_data['balance']}")

# Task conversation
TASK_SCREENSHOT = 1

async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 Complete these tasks:\n"
        "1. Follow https://t.me/UtilizersChannel\n"
        "2. Post: 'Join Utilizers to earn ₦50 every 2 weeks. Try now!'\n"
        "3. Share the bot to 5 WhatsApp groups\n\n"
        "✅ After completing, send a screenshot for verification."
    )
    return TASK_SCREENSHOT

async def receive_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user(user.id)

    if not user_data["tasks_done"]:
        user_data["tasks_done"] = True
        user_data["balance"] += 50
        user_data["total_earned"] += 50
        update_user(user.id, user_data)
        await update.message.reply_text("✅ Screenshot received. ₦50 has been added to your balance.")
    else:
        await update.message.reply_text("✅ You've already completed the tasks.")
    return ConversationHandler.END

# Account setup conversation
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

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user(user.id)
    count = 0
    for ref_id in user_data["referrals"].keys():
        ref_user = get_user(ref_id)
        if ref_user["verified"] and ref_user["tasks_done"] and not user_data['referrals'][ref_id]['rewarded']:
            user_data['referrals'][ref_id]['rewarded'] = True
            count += 1
    update_user(user.id, user_data)
    reward = count * 70
    link = f"https://t.me/{context.bot.username}?start={user.id}"
    await update.message.reply_text(
        f"👥 Referrals: {len(user_data['referrals'])}\n💵 Earnings: ₦{user_data['balance']}\n\n🔗 Referral Link:\n{link}"
    )

# Withdrawal
WITHDRAW = 1

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
            user["withdrawals"].append({
                "amount": amount,
                "date": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            })
            update_user(user_id, user)
            await update.message.reply_text("✅ Withdrawal request submitted.")
    except ValueError:
        await update.message.reply_text("❌ Enter a valid number")
    return ConversationHandler.END

async def withdrawal_records(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user(update.effective_user.id)
    history = user_data["withdrawals"]
    total = user_data["total_earned"]
    if not history:
        await update.message.reply_text("📜 No withdrawals yet.")
    else:
        msg = "📜 Withdrawal Records:\n"
        for h in history:
            msg += f"• ₦{h['amount']} on {h['date']}\n"
        msg += f"\n💰 Total Earned: ₦{total}"
        await update.message.reply_text(msg)

async def level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user(update.effective_user.id)
    count = sum(1 for ref_id in user_data["referrals"]
                if get_user(ref_id)["verified"] and get_user(ref_id)["tasks_done"])
    total = user_data["total_earned"]
    level = "Novice"
    if count >= 100 and total >= 10000:
        level = "Guru"
    elif count >= 75 and total >= 7500:
        level = "Master"
    elif count >= 50 and total >= 5000:
        level = "Pro"
    elif count >= 20 and total >= 2500:
        level = "Amateur"
    await update.message.reply_text(f"🏅 Your Level: {level}")

async def daily_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user(update.effective_user.id)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    if user_data["daily_bonus"] == today:
        await update.message.reply_text("❌ Bonus already claimed today.")
    else:
        user_data["balance"] += 25
        user_data["total_earned"] += 25
        user_data["daily_bonus"] = today
        update_user(update.effective_user.id, user_data)
        await update.message.reply_text("🎁 You received ₦25 daily bonus!")

# --- App Setup ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("play", play))
    app.add_handler(CallbackQueryHandler(confirm_twitter, pattern="^confirm_twitter$"))
    app.add_handler(CallbackQueryHandler(verify_tasks, pattern="^verify_tasks$"))

    app.add_handler(MessageHandler(filters.Regex("💰 Balance"), balance))
    app.add_handler(MessageHandler(filters.Regex("📝 Tasks"), tasks))
    app.add_handler(MessageHandler(filters.Regex("🏦 Set Account"), set_account))
    app.add_handler(MessageHandler(filters.Regex("👥 Referral"), referral))
    app.add_handler(MessageHandler(filters.Regex("💸 Withdraw"), withdraw))
    app.add_handler(MessageHandler(filters.Regex("📜 Withdrawals"), withdrawal_records))
    app.add_handler(MessageHandler(filters.Regex("🏅 Level"), level))
    app.add_handler(MessageHandler(filters.Regex("🎁 Daily Bonus"), daily_bonus))

    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.PHOTO & ~filters.COMMAND, receive_screenshot)],
        states={TASK_SCREENSHOT: [MessageHandler(filters.PHOTO, receive_screenshot)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    ))

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("withdraw", withdraw)],
        states={WITHDRAW: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_amount)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    ))

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("set_account", set_account)],
        states={
            ACCOUNT_BANK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bank)],
            ACCOUNT_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_number)],
            ACCOUNT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    ))

    print("✅ Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
