"""
Telegram bot command/message handlers
"""

from telegram import Update
from telegram.ext import ContextTypes

from config import Config
from database import Event, SessionLocal
from message_parser import CATEGORY_LABELS, categorize
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
            f"Just message me naturally to log an event:\n"
            f"  \U0001F305 Wake up: Goodmorning / Awake / I'm awake\n"
            f"  \U0001F3E2 Arrive at work: At work / Arrived at work / Arrived\n"
            f"  \U0001F6AA Leave work: Leaving / Left / Leaving work / Left work / Goodbye / Bye work\n"
            f"  \U0001F319 Bedtime: Goodnight / Bedtime / Going to sleep / Sleeping\n\n"
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
    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not TelegramHandler._is_authorized(update):
            await update.message.reply_text(
                "This bot is private and isn't set up to log events for you."
            )
            return

        text = update.message.text or ""
        category = categorize(text)

        if category is None:
            await update.message.reply_text(
                "I didn't recognize that as a wake/arrive/leave/sleep message. "
                "Send /help to see the phrases I understand."
            )
            return

        db = SessionLocal()
        try:
            event = Event(category=category, timestamp=Config.now(), raw_message=text)
            db.add(event)
            db.commit()
            logged_at = event.timestamp
        finally:
            db.close()

        label = CATEGORY_LABELS[category]
        await update.message.reply_text(f"Logged: {label} at {logged_at.strftime('%I:%M %p').lstrip('0')}")
