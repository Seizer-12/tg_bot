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
    ApplicationBuilder, CommandHandler, ConversationHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
TWITTER_HANDLE = os.getenv("TWITTER_HANDLE")
BOT_USERNAME = "UtilizersBot"
ADMIN_CHAT_ID = os.getenv("ADMIN_ID")  # Add this to your .env file

# Conversion rate (points to Naira)
POINTS_TO_NAIRA = 1  # 1 point = 1 Naira
DAILY_BONUS_AMOUNT = 25  # 25 Naira daily bonus

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

DATA_FILE = "user_data.json"
WITHDRAWAL_FILE = "withdrawals.json"

# --- Utility Functions ---
def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading data: {e}")
    return {}

def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving data: {e}")

def load_withdrawals():
    try:
        if os.path.exists(WITHDRAWAL_FILE):
            with open(WITHDRAWAL_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading withdrawals: {e}")
    return {}

def save_withdrawals(data):
    try:
        with open(WITHDRAWAL_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving withdrawals: {e}")

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
    if field not in user_info:
        user_info[field] = {}
    user_info[field]["date"] = today

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

def get_main_menu_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["💰 Balance", "📝 Tasks"],
            ["🏦 Set Account", "👥 Referral"],
            ["💳 Withdraw", "📋 Withdrawals"],
            ["🏆 Level", "🎁 Daily Bonus"],
            ["🏠 Main Menu"]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

# --- Start Command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user(user.id)

    if "referral" not in user_data:
        if context.args:
            referrer_id = context.args[0]
            if referrer_id != str(user.id):
                referrer_data = get_user(referrer_id)
                referrer_data["points"] = referrer_data.get("points", 0) + 70
                user_data["total_earned"] = user_data.get("total_earned", 0) + 70
                referrer_data["referrals"] = referrer_data.get("referrals", 0) + 1
                update_user(referrer_id, referrer_data)
                user_data["referral"] = referrer_id
                await update.message.reply_text(
                    "🎯 You just referred a user and got 25 Points...",
                    reply_markup=get_main_menu_keyboard()
                )

    update_user(user.id, user_data)

    keyboard = [
        [InlineKeyboardButton("🐦 Follow Twitter", url=f"https://twitter.com/{TWITTER_HANDLE}")],
        [InlineKeyboardButton("💬 Join Whatsapp Group", url="https://chat.whatsapp.com/KyBPEZKLjAZ8JMgFt9KMft")],
        [InlineKeyboardButton("📢 Join Whatsapp Channel", url="https://whatsapp.com/channel/0029VbAXEgUFy72Ich07Z53o")],
        [InlineKeyboardButton("✅ Join Telegram Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton("🔍 Verify Tasks", callback_data="verify_tasks")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"🎯 WELCOME {user.username or user.first_name} \n\nTo participate in the campaign, complete the tasks below:\n\n\n"
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
    except Exception as e:
        logger.error(f"Error verifying channel membership: {e}")
        await query.edit_message_text("❌ You have not joined the Telegram channel.\n\nType or tap /start to start again")
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
    user_data["total_earned"] = user_data.get("total_earned", 0) + 50
    
    update_user(user_id, user_data)

    await query.edit_message_text(
        "✅ You're verified and have earned ₦50 for completing the tasks!\n\n"
        "Use the menu below to explore the bot features:",
        reply_markup=get_main_menu_keyboard()
    )

# --- Command Handlers ---
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    if not user_data.get("verified_user"):
        await update.message.reply_text("❌ Please complete verification first using /start")
        return
    
    if text == "💰 balance":
        await balance(update, context)
    elif text == "📝 tasks":
        await tasks(update, context)
    elif text == "🏦 set account":
        await set_account(update, context)
    elif text == "👥 referral":
        await referral(update, context)
    elif text == "💳 withdraw":
        await withdraw(update, context)
    elif text == "📋 withdrawals":
        await withdrawals(update, context)
    elif text == "🏆 level":
        await level(update, context)
    elif text == "🎁 daily bonus":
        await daily_bonus(update, context)
    elif text == "🏠 main menu":
        await update.message.reply_text(
            "Main Menu:",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        # Handle context-specific inputs
        if context.user_data.get("awaiting_bank"):
            await handle_bank_selection(update, context)
        elif context.user_data.get("awaiting_account_number"):
            await handle_account_number(update, context)
        elif context.user_data.get("awaiting_account_name"):
            await handle_account_name(update, context)
        elif context.user_data.get("awaiting_withdrawal_amount"):
            await handle_withdrawal_amount(update, context)
        else:
            await update.message.reply_text(
                "I didn't understand that command. Please use the menu buttons.",
                reply_markup=get_main_menu_keyboard()
            )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    balance_naira = user_data.get("points", 0) * POINTS_TO_NAIRA
    await update.message.reply_text(
        f"💰 Your current balance: ₦{balance_naira:,.2f}",
        reply_markup=get_main_menu_keyboard()
    )

#tasks
async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    # Check if user has already claimed today
    if has_claimed_today(user_data, "daily_tasks"):
        await update.message.reply_text(
            "❌ You've already completed tasks today. Come back tomorrow!",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    bot_link = "https://t.me/UtilizersBot"
    task_link1 = f"https://twitter.com/{TWITTER_HANDLE}"
    post_text = f"I just joined the Utilizers, and you should too! \n\nGet started early and don't miss out. \n\nAct fast, and accumulate earnings!\n\n{bot_link}"
    encoded_text = urllib.parse.quote(post_text)
    task_link2 = f"https://twitter.com/intent/tweet?text={encoded_text}"
    task_link3 = f"https://wa.me/?text={encoded_text}"

    message = (
        f"📝 Available Tasks (Complete all to earn ₦50 daily):\n\n"
        f"1. Follow <a href='{task_link1}'>Utilizer01 on Twitter</a>\n\n"
        f"2. <a href='{task_link2}'>Post on X (Twitter)</a>\n\n"
        f"3. <a href='{task_link3}'>Share to 5 WhatsApp groups and your status</a>\n\n"
        "After completing all tasks, upload screenshots as proof to claim your ₦50 reward."
    )
    
    await update.message.reply_text(
        message, 
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu_keyboard()
    )
    context.user_data["awaiting_task_proof"] = True

async def handle_task_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_task_proof"):
        return
    
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    # Check if user has already claimed today
    if has_claimed_today(user_data, "daily_tasks"):
        await update.message.reply_text(
            "❌ You've already claimed your daily task reward today. Come back tomorrow!",
            reply_markup=get_main_menu_keyboard()
        )
        context.user_data["awaiting_task_proof"] = False
        return
    
    # Award the user
    user_data["points"] = user_data.get("points", 0) + 50
    user_data["total_earned"] = user_data.get("total_earned", 0) + 50
    mark_claimed_today(user_data, "daily_tasks")
    update_user(user_id, user_data)
    
    await update.message.reply_text(
        "✅ Screenshot received! You've been awarded ₦50 for completing today's tasks.",
        reply_markup=get_main_menu_keyboard()
    )
    context.user_data["awaiting_task_proof"] = False


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


async def set_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    # Check if user already has account details
    if user_data.get("account_set"):
        await update.message.reply_text(
            f"Your current account details:\n"
            f"Bank: {user_data.get('bank_name', 'Not set')}\n"
            f"Account Number: {user_data.get('account_number', 'Not set')}\n"
            f"Account Name: {user_data.get('account_name', 'Not set')}\n\n"
            "To update, please send:\n"
            "1. Your bank (OPay or PalmPay)\n"
            "2. Your account number\n"
            "3. Your account name\n\n"
            "In separate messages.",
            reply_markup=ReplyKeyboardMarkup(
                [["🏠 Main Menu"]],
                resize_keyboard=True
            )
        )
        context.user_data["awaiting_bank"] = True
        return
    
    await update.message.reply_text(
        "Please set your account details by sending:\n"
        "1. Your bank (OPay or PalmPay)\n"
        "2. Your account number\n"
        "3. Your account name\n\n"
        "In separate messages.",
        reply_markup=ReplyKeyboardMarkup(
            [["🏠 Main Menu"]],
            resize_keyboard=True
        )
    )
    context.user_data["awaiting_bank"] = True

async def handle_bank_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bank = update.message.text.strip().lower()
    
    if bank not in ["opay", "palmpay"]:
        await update.message.reply_text(
            "❌ Invalid bank. Please choose either OPay or PalmPay.",
            reply_markup=ReplyKeyboardMarkup(
                [["🏠 Main Menu"]],
                resize_keyboard=True
            )
        )
        return
    
    context.user_data["selected_bank"] = bank.capitalize()
    context.user_data["awaiting_bank"] = False
    context.user_data["awaiting_account_number"] = True
    
    await update.message.reply_text(
        "Now please send your account number:",
        reply_markup=ReplyKeyboardMarkup(
            [["🏠 Main Menu"]],
            resize_keyboard=True
        )
    )

async def handle_account_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    account_number = update.message.text.strip()
    
    if not account_number.isdigit() or len(account_number) < 10:
        await update.message.reply_text(
            "❌ Invalid account number. Please enter a valid 10-digit account number.",
            reply_markup=ReplyKeyboardMarkup(
                [["🏠 Main Menu"]],
                resize_keyboard=True
            )
        )
        return
    
    context.user_data["account_number"] = account_number
    context.user_data["awaiting_account_number"] = False
    context.user_data["awaiting_account_name"] = True
    
    await update.message.reply_text(
        "Now please send your account name as it appears on your bank records:",
        reply_markup=ReplyKeyboardMarkup(
            [["🏠 Main Menu"]],
            resize_keyboard=True
        )
    )

async def handle_account_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    account_name = update.message.text.strip()
    
    if len(account_name) < 2:
        await update.message.reply_text(
            "❌ Invalid account name. Please enter your full name.",
            reply_markup=get_main_menu_keyboard()
        )
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
        f"Account Name: {user_data['account_name']}",
        reply_markup=get_main_menu_keyboard()
    )

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
    count = user_data.get("referrals", 0)
    await update.message.reply_text(
        f"👥 Your referral link:\n{ref_link}\n\n"
        f"Total referrals: {count}\n"
        f"Earn ₦70 for each successful referral (when they complete initial tasks)",
        reply_markup=get_main_menu_keyboard()
    )

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    if not user_data.get("account_set"):
        await update.message.reply_text(
            "❌ Please set your account details first using '🏦 Set Account'",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    balance_naira = user_data.get("points", 0) * POINTS_TO_NAIRA
    
    if balance_naira < 1000:
        await update.message.reply_text(
            f"❌ Minimum withdrawal is ₦1,000. Your current balance is ₦{balance_naira:,.2f}",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    await update.message.reply_text(
        f"💰 Your current balance: ₦{balance_naira:,.2f}\n"
        f"Minimum withdrawal: ₦1,000\n\n"
        "Please enter the amount you want to withdraw:",
        reply_markup=ReplyKeyboardMarkup(
            [["🏠 Main Menu"]],
            resize_keyboard=True
        )
    )
    context.user_data["awaiting_withdrawal_amount"] = True

async def handle_withdrawal_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    amount_text = update.message.text.strip()
    
    try:
        amount = float(amount_text)
        if amount < 1000:
            await update.message.reply_text(
                "❌ Minimum withdrawal is ₦1,000",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        user_data = get_user(user_id)
        balance_naira = user_data.get("points", 0) * POINTS_TO_NAIRA
        
        if amount > balance_naira:
            await update.message.reply_text(
                f"❌ Insufficient balance. Your current balance is ₦{balance_naira:,.2f}",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Process withdrawal
        withdrawal_id = str(datetime.now().timestamp())
        withdrawal_data = {
            "user_id": str(user_id),
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
        user_data["points"] = max(0, user_data.get("points", 0) - (amount / POINTS_TO_NAIRA))
        user_data["total_withdrawn"] = user_data.get("total_withdrawn", 0) + amount
        user_data["total_earned"] = user_data.get("total_earned", 0) + amount
        update_user(user_id, user_data)
        
        # Notify admin
        if ADMIN_CHAT_ID:
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=f"🔄 New Withdrawal Request:\n\n"
                         f"User: @{update.effective_user.username or update.effective_user.first_name}\n"
                         f"User ID: {user_id}\n"
                         f"Amount: ₦{amount:,.2f}\n"
                         f"Bank: {user_data.get('bank_name')}\n"
                         f"Account Number: {user_data.get('account_number')}\n"
                         f"Account Name: {user_data.get('account_name')}\n\n"
                         f"Withdrawal ID: {withdrawal_id}"
                )
            except Exception as e:
                logger.error(f"Error sending admin notification: {e}")
        
        await update.message.reply_text(
            f"✅ Withdrawal request of ₦{amount:,.2f} submitted successfully!\n\n"
            "Your request will be processed within 24 hours.\n"
            "Use '📋 Withdrawals' to check your withdrawal history.",
            reply_markup=get_main_menu_keyboard()
        )
        
        context.user_data["awaiting_withdrawal_amount"] = False
    
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid amount. Please enter a valid number.",
            reply_markup=get_main_menu_keyboard()
        )

async def withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    withdrawals = load_withdrawals()
    user_withdrawals = [w for w in withdrawals.values() if w["user_id"] == str(user_id)]
    
    if not user_withdrawals:
        await update.message.reply_text(
            "You have no withdrawal records yet.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    total_withdrawn = user_data.get("total_withdrawn", 0)
    total_earned = user_data.get("total_earned", 0)
    
    message = "📝 Your Withdrawal History:\n\n"
    for w in sorted(user_withdrawals, key=lambda x: x["date"], reverse=True):
        try:
            date = datetime.fromisoformat(w["date"]).strftime("%Y-%m-%d %H:%M")
            message += (
                f"💰 Amount: ₦{w['amount']:,.2f}\n"
                f"📅 Date: {date}\n"
                f"🔄 Status: {w.get('status', 'pending')}\n"
                f"🏦 Bank: {w['account_details']['bank']}\n"
                f"🔢 Account: {w['account_details']['account_number']}\n\n"
            )
        except Exception as e:
            logger.error(f"Error formatting withdrawal record: {e}")
            continue
    
    message += f"💵 Total Withdrawn: ₦{total_withdrawn:,.2f}\n"
    message += f"💸 Total Earned: ₦{total_earned:,.2f}"
    
    await update.message.reply_text(
        message,
        reply_markup=get_main_menu_keyboard()
    )

async def level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
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
    
    await update.message.reply_text(
        message,
        reply_markup=get_main_menu_keyboard()
    )

async def daily_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    if has_claimed_today(user_data, "daily_bonus"):
        await update.message.reply_text(
            "❌ You've already claimed your daily bonus today. Come back tomorrow!",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    # Award daily bonus
    user_data["points"] = user_data.get("points", 0) + DAILY_BONUS_AMOUNT
    user_data["total_earned"] = user_data.get("total_earned", 0) + DAILY_BONUS_AMOUNT
    mark_claimed_today(user_data, "daily_bonus")
    update_user(user_id, user_data)
    
    await update.message.reply_text(
        f"🎁 You've claimed your daily bonus of ₦{DAILY_BONUS_AMOUNT}!\n"
        f"💰 Your new balance: ₦{(user_data.get('points', 0) * POINTS_TO_NAIRA):,.2f}",
        reply_markup=get_main_menu_keyboard()
    )

# --- Run Bot ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    
    # Callback query handlers
    app.add_handler(CallbackQueryHandler(confirm_twitter, pattern="^confirm_twitter$"))
    app.add_handler(CallbackQueryHandler(verify_tasks, pattern="^verify_tasks$"))
    
    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_task_proof))

    # Error handler
    app.add_error_handler(error_handler)
    
    app.run_polling()

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_user:
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text="❌ An error occurred. Please try again.",
            reply_markup=get_main_menu_keyboard()
        )

if __name__ == "__main__":
    main()
