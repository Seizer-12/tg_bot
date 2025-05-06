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
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # Add this to your .env file

# Conversion rate (points to Naira)
POINTS_TO_NAIRA = 1  # 1 point = 1 Naira

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_FILE = "user_data.json"
WITHDRAWAL_FILE = "withdrawals.json"

# --- Utility Functions ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_withdrawals():
    if os.path.exists(WITHDRAWAL_FILE):
        with open(WITHDRAWAL_FILE, "r") as f:
            return json.load(f)
    return {}

def save_withdrawals(data):
    with open(WITHDRAWAL_FILE, "w") as f:
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

def calculate_level(user_data):
    referrals = user_data.get("referrals", 0)
    total_earned = user_data.get("total_earned", 0)
    
    if referrals >= 100 and total_earned >= 10000:
        return ("Guru", 5)
    elif referrals >= 75 and total_earned >= 7500:
        return ("Master", 4)
    elif referrals >= 50 and total_earned >= 5000:
        return ("Pro", 3)
    elif referrals >= 20 and total_earned >= 2500:
        return ("Amateur", 2)
    else:
        return ("Novice", 1)

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
                    "🎯 You just referred a user and got 25 Points..."
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

async def confirm_twitter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data = get_user(user_id)
    
    # Mark tasks as completed
    user_data["completed_initial_tasks"] = True
    user_data["verified_user"] = True
    user_data["points"] = user_data.get("points", 0) + 50  # 50 Naira for completing tasks
    
    update_user(user_id, user_data)

    await query.edit_message_text(
        "✅ You're verified and have earned ₦50 for completing the tasks!\n\n"
        "Use the following commands:\n"
        "/balance - Check your balance\n"
        "/tasks - View available tasks\n"
        "/setaccount - Set your payment details\n"
        "/referral - Get your referral link\n"
        "/withdraw - Request a withdrawal\n"
        "/withdrawals - View your withdrawal history\n"
        "/level - Check your current level"
    )

# --- Command Handlers ---
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    if not user_data.get("verified_user"):
        await update.message.reply_text("❌ Please complete verification first using /start")
        return
    
    balance_naira = user_data.get("points", 0) * POINTS_TO_NAIRA
    await update.message.reply_text(f"💰 Your current balance: ₦{balance_naira:,.2f}")

async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    if not user_data.get("verified_user"):
        await update.message.reply_text("❌ Please complete verification first using /start")
        return
    
    bot_link = "https://t.me/UtilizersBot"
    task_link1 = f"https://twitter.com/{TWITTER_HANDLE}"
    post_text = f"I just joined the Utilizers, and you should too! \n\nGet picked as one of the 1,000 verified testers of THE UTILIZERS beta platform and earn $50 every 2 weeks for FREE. \n\nAct fast, spots are limited!\n\n{bot_link}"
    encoded_text = urllib.parse.quote(post_text)
    task_link2 = f"https://twitter.com/intent/tweet?text={encoded_text}"
    task_link3 = f"https://wa.me/?text={encoded_text}"

    message = (
        f"📝 Available Tasks (Complete all to earn ₦50):\n\n"
        f"1. Follow <a href='{task_link1}'>Utilizer01 on Twitter</a>\n\n"
        f"2. <a href='{task_link2}'>Post on X (Twitter)</a>\n\n"
        f"3. <a href='{task_link3}'>Share to 5 WhatsApp groups and your status</a>\n\n"
        "After completing all tasks, upload screenshots using /verifytasks"
    )
    
    await update.message.reply_text(message, parse_mode=ParseMode.HTML)

