# Wake/Work/Sleep Logger — Project Steering File

A personal Telegram bot that logs four daily life events - waking up,
arriving at work, leaving work, going to bed - either in real time (fixed
exact phrases) or backfilled after the fact (free-text with an explicit
time, e.g. "I arrived to work at 9:00 AM yesterday") - plus a static GitHub
Pages dashboard showing trends/averages over week/month/quarter/year.
Single user, SQLite-backed, runs as a long-lived polling process
(`python main.py`), same overall shape as the sibling [[chores-assistant]]
project.

## Architecture

```
main.py                 Entry point. Builds the python-telegram-bot Application,
                         registers handlers, runs polling.
config.py                Env var loading (.env via python-dotenv) + Config.now()
database.py              SQLAlchemy Event model + backup_database()
message_parser.py        Exact-phrase instant classification + free-text backfill parsing
telegram_handler.py      /start, /help, /stats, and free-text message handling
stats.py                 Per-day aggregation + avg/min/max stats over a date range
export_stats.py          Dumps docs/data.json for the GitHub Pages dashboard
docs/index.html           Static dashboard (fetches data.json client-side, no build step)
scripts/export_and_push.sh    Runs export_stats.py, commits+pushes docs/data.json if changed
scripts/manual_smoke_test.py  Sends a real Telegram message via the live bot for manual checks
tests/                   pytest suite, isolated in-memory DB (conftest.py fixture)
```

Message flow, in `telegram_handler.handle_message`: an incoming text message
is tried against **two parsers in order**, and the first one that succeeds
wins:

1. `message_parser.categorize` - exact match (after lowercasing/stripping
   punctuation) against a fixed phrase list, logged with `timestamp =
   Config.now()`. This is the real-time "log it right now" path.
2. `message_parser.parse_backfill` - only tried if (1) didn't match. Uses
   keyword/regex heuristics instead of an exact list (backfilled phrasing
   can't be enumerated the way instant phrases can), and only fires if the
   message contains an **explicit clock time** - that's the signal that
   distinguishes "log this for a specific past/other time" from "I said
   something I didn't mean as a log entry". Resolves "yesterday"/"last
   night" to the previous calendar day, everything else (including no day
   word at all) to today.

If neither matches, the bot asks the user to check `/help` rather than
silently dropping the message.

Recognized instant phrases (see `message_parser.CATEGORY_PHRASES` - update
both places if these ever change):
- **wake**: Goodmorning, Awake, I'm awake
- **arrive_work**: At work, Arrived at work, Arrived
- **leave_work**: Leaving, Left, Leaving work, Left work, Goodbye, Bye work
- **sleep**: Goodnight, Bedtime, Going to sleep, Sleeping

Instant-phrase matching is exact (post-normalization), not substring/fuzzy -
deliberately, so "leftovers" doesn't get misread as "left". If the phrase
list grows, prefer adding new exact phrases over loosening the match to
substring.

Backfill category keywords (see `message_parser._BACKFILL_CATEGORY_PATTERNS`)
are looser stems/phrases - `arriv*`, `got/get/made it to work`, `at work` for
arrive_work; `leav*`, `left`, `goodbye`, `bye` for leave_work; `wake*`,
`woke`, `awake` for wake; `sleep*`, `bed*` for sleep. Word-boundary-anchored
the same way the instant list is, so "leftovers" still doesn't false-positive
as leave_work. If a message's text matches keywords from **more than one**
category, `_categorize_backfill` treats it as ambiguous and returns no match
(fails safe to "didn't understand" rather than guessing wrong) - this is a
known/accepted limitation for oddly-phrased messages, not a bug to silently
"fix" by picking one.

## Key conventions

- **All datetimes are naive local time, always.** Same reasoning as
  chores-assistant: SQLite drops tzinfo on round-trip, so the whole app
  standardizes on naive local datetimes. Use `Config.now()`, never
  `datetime.now()`.
- **Never hardcode secrets** (bot token, GitHub deploy key) outside `.env`
  and `~/.ssh/`. `.env` is gitignored.
- **Never run ad-hoc scripts against the live `wwsl.db`.**
  `database.SessionLocal()` refuses to open unless `WWSL_BOT_ALLOW_LIVE_DB`
  is set (`main.py` and `export_stats.py` set it automatically). A
  deliberate one-off production fix should set that env var explicitly in
  the command itself. `init_db()` backs up `wwsl.db` into `backups/` (keeps
  last 14) on every bot startup as a second line of defense. See
  chores-assistant's CLAUDE.md "Lessons Learned" for why this rule exists -
  it was learned the hard way there, and this project copied the guard rail
  up front instead of waiting to repeat the mistake.
