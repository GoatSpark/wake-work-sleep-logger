"""
Configuration management for Wake/Work/Sleep Logger
"""

import os
from datetime import datetime
from dotenv import load_dotenv
import pytz

load_dotenv()


class Config:
    """Application configuration"""

    # Telegram Bot
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    _user_id_str = os.getenv("TELEGRAM_USER_ID")
    TELEGRAM_USER_ID = int(_user_id_str) if _user_id_str and _user_id_str.isdigit() else None

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///wwsl.db")

    # Timezone
    TIMEZONE = pytz.timezone(os.getenv("TIMEZONE", "America/Los_Angeles"))

    @classmethod
    def validate(cls) -> bool:
        """Validate that all required configuration is set"""
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN not set in .env file")
        # TELEGRAM_USER_ID is optional on startup - user can get it from /start command
        return True

    @classmethod
    def now(cls):
        """
        Current local time as a naive datetime.
        SQLite (this project's database) has no real timezone support, so
        datetimes are stored and compared as naive local time everywhere in
        the app. Localize here once, then drop the tzinfo.
        """
        return datetime.now(cls.TIMEZONE).replace(tzinfo=None)


def get_database_url():
    """Get the database URL for SQLAlchemy"""
    url = Config.DATABASE_URL
    if url.startswith("sqlite"):
        if ":///" in url:
            return url
        return f"sqlite:///{url}"
    return url


if __name__ == "__main__":
    print(f"Bot Token: {Config.TELEGRAM_BOT_TOKEN[:10]}..." if Config.TELEGRAM_BOT_TOKEN else "Not set")
    print(f"User ID: {Config.TELEGRAM_USER_ID}")
    print(f"Database: {Config.DATABASE_URL}")
    print(f"Timezone: {Config.TIMEZONE}")