async def set_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    if not user_data.get("verified_user"):
        await update.message.reply_text("❌ Please complete verification first using /start")
        return
    
    # Check if user already has account details
    if user_data.get("account_set"):
        await update.message.reply_text(
            f"Your current account details:\n"
            f"Bank: {user_data.get('bank_name')}\n"
            f"Account Number: {user_data.get('account_number')}\n"
            f"Account Name: {user_data.get('account_name')}\n\n"
            "To update, use /setaccount again."
        )
        return
    
    # Create keyboard for bank selection
    keyboard = [
        [InlineKeyboardButton("OPay", callback_data="bank_opay")],
        [InlineKeyboardButton("PalmPay", callback_data="bank_palmpay")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Please select your bank:",
        reply_markup=reply_markup
    )
    context.user_data["awaiting_bank"] = True

async def bank_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    bank = "OPay" if query.data == "bank_opay" else "PalmPay"
    context.user_data["selected_bank"] = bank
    context.user_data["awaiting_bank"] = False
    context.user_data["awaiting_account_number"] = True
    
    await query.edit_message_text(f"You selected {bank}. Now please send your account number.")

async def handle_account_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    account_number = update.message.text
    
    if not context.user_data.get("awaiting_account_number"):
        return
    
    if not account_number.isdigit() or len(account_number) < 10:
        await update.message.reply_text("❌ Invalid account number. Please enter a valid 10-digit account number.")
        return
    
    context.user_data["account_number"] = account_number
    context.user_data["awaiting_account_number"] = False
    context.user_data["awaiting_account_name"] = True
    
    await update.message.reply_text("Now please send your account name as it appears on your bank records.")

async def handle_account_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    account_name = update.message.text
    
    if not context.user_data.get("awaiting_account_name"):
        return
    
    if len(account_name.strip()) < 2:
        await update.message.reply_text("❌ Invalid account name. Please enter your full name.")
        return
    
    # Save all account details
    user_data = get_user(user_id)
    user_data["bank_name"] = context.user_data["selected_bank"]
    user_data["account_number"] = context.user_data["account_number"]
    user_data["account_name"] = account_name
    user_data["account_set"] = True
    update_user(user_id, user_data)
    
    # Clear context
    context.user_data.clear()
    
    await update.message.reply_text(
        f"✅ Account details saved successfully!\n\n"
        f"Bank: {user_data['bank_name']}\n"
        f"Account Number: {user_data['account_number']}\n"
        f"Account Name: {user_data['account_name']}"
    )

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    if not user_data.get("verified_user"):
        await update.message.reply_text("❌ Please complete verification first using /start")
        return
    
    ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
    count = user_data.get("referrals", 0)
    await update.message.reply_text(
        f"👥 Your referral link:\n{ref_link}\n\n"
        f"Total referrals: {count}\n"
        f"Earn ₦70 for each successful referral (when they complete initial tasks)"
    )

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    if not user_data.get("verified_user"):
        await update.message.reply_text("❌ Please complete verification first using /start")
        return
    
    if not user_data.get("account_set"):
        await update.message.reply_text("❌ Please set your account details first using /setaccount")
        return
    
    balance_naira = user_data.get("points", 0) * POINTS_TO_NAIRA
    
    if balance_naira < 1000:
        await update.message.reply_text(f"❌ Minimum withdrawal is ₦1,000. Your current balance is ₦{balance_naira:,.2f}")
        return
    
    await update.message.reply_text(
        f"💰 Your current balance: ₦{balance_naira:,.2f}\n"
        f"Minimum withdrawal: ₦1,000\n\n"
        "Please enter the amount you want to withdraw:"
    )
    context.user_data["awaiting_withdrawal_amount"] = True

async def handle_withdrawal_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    amount_text = update.message.text
    
    if not context.user_data.get("awaiting_withdrawal_amount"):
        return
    
    try:
        amount = float(amount_text)
        if amount < 1000:
            await update.message.reply_text("❌ Minimum withdrawal is ₦1,000")
            return
        
        user_data = get_user(user_id)
        balance_naira = user_data.get("points", 0) * POINTS_TO_NAIRA
        
        if amount > balance_naira:
            await update.message.reply_text(f"❌ Insufficient balance. Your current balance is ₦{balance_naira:,.2f}")
            return
        
        # Process withdrawal
        withdrawal_id = str(datetime.now().timestamp())
        withdrawal_data = {
            "user_id": user_id,
            "amount": amount,
            "status": "pending",
            "date": datetime.utcnow().isoformat(),
            "account_details": {
                "bank": user_data.get("bank_name"),
                "account_number": user_data.get("account_number"),
                "account_name": user_data.get("account_name")
            }
        }
        
        # Save withdrawal record
        withdrawals = load_withdrawals()
        withdrawals[withdrawal_id] = withdrawal_data
        save_withdrawals(withdrawals)
        
        # Deduct from user balance
        user_data["points"] = user_data.get("points", 0) - (amount / POINTS_TO_NAIRA)
        user_data["total_withdrawn"] = user_data.get("total_withdrawn", 0) + amount
        user_data["total_earned"] = user_data.get("total_earned", 0) + amount
        update_user(user_id, user_data)
        
        # Notify admin
        if ADMIN_CHAT_ID:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"🔄 New Withdrawal Request:\n\n"
                     f"User: @{update.effective_user.username}\n"
                     f"Amount: ₦{amount:,.2f}\n"
                     f"Bank: {user_data.get('bank_name')}\n"
                     f"Account Number: {user_data.get('account_number')}\n"
                     f"Account Name: {user_data.get('account_name')}\n\n"
                     f"Withdrawal ID: {withdrawal_id}"
            )
        
        await update.message.reply_text(
            f"✅ Withdrawal request of ₦{amount:,.2f} submitted successfully!\n\n"
            "Your request will be processed within 24 hours.\n"
            "Use /withdrawals to check your withdrawal history."
        )
        
        context.user_data["awaiting_withdrawal_amount"] = False
    
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a valid number.")