- **Bedtime crosses midnight; averaging handles that.** A naive average of
  11:30 PM and 12:30 AM comes out to noon, which is nonsense. `stats.py`'s
  `WRAP_MIDNIGHT_CATEGORIES` (currently just `sleep`) shifts any time before
  noon by +24h before computing avg/min/max, then formats back to a normal
  clock time. `docs/index.html`'s JS mirrors this same logic client-side
  (`WRAP_MIDNIGHT` set) - if the wraparound rule ever changes, update both.
- **Same-day duplicates use the earliest event.** If the user sends "awake"
  twice in one morning, `stats.build_days_table` keeps only the earliest
  timestamp per (day, category) as that day's data point, so a duplicate or
  correction message can't skew the average.
- **The bot restricts itself to `TELEGRAM_USER_ID` once configured.**
  Unlike chores-assistant (which never bothered), `handle_message` checks
  `update.effective_user.id` against `Config.TELEGRAM_USER_ID` when that's
  set and silently-politely declines otherwise. It's optional at first boot
  (unset = accept from anyone) so `/start` can reveal the ID to put in
  `.env`.

## The GitHub Pages data pipeline

The dashboard at `docs/index.html` is static and has no server - it can only
`fetch()` a same-origin file. Since the bot's DB lives on a home server with
no public inbound access, the sync direction is push-from-server, not
pull-from-page:

```
Linux box (systemd timer, every 15 min)
  -> scripts/export_and_push.sh
       -> export_stats.py reads wwsl.db, writes docs/data.json
       -> git commit + git push (only if data.json changed)
  -> GitHub Pages redeploys docs/ automatically on push to main
```

- The repo (`GoatSpark/wake-work-sleep-logger`) is **public** - GitHub Pages
  requires that on the free tier, and the data is just timestamps (no
  content/location), which the user was comfortable making public.
- Push auth uses a **dedicated deploy key**
  (`~/.ssh/wake_work_sleep_logger_deploy` on the Linux box), added to the
  GitHub repo with write access, not a personal access token - it can only
  ever touch this one repo. The `origin` remote URL uses the `github-wwsl`
  alias in `~/.ssh/config` (`IdentityFile` pointed at that key), so plain
  `git push origin` "just works" without extra flags.
- `export_stats.py` only writes JSON - it never touches git. Git add/commit/
  push lives entirely in `scripts/export_and_push.sh`, run by the
  `wake-work-sleep-logger-export.timer` systemd unit. Keeping git operations
  out of the Python script makes `export_stats.py`'s output directly
  testable and keeps "what pushes to a public repo" in one auditable place.
- Data lag is bounded by the timer interval (15 min), not real-time - this
  was a deliberate simplicity-over-freshness tradeoff (the alternative, a
  live API tunneled off the home box, was rejected as more moving parts and
  attack surface than a personal habit tracker warrants).
- `docs/data.json`'s per-day rows store `time-of-day-in-minutes` (an int),
  not `"HH:MM"` strings, so the dashboard's JS does its own stats/chart math
  without re-parsing time strings.

## Running the bot / working preferences

Lives on the same always-on Linux box as chores-assistant (Ubuntu 24.04,
`192.168.0.44`, user `plexbot2`) at
`/home/plexbot2/dev/wake-work-sleep-logger`, also reachable from Windows at
`\\192.168.0.44\claudeshare\wake-work-sleep-logger` (same files). Runs as a
systemd **user** service, same lingering setup as chores-assistant.

```bash
# Bot service
systemctl --user status wake-work-sleep-logger.service
systemctl --user restart wake-work-sleep-logger.service   # after a code change
journalctl --user -u wake-work-sleep-logger.service -n 100 --no-pager

# Export/push timer (updates the public dashboard)
systemctl --user status wake-work-sleep-logger-export.timer
systemctl --user start wake-work-sleep-logger-export.service   # force a push now
journalctl --user -u wake-work-sleep-logger-export.service -n 50 --no-pager
```

- venv is Linux-native at `/home/plexbot2/dev/wake-work-sleep-logger/venv`
  (`python3 -m venv`, Python 3.12.3) - same caveat as chores-assistant, a
  venv never survives a cross-OS move, always recreate at the destination.
- **Claude cannot simulate a live end-to-end test of the running bot** - a
  bot's own `sendMessage` calls never come back through `getUpdates`, so
  there's no way to fake an inbound user message via the API (confirmed on
  chores-assistant). Verifying the actual live bot requires the user to send
  a real message from their Telegram client. `pytest` and direct
  `message_parser`/`stats` calls in isolation are how Claude verifies logic
  changes; `scripts/manual_smoke_test.py` is an opt-in manual round-trip
  prompt, not an automated test.
