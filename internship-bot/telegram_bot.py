import os
import subprocess
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Setup basic logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load variables
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /run command."""
    chat_id = str(update.effective_chat.id)
    
    # Security: only allow the configured chat ID to run the bot
    if chat_id != ALLOWED_CHAT_ID:
        logger.warning(f"Unauthorized /run attempt from chat ID {chat_id}")
        return

    await update.message.reply_text("🚀 Starting ApplyFlow background runner... Check your terminal for live logs!")
    
    try:
        # Spawn the bot process asynchronously
        subprocess.Popen(
            ["python", "main.py", "--run-now"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        logger.error(f"Failed to start main.py: {e}")
        await update.message.reply_text(f"❌ Failed to start the bot: {e}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /start command."""
    chat_id = str(update.effective_chat.id)
    if chat_id != ALLOWED_CHAT_ID:
        return
    await update.message.reply_text("👋 Hello! I am your ApplyFlow controller.\n\nSend /run to start the internship application scraper, or /help to see all commands.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /help command."""
    chat_id = str(update.effective_chat.id)
    if chat_id != ALLOWED_CHAT_ID:
        return
    help_text = (
        "🤖 **ApplyFlow Bot Commands**\n\n"
        "▶️ /run - Start the background application scraper\n"
        "📊 /stats - Get current application statistics\n"
        "🏓 /ping - Check if the Telegram listener is online\n"
        "❓ /help - Show this message"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /ping command."""
    chat_id = str(update.effective_chat.id)
    if chat_id != ALLOWED_CHAT_ID:
        return
    await update.message.reply_text("🏓 Pong! The ApplyFlow Telegram listener is online and ready.")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /stats command."""
    chat_id = str(update.effective_chat.id)
    if chat_id != ALLOWED_CHAT_ID:
        return
    
    csv_path = "logs/applications.csv"
    if not os.path.exists(csv_path):
        await update.message.reply_text("📉 No statistics available yet (`logs/applications.csv` not found).")
        return
    
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        total = max(0, len(lines) - 1)
        applied = sum(1 for l in lines if ",Applied," in l)
        errors = sum(1 for l in lines if ",Error" in l)
        pending = sum(1 for l in lines if ",Pending" in l)
        
        stats_text = (
            "📊 **ApplyFlow Current Statistics**\n\n"
            f"✅ **Applied:** {applied}\n"
            f"❌ **Errors:** {errors}\n"
            f"⏳ **Pending/Skipped:** {pending}\n"
            f"📝 **Total Listings Processed:** {total}"
        )
        await update.message.reply_text(stats_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Failed to read stats: {e}")
        await update.message.reply_text(f"❌ Could not read statistics: {e}")

if __name__ == "__main__":
    if not BOT_TOKEN or not ALLOWED_CHAT_ID or BOT_TOKEN == "your_bot_token_here":
        print("Telegram credentials missing in .env. Exiting.")
        exit(1)

    print("Telegram Remote Control is starting...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("run", run_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(CommandHandler("stats", stats_command))

    print("Telegram Listener is now running! Send /run in Telegram to start the bot.")
    app.run_polling()