async def withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    if not user_data.get("verified_user"):
        await update.message.reply_text("❌ Please complete verification first using /start")
        return
    
    withdrawals = load_withdrawals()
    user_withdrawals = [w for w in withdrawals.values() if w["user_id"] == str(user_id)]
    
    if not user_withdrawals:
        await update.message.reply_text("You have no withdrawal records yet.")
        return
    
    total_withdrawn = user_data.get("total_withdrawn", 0)
    total_earned = user_data.get("total_earned", 0)
    
    message = "📝 Your Withdrawal History:\n\n"
    for w in user_withdrawals:
        date = datetime.fromisoformat(w["date"]).strftime("%Y-%m-%d %H:%M")
        message += (
            f"💰 Amount: ₦{w['amount']:,.2f}\n"
            f"📅 Date: {date}\n"
            f"🔄 Status: {w['status']}\n"
            f"🏦 Bank: {w['account_details']['bank']}\n"
            f"🔢 Account: {w['account_details']['account_number']}\n\n"
        )
    
    message += f"💵 Total Withdrawn: ₦{total_withdrawn:,.2f}\n"
    message += f"💸 Total Earned: ₦{total_earned:,.2f}"
    
    await update.message.reply_text(message)

async def level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    if not user_data.get("verified_user"):
        await update.message.reply_text("❌ Please complete verification first using /start")
        return
    
    level_name, level_num = calculate_level(user_data)
    referrals = user_data.get("referrals", 0)
    total_earned = user_data.get("total_earned", 0)
    
    message = (
        f"🏆 Your Level: {level_name} (Level {level_num})\n\n"
        f"👥 Referrals: {referrals}\n"
        f"💰 Total Earned: ₦{total_earned:,.2f}\n\n"
    )
    
    # Show next level requirements
    if level_num == 1:
        message += "Next Level (Amateur) Requirements:\n- 20 referrals\n- ₦2,500 total earned"
    elif level_num == 2:
        message += "Next Level (Pro) Requirements:\n- 50 referrals\n- ₦5,000 total earned"
    elif level_num == 3:
        message += "Next Level (Master) Requirements:\n- 75 referrals\n- ₦7,500 total earned"
    elif level_num == 4:
        message += "Next Level (Guru) Requirements:\n- 100 referrals\n- ₦10,000 total earned"
    else:
        message += "You've reached the highest level!"
    
    await update.message.reply_text(message)

# --- Run Bot ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("tasks", tasks))
    app.add_handler(CommandHandler("setaccount", set_account))
    app.add_handler(CommandHandler("referral", referral))
    app.add_handler(CommandHandler("withdraw", withdraw))
    app.add_handler(CommandHandler("withdrawals", withdrawals))
    app.add_handler(CommandHandler("level", level))
    
    # Callback query handlers
    app.add_handler(CallbackQueryHandler(confirm_twitter, pattern="^confirm_twitter$"))
    app.add_handler(CallbackQueryHandler(bank_selection, pattern="^bank_.*"))
    
    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(r'^\d+$'), handle_account_number))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(r'^[a-zA-Z ]+$'), handle_account_name))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(r'^\d+\.?\d*$'), handle_withdrawal_amount))
    
    app.run_polling()

if __name__ == "__main__":
    main()