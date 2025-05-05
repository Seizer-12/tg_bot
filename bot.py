import json
import os
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler, CallbackQueryHandler
)

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
            "referrals": [],
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

    user = update.effective_user
    user_data = get_user(user.id)

    if ref and ref != str(user.id):
        referrer = get_user(ref)
        if user.id not in referrer['referrals']:
            referrer['referrals'].append(user.id)
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


# --- Confirm Twitter ---
async def confirm_twitter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data = get_user(user_id)
    user_data["verified_user"] = True
    update_user(user_id, user_data)

    keyboard = [[InlineKeyboardButton("Play", callback_data="play")]]
    await query.edit_message_text("✅ You're verified. \n\nTap or type /play to begin!", reply_markup=InlineKeyboardMarkup(keyboard))


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
    user_data = get_user(update.effective_user.id)
    await update.message.reply_text(f"💰 Your balance: ₦{user_data['balance']}")

# Task verification (asks for screenshot)
async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 Complete these tasks:\n"
        "1. Follow https://t.me/UtilizersChannel\n"
        "2. Post: 'Join Utilizers to earn ₦50 every 2 weeks. Try now!'\n"
        "3. Share the bot to 5 WhatsApp groups\n\n"
        "✅ After completing, send a screenshot for verification."
    )
    return 1

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

# Set Account
async def set_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏦 Enter your bank name (Opay or Palmpay):")
    context.user_data["awaiting"] = "bank_name"

async def handle_account_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user(update.effective_user.id)
    state = context.user_data.get("awaiting")

    if state == "bank_name":
        bank = update.message.text.strip().lower()
        if bank not in ["opay", "palmpay"]:
            await update.message.reply_text("❌ Invalid bank. Choose Opay or Palmpay.")
            return
        context.user_data["bank_name"] = bank
        context.user_data["awaiting"] = "account_number"
        await update.message.reply_text("🔢 Enter your account number:")
    elif state == "account_number":
        acc_num = update.message.text.strip()
        if not acc_num.isdigit() or len(acc_num) != 10:
            await update.message.reply_text("❌ Invalid account number. Must be 10 digits.")
            return
        context.user_data["account_number"] = acc_num
        context.user_data["awaiting"] = "account_name"
        await update.message.reply_text("👤 Enter your account name:")
    elif state == "account_name":
        acc_name = update.message.text.strip()
        user_data["account"] = {
            "bank": context.user_data["bank_name"],
            "number": context.user_data["account_number"],
            "name": acc_name
        }
        update_user(update.effective_user.id, user_data)
        context.user_data.clear()
        await update.message.reply_text("✅ Account saved successfully!")

# Referral
async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user(user.id)
    count = 0
    for ref_id in user_data["referrals"]:
        ref_user = get_user(ref_id)
        if ref_user["verified"] and ref_user["tasks_done"]:
            count += 1
    reward = count * 70
    link = f"https://t.me/{context.bot.username}?start={user.id}"
    await update.message.reply_text(
        f"👥 Referrals: {count}\n💵 Earnings: ₦{reward}\n\n🔗 Referral Link:\n{link}"
    )

# Withdrawals
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💸 Enter the amount to withdraw (min ₦1000):")
    return 1

async def receive_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount = int(update.message.text)
    user_id = update.effective_user.id
    user_data = get_user(user_id)

    if amount > user_data["balance"]:
        await update.message.reply_text("❌ Insufficient balance.")
    elif amount < 1000:
        await update.message.reply_text("❌ Minimum withdrawal is ₦1000.")
    elif not user_data.get("account"):
        await update.message.reply_text("❌ Set your account details first using '🏦 Set Account'.")
    else:
        user_data["balance"] -= amount
        user_data["withdrawals"].append({
            "amount": amount,
            "date": datetime.utcnow().strftime("%Y-%m-%d")
        })
        update_user(user_id, user_data)
        await update.message.reply_text("✅ Withdrawal request submitted!")

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

# Levels
async def level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user(update.effective_user.id)
    count = 0
    for ref_id in user_data["referrals"]:
        ref_user = get_user(ref_id)
        if ref_user["verified"] and ref_user["tasks_done"]:
            count += 1

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

# Daily Bonus
async def daily_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user(update.effective_user.id)
    if user_data["daily_bonus"] == datetime.utcnow().strftime("%Y-%m-%d"):
        await update.message.reply_text("❌ Bonus already claimed today.")
    else:
        user_data["balance"] += 25
        user_data["total_earned"] += 25
        user_data["daily_bonus"] = datetime.utcnow().strftime("%Y-%m-%d")
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

    # Conversations
    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.PHOTO & ~filters.COMMAND, receive_screenshot)],
        states={},
        fallbacks=[]
    ))

    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("🏦 Set Account"), set_account)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_bank)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_account_number)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_account_name)],
        },
        fallbacks=[]
    ))

    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("💸 Withdraw"), withdraw)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_withdraw)]
        },
        fallbacks=[]
    ))

    print("✅ Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
