"""
Database models and setup for Wake/Work/Sleep Logger
"""

import glob
import os
import shutil
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from config import get_database_url, Config

BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")
BACKUPS_TO_KEEP = 14

DATABASE_URL = get_database_url()
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False
)

_SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

LIVE_DB_ENV_VAR = "WWSL_BOT_ALLOW_LIVE_DB"


def SessionLocal():
    """
    Open a session against the live wwsl.db.

    Requires the WWSL_BOT_ALLOW_LIVE_DB env var to be set - main.py and
    export_stats.py both set it automatically before importing anything
    else, so normal operation is unaffected. This guard exists to stop an
    ad-hoc/debug script from accidentally running a destructive query
    against real logged events (same pattern as chores-assistant, which
    was bitten by exactly this twice). If you're deliberately making a
    targeted, one-off fix to production data, set the env var explicitly
    right in that command - that makes the intent visible instead of
    implicit. For anything exploratory or destructive, use an isolated
    database instead (see tests/conftest.py's db_session fixture).
    """
    if not os.environ.get(LIVE_DB_ENV_VAR):
        raise RuntimeError(
            f"Refusing to open a session against the live wwsl.db: "
            f"{LIVE_DB_ENV_VAR} is not set. If this is a deliberate, "
            f"targeted fix to production data, set {LIVE_DB_ENV_VAR}=1 "
            f"explicitly. For testing/exploration, use an isolated "
            f"database instead - never the live one."
        )
    return _SessionFactory()


Base = declarative_base()

# Valid Event.category values
WAKE = "wake"
ARRIVE_WORK = "arrive_work"
LEAVE_WORK = "leave_work"
SLEEP = "sleep"
CATEGORIES = (WAKE, ARRIVE_WORK, LEAVE_WORK, SLEEP)


class Event(Base):
    """One logged wake/arrive-work/leave-work/sleep timestamp"""
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, default=Config.now, index=True)
    raw_message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=Config.now)

    def __repr__(self):
        return f"<Event id={self.id} category={self.category} timestamp={self.timestamp}>"


def backup_database():
    """
    Copy the SQLite database file into backups/ before touching it further.
    A no-op for non-SQLite databases or if the file doesn't exist yet (first run).
    Keeps only the most recent BACKUPS_TO_KEEP backups.
    """
    if not DATABASE_URL.startswith("sqlite:///"):
        return

    db_path = DATABASE_URL.removeprefix("sqlite:///")
    if not os.path.exists(db_path):
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = Config.now().strftime("%Y%m%d_%H%M%S")
    db_name = os.path.splitext(os.path.basename(db_path))[0]
    backup_path = os.path.join(BACKUP_DIR, f"{db_name}_{timestamp}.db")
    shutil.copy2(db_path, backup_path)

    backups = sorted(glob.glob(os.path.join(BACKUP_DIR, f"{db_name}_*.db")))
    for stale_backup in backups[:-BACKUPS_TO_KEEP]:
        os.remove(stale_backup)


def init_db():
    """Initialize database tables"""
    backup_database()
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    os.environ.setdefault(LIVE_DB_ENV_VAR, "1")
    init_db()
