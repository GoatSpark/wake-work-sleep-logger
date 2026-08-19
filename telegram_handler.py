"""
Telegram bot command/message handlers
"""

from telegram import Update
from telegram.ext import ContextTypes

from config import Config
from database import Event, SessionLocal
from message_parser import CATEGORY_LABELS, categorize, parse_backfill
from stats import RANGE_DAYS, all_category_stats, build_days_table

RANGE_ORDER = ["week", "month", "quarter", "year"]
RANGE_TITLES = {
    "week": "Last 7 days",
    "month": "Last 30 days",
    "quarter": "Last 90 days",
    "year": "Last 365 days",
}


class TelegramHandler:
    """Handle Telegram bot interactions"""

    @staticmethod
    def _is_authorized(update: Update) -> bool:
        if Config.TELEGRAM_USER_ID is None:
            return True
        return update.effective_user.id == Config.TELEGRAM_USER_ID

    @staticmethod
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        await update.message.reply_text(
            f"\U0001F4CA Welcome to Wake/Work/Sleep Logger!\n\n"
            f"Your Telegram ID: {user_id}\n\n"
            f"Add this to your .env file as TELEGRAM_USER_ID so only you "
            f"can log events, then restart the bot.\n\n"
            f"Message me naturally to log an event right now:\n"
            f"  \U0001F305 Wake up: Goodmorning / Awake / I'm awake\n"
            f"  \U0001F3E2 Arrive at work: At work / Arrived at work / Arrived\n"
            f"  \U0001F6AA Leave work: Leaving / Left / Leaving work / Left work / Goodbye / Bye work\n"
            f"  \U0001F319 Bedtime: Goodnight / Bedtime / Going to sleep / Sleeping\n\n"
            f"Forgot to log something in the moment? Backfill it with a "
            f"time and I'll log it for that time instead of now:\n"
            f"  • I arrived to work at 9:00 AM yesterday\n"
            f"  • I went to sleep at 11:00 PM last night\n"
            f"  • I got to work at 8:30 AM this morning\n\n"
            f"Commands:\n"
            f"  /stats - View your averages, earliest and latest for each category\n"
            f"  /help - Show this message"
        )

    @staticmethod
    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await TelegramHandler.start(update, context)

    @staticmethod
    async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not TelegramHandler._is_authorized(update):
            return

        db = SessionLocal()
        try:
            by_date = build_days_table(db)
        finally:
            db.close()

        if not by_date:
            await update.message.reply_text("No events logged yet.")
            return

        lines = []
        for range_name in RANGE_ORDER:
            stats = all_category_stats(by_date, range_name)
            lines.append(f"\U0001F4C8 {RANGE_TITLES[range_name]}")
            for category, label in CATEGORY_LABELS.items():
                s = stats[category]
                if s is None:
                    lines.append(f"  {label}: no data")
                else:
                    lines.append(
                        f"  {label}: avg {s['average']}  "
                        f"(earliest {s['earliest']}, latest {s['latest']}, n={s['count']})"
                    )
            lines.append("")

        await update.message.reply_text("\n".join(lines).strip())

    @staticmethod
    def _log_event(category: str, timestamp, raw_message: str) -> None:
        db = SessionLocal()
        try:
            db.add(Event(category=category, timestamp=timestamp, raw_message=raw_message))
            db.commit()
        finally:
            db.close()

    @staticmethod
    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not TelegramHandler._is_authorized(update):
            await update.message.reply_text(
                "This bot is private and isn't set up to log events for you."
            )
            return

        text = update.message.text or ""

        category = categorize(text)
        if category is not None:
            timestamp = Config.now()
            TelegramHandler._log_event(category, timestamp, text)
            label = CATEGORY_LABELS[category]
            await update.message.reply_text(
                f"Logged: {label} at {timestamp.strftime('%I:%M %p').lstrip('0')}"
            )
            return

        backfill = parse_backfill(text, Config.now())
        if backfill is not None:
            category, timestamp = backfill
            TelegramHandler._log_event(category, timestamp, text)
            label = CATEGORY_LABELS[category]
            await update.message.reply_text(
                f"Logged (backfilled): {label} at "
                f"{timestamp.strftime('%I:%M %p').lstrip('0')} on "
                f"{timestamp.strftime('%A, %b %-d')}"
            )
            return

        await update.message.reply_text(
            "I didn't recognize that as a wake/arrive/leave/sleep message. "
            "Send /help to see the phrases I understand, or backfill one "
            "with a time, e.g. \"I arrived to work at 9:00 AM yesterday\"."
        )
