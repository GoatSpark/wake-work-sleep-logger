"""
Main entry point for Wake/Work/Sleep Logger
"""

import os

# Must be set before `database` is imported (directly or transitively via
# telegram_handler) - see database.SessionLocal for why.
os.environ.setdefault("WWSL_BOT_ALLOW_LIVE_DB", "1")

import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import Config
from database import init_db
from telegram_handler import TelegramHandler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def setup_handlers(app: Application):
    app.add_handler(CommandHandler("start", TelegramHandler.start))
    app.add_handler(CommandHandler("help", TelegramHandler.help_command))
    app.add_handler(CommandHandler("stats", TelegramHandler.show_stats))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, TelegramHandler.handle_message)
    )


def main():
    Config.validate()
    init_db()

    app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
    setup_handlers(app)

    logger.info("Starting Wake/Work/Sleep Logger Bot...")
    logger.info(f"Timezone: {Config.TIMEZONE}")

    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
