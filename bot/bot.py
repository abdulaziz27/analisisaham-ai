"""
Telegram Bot Main Entry Point
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# Import handlers
from bot.handlers.start import start_command
from bot.handlers.analisa import analisa_command
from bot.handlers.quota import kuota_command
from bot.handlers.callbacks import handle_callback

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle errors
    """
    logger.error(f"Update {update} caused error {context.error}", exc_info=context.error)
    
    try:
        if isinstance(update, Update):
            if update.message:
                await update.message.reply_text(
                    "❌ Terjadi error. Mohon coba lagi nanti."
                )
            elif update.callback_query:
                await update.callback_query.answer(
                    "❌ Terjadi error. Coba lagi.",
                    show_alert=True
                )
    except Exception as e:
        logger.error(f"Error in error handler: {e}")


async def post_init(application: Application):
    """
    Set up bot commands menu on startup
    """
    try:
        commands = [
            BotCommand("start", "Mulai bot & bantuan"),
            BotCommand("analisa", "Analisa saham (e.g. /analisa BBCA)"),
            BotCommand("kuota", "Cek sisa kuota & Info akun"),
        ]
        await application.bot.set_my_commands(commands)
        logger.info("Bot commands menu updated successfully")
    except Exception as e:
        logger.error(f"Failed to update bot commands: {e}")

def main():
    """
    Start the bot
    """
    # Get bot token from environment
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
    
    # Create application with post_init hook
    application = Application.builder().token(bot_token).post_init(post_init).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("analisa", analisa_command))
    application.add_handler(CommandHandler("kuota", kuota_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start bot
    logger.info("Bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
