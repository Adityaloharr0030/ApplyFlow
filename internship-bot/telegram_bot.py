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
    await update.message.reply_text("👋 Hello! I am your ApplyFlow controller.\n\nSend /run to start the internship application scraper.")

if __name__ == "__main__":
    if not BOT_TOKEN or not ALLOWED_CHAT_ID or BOT_TOKEN == "your_bot_token_here":
        print("Telegram credentials missing in .env. Exiting.")
        exit(1)

    print("Telegram Remote Control is starting...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("run", run_command))

    print("Telegram Listener is now running! Send /run in Telegram to start the bot.")
    app.run_polling()
