#!/usr/bin/env python3
"""
Lightweight container scheduler for IBM ESPP Monitor.
Runs on startup, then executes daily after US market close (21:30 UTC on Monday-Friday).

If TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set, the interactive Telegram bot
is started in a background thread so commands (/check, /lots, /set, etc.) are
available at all times without interfering with the scheduled runs.
"""

import os
import sys
import threading
import time
from datetime import datetime, timezone, timedelta
from ibm_espp_monitor.app import run_once
from ibm_espp_monitor.market_data import MarketDataError


def ensure_default_lots(lots_path: str = "data/espp_lots.csv", default_src: str = "data_default/espp_lots.csv") -> None:
    """If lots file doesn't exist on mounted volume, seed with initial template."""
    if not os.path.exists(lots_path) and os.path.exists(default_src):
        os.makedirs(os.path.dirname(lots_path), exist_ok=True)
        with open(default_src, "r", encoding="utf-8") as f_src, open(lots_path, "w", encoding="utf-8") as f_dst:
            f_dst.write(f_src.read())


def execute_job() -> None:
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{now_str}] Starting scheduled IBM ESPP evaluation...", flush=True)
    try:
        lots_path = os.environ.get("LOTS_PATH", "data/espp_lots.csv")
        ensure_default_lots(lots_path)
        run_once(
            config_path=os.environ.get("CONFIG_PATH", "config/default.toml"),
            lots_path=lots_path,
            state_path=os.environ.get("STATE_PATH", "data/notification_state.json"),
        )
        print(f"[{now_str}] Evaluation completed successfully.\n", flush=True)
    except MarketDataError as e:
        print(f"[{now_str}] Market data error: {e}", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[{now_str}] Unexpected error: {e}", file=sys.stderr, flush=True)


def get_seconds_until_next_run(target_hour_utc: int = 21, target_minute_utc: int = 30) -> float:
    now = datetime.now(timezone.utc)
    # Next candidate today
    candidate = now.replace(
        hour=target_hour_utc,
        minute=target_minute_utc,
        second=0,
        microsecond=0,
    )
    if candidate <= now:
        candidate += timedelta(days=1)

    # If Saturday (5) -> push to Monday (0)
    # If Sunday (6) -> push to Monday (0)
    while candidate.weekday() in (5, 6):
        candidate += timedelta(days=1)

    return (candidate - now).total_seconds()


def _start_bot_thread() -> None:
    """Start the Telegram bot in a daemon thread if credentials are available."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Bot credentials not set — interactive bot will not start.", flush=True)
        return

    def _run() -> None:
        try:
            from ibm_espp_monitor.telegram_bot import run_bot
            run_bot()
        except Exception as e:
            print(f"[Bot] Fatal error: {e}", file=sys.stderr, flush=True)

    t = threading.Thread(target=_run, name="telegram-bot", daemon=True)
    t.start()
    print("Telegram bot thread started.", flush=True)


def main() -> None:
    print("=== IBM ESPP Portfolio Monitor Daemon Started ===", flush=True)

    # Start interactive bot alongside the scheduler
    _start_bot_thread()

    # Run once immediately on container startup
    execute_job()

    while True:
        wait_seconds = get_seconds_until_next_run(target_hour_utc=21, target_minute_utc=30)
        next_run_dt = datetime.now(timezone.utc) + timedelta(seconds=wait_seconds)
        print(
            f"Next scheduled run at: {next_run_dt.strftime('%Y-%m-%d %H:%M:%S UTC')} "
            f"(sleeping for {wait_seconds / 3600:.2f} hours)...",
            flush=True,
        )
        time.sleep(wait_seconds)
        execute_job()


if __name__ == "__main__":
    main()
